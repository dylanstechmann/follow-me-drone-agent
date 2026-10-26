"""The rider's motion: a constant-velocity Kalman filter over the fused estimates.

The council's estimates are relative to the drone, which moves, so the rider's own
velocity cannot be read from them alone. Given the drone's pose in a local frame
(meters east and north, and heading), which an autopilot reports and the simulation
knows, each estimate is placed in that frame and filtered there. The velocity is
then expressed in the drone's frame for the controller.

The local frame may drift slowly, as autopilot odometry does. The filter only needs
it to be consistent over a few seconds. East and north are filtered separately,
which is exact here because the estimates' variance is isotropic.
"""

import math
from dataclasses import dataclass

from follow_me.fusion import Estimate


@dataclass(frozen=True)
class Pose:
    """The drone in a local frame: meters east and north, heading clockwise from north."""

    east: float
    north: float
    heading_deg: float


@dataclass(frozen=True)
class Motion:
    """The rider's estimated velocity over the ground, in the drone's frame (+x forward, +y left)."""

    forward_mps: float
    left_mps: float
    sigma_mps: float  # one-sigma uncertainty of each component

    @property
    def speed_mps(self) -> float:
        return math.hypot(self.forward_mps, self.left_mps)


def to_local(pose: Pose, est: Estimate) -> tuple[float, float]:
    """A body-frame estimate as meters east and north in the pose's local frame."""
    h = math.radians(pose.heading_deg)
    # The nose points (sin h, cos h) in east and north, and the left side (-cos h, sin h).
    return (
        pose.east + est.x * math.sin(h) - est.y * math.cos(h),
        pose.north + est.x * math.cos(h) + est.y * math.sin(h),
    )


def to_body(pose: Pose, east: float, north: float) -> tuple[float, float]:
    """An east and north vector, such as a velocity, as forward and left of the pose's nose."""
    h = math.radians(pose.heading_deg)
    return east * math.sin(h) + north * math.cos(h), -east * math.cos(h) + north * math.sin(h)


class _Axis:
    """Position and velocity along one axis, with their 2x2 covariance."""

    def __init__(self, pos: float, pos_var: float, vel_var: float) -> None:
        self.pos, self.vel = pos, 0.0
        self.p00, self.p01, self.p11 = pos_var, 0.0, vel_var

    def predict(self, dt: float, q: float) -> None:
        self.pos += self.vel * dt
        self.p00 += dt * (2.0 * self.p01 + dt * self.p11) + q * dt**3 / 3.0
        self.p01 += dt * self.p11 + q * dt**2 / 2.0
        self.p11 += q * dt

    def update(self, z: float, r: float) -> None:
        s = self.p00 + r
        k0, k1 = self.p00 / s, self.p01 / s
        innovation = z - self.pos
        self.pos += k0 * innovation
        self.vel += k1 * innovation
        p00, p01, p11 = self.p00, self.p01, self.p11
        self.p00 = (1.0 - k0) * p00
        self.p01 = (1.0 - k0) * p01
        self.p11 = p11 - k1 * p01


class RiderTracker:
    def __init__(
        self,
        # How hard the rider may speed up, slow down or turn, as one sigma of a
        # white-noise acceleration. A guess for a skater; tune on real logs.
        accel_sigma_mps2: float = 1.5,
        # After this long without an estimate the velocity is stale: report none,
        # and start afresh at the next estimate.
        max_gap_s: float = 5.0,
        initial_speed_sigma_mps: float = 5.0,
    ) -> None:
        if accel_sigma_mps2 <= 0 or max_gap_s <= 0 or initial_speed_sigma_mps <= 0:
            raise ValueError("tracker settings must be positive")
        self.q = accel_sigma_mps2**2
        self.max_gap_s = max_gap_s
        self.initial_vel_var = initial_speed_sigma_mps**2
        self._axes: tuple[_Axis, _Axis] | None = None
        self._now: float | None = None
        self._measured: float | None = None  # when the last measurement used was taken

    def step(
        self, now: float, pose: Pose, estimate: Estimate | None, measured_at: float | None = None,
    ) -> Motion | None:
        """Take the estimate, if it is a new measurement, and return the rider's velocity
        in the drone's frame at `now`: None before the first estimate or after a gap.

        `measured_at` is when the estimate's measurement was taken (`now` if not given).
        The same measurement seen again, such as a 1 Hz phone fix on a 2 Hz loop, adds
        nothing. The estimate must be relative to the drone at `pose`, as the council's are.
        """
        if self._now is not None and now < self._now:
            raise ValueError("tick times must not go backwards")
        self._now = now
        if estimate is not None:
            at = now if measured_at is None else measured_at
            if self._measured is None or at > self._measured + 1e-9:
                east, north = to_local(pose, estimate)
                if self._axes is None or at - self._measured > self.max_gap_s:
                    self._axes = (
                        _Axis(east, estimate.variance, self.initial_vel_var),
                        _Axis(north, estimate.variance, self.initial_vel_var),
                    )
                else:
                    for axis, z in zip(self._axes, (east, north)):
                        axis.predict(at - self._measured, self.q)
                        axis.update(z, estimate.variance)
                self._measured = at
        if self._axes is None or now - self._measured > self.max_gap_s:
            return None
        e, n = self._axes
        forward, left = to_body(pose, e.vel, n.vel)
        # The velocity is carried forward unchanged; its uncertainty grows until the next measurement.
        return Motion(forward, left, math.sqrt(max(e.p11, n.p11) + self.q * (now - self._measured)))
