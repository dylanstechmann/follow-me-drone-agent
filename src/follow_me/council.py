"""The council: one tick of sense -> context -> fusion -> mode -> control."""

from dataclasses import dataclass, field

from follow_me.context import Conditions, apply_attention, attention
from follow_me.controller import Command, FollowController
from follow_me.fusion import Estimate, FuseReport, Reading, fuse_report
from follow_me.mode import Mode, ModeMachine
from follow_me.motion import Motion, Pose, RiderTracker
from follow_me.sources import estimate_to_detection

DEFAULT_HFOV = 1.5708  # 90 degrees, a placeholder camera
DEFAULT_VFOV = 1.0472  # 60 degrees, a placeholder camera
# The speed an adapter would give a forward command of 1.0. A placeholder, the same
# as the simulation's limit; a real autopilot sets it.
DEFAULT_SPEED_SCALE_MPS = 10.0


def forward_feed(motion: Motion | None, speed_scale_mps: float) -> float:
    """The rider's speed along the drone's nose as a share of full-scale speed.

    It shrinks toward zero when the speed estimate is uncertain compared with the
    speed itself, so a standing rider seen through noisy fixes does not pull the drone.
    """
    if motion is None:
        return 0.0
    v2 = motion.speed_mps**2
    if v2 == 0.0:
        return 0.0
    return motion.forward_mps * v2 / (v2 + motion.sigma_mps**2) / speed_scale_mps


@dataclass(frozen=True)
class TickResult:
    estimate: Estimate | None
    mode: Mode
    gain_scale: float
    request_return_home: bool
    command: Command
    # How the tick was decided, for logs and the replay viewer. Not used for control.
    weights: dict[str, float] = field(default_factory=dict)  # attention multiplier per source
    fusion: FuseReport | None = None
    # The mode machine allows the caller to keep its previous command (dead reckoning).
    hold_last_command: bool = False
    # The rider's estimated velocity, when the caller gave the drone's pose.
    motion: Motion | None = None
    feed: float = 0.0  # the share of the forward command that came from the rider's speed


class Council:
    def __init__(
        self,
        controller: FollowController | None = None,
        machine: ModeMachine | None = None,
        hfov_rad: float = DEFAULT_HFOV,
        vfov_rad: float = DEFAULT_VFOV,
        tracker: RiderTracker | None = None,
        speed_scale_mps: float = DEFAULT_SPEED_SCALE_MPS,
        feed_forward: bool = True,  # False gives the controller as it was before, for comparison
    ) -> None:
        self.controller = controller or FollowController()
        self.machine = machine or ModeMachine()
        self.hfov_rad = hfov_rad
        self.vfov_rad = vfov_rad
        self.tracker = tracker or RiderTracker()
        if speed_scale_mps <= 0:
            raise ValueError("speed_scale_mps must be positive")
        self.speed_scale_mps = speed_scale_mps
        self.feed_forward = feed_forward

    def tick(
        self,
        readings: list[Reading],
        conditions: Conditions,
        overrides: dict[str, float] | None = None,
        *,
        now: float,
        pose: Pose | None = None,
    ) -> TickResult:
        """One tick at time `now`, in seconds. The mode machine times losses with it.

        `pose` is the drone's pose in a local frame, from the autopilot or a simulation.
        With it, the council also estimates the rider's velocity.
        """
        weights = attention(conditions, overrides)
        report = fuse_report(apply_attention(readings, weights))
        fused = report.estimate
        status = self.machine.step(fused, now)
        motion = None
        if pose is not None:
            measured_at = now - report.age_s if fused is not None else None
            motion = self.tracker.step(now, pose, fused, measured_at)
        detection = None
        feed = 0.0
        if fused is not None:
            detection = estimate_to_detection(fused, self.hfov_rad, self.vfov_rad)
            if self.feed_forward:
                feed = forward_feed(motion, self.speed_scale_mps)
        raw = self.controller.update(detection, feed)
        command = Command(
            yaw=raw.yaw * status.gain_scale,
            forward=raw.forward * status.gain_scale,
            climb=raw.climb * status.gain_scale,
        )
        return TickResult(
            estimate=fused,
            mode=status.mode,
            gain_scale=status.gain_scale,
            request_return_home=status.request_return_home,
            command=command,
            weights=weights,
            fusion=report,
            hold_last_command=status.hold_last_command,
            motion=motion,
            feed=feed,
        )
