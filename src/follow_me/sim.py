"""Kinematic follow simulation: a point drone that turns and moves as the council commands.

This is not a flight simulator. There is no physics, wind, autopilot, battery or
camera. The drone is a point in a flat local frame, in meters east and north of the
track's first fix. Each tick it turns at a limited rate and moves along its nose at a
limited speed, scaled by the council's normalized commands. Climb is ignored, and a
return-home request is recorded, not flown. The limits are placeholders.

It closes the loop: where the drone goes changes what the next reading says. That
lets the follow logic be tested against a rider who moves, and lets a recorded track
be replayed. It does not stand in for the SITL gate in docs/build-plan.md.
"""

import math
import random
import statistics
from dataclasses import dataclass

from follow_me.companion import offset_estimate
from follow_me.context import Conditions
from follow_me.controller import Command, Detection
from follow_me.council import Council, TickResult
from follow_me.fusion import Reading
from follow_me.motion import Pose, to_body
from follow_me.replay import TRACE_FORMAT, trace_settings, trace_tick
from follow_me.sources import camera_estimate

PERSON_HEIGHT_M = 1.75  # the default in sources.estimate_to_detection
EPS = 1e-9
EXAMPLE_NOTE = (
    "A made-up ride, not a recording: invented positions and accuracies, one fix a "
    "second, chosen to show each mode. The drone is simulated, with placeholder limits; "
    "it is not a flight simulator."
)


@dataclass(frozen=True)
class Limits:
    """Map normalized commands to motion. Placeholders: an autopilot would set these."""

    max_speed_mps: float = 10.0
    max_yaw_rate_dps: float = 90.0


# How often the person detector (YOLOX-Nano at a 0.35 score) found people in 500 COCO
# validation photos, by the person's height in its 416-pixel input: (height px, share
# found). All people, partly hidden ones included, so a rider in clear view is found
# somewhat more often. Measured with tools/detector_recall.py on 2026-10-27; see
# docs/camera.md. Heights are bin middles; beyond the last point the share stays level.
MEASURED_RECALL = (
    (4.0, 0.01), (10.0, 0.01), (14.0, 0.05), (20.0, 0.12), (28.0, 0.31),
    (40.0, 0.47), (56.0, 0.66), (80.0, 0.69), (112.0, 0.82), (160.0, 0.89),
)
INPUT_FRAME_PX = 312.0  # a 4:3 frame's height in the detector's 416-pixel input


def recall_at(height_px: float, curve: tuple = MEASURED_RECALL) -> float:
    """The share of people found at a height on screen, between the curve's points."""
    if height_px <= curve[0][0]:
        return curve[0][1]
    for (h0, r0), (h1, r1) in zip(curve, curve[1:]):
        if height_px <= h1:
            return r0 + (r1 - r0) * (height_px - h0) / (h1 - h0)
    return curve[-1][1]


@dataclass(frozen=True)
class Camera:
    """A simulated camera on the drone's nose, standing in for the person detector.

    Each tick it sees the rider only inside the council's field of view and its range
    limit, and only as often as the detector found people of the rider's height on
    screen (`recall`, measured on COCO photos). It makes the box a detector would, with
    the error sources.camera_estimate assumes, and passes the box through that function.
    There are no other people, no wrong detections and nothing in the way.
    """

    max_range_m: float = 60.0
    bearing_sigma_rad: float = 0.05  # placeholders, as in sources.camera_estimate
    range_sigma_frac: float = 0.15
    recall: tuple = MEASURED_RECALL
    frame_px: float = INPUT_FRAME_PX
    seed: int = 1


@dataclass(frozen=True)
class RiderFix:
    """One fix from the rider's phone, as an offset from the track's first fix."""

    t: float  # seconds since the first fix
    east: float  # meters east of the first fix
    north: float  # meters north of the first fix
    accuracy_m: float  # reported 1-sigma horizontal accuracy


# The simulated drone's state is its pose: meters east and north, heading clockwise from north.
DroneState = Pose


@dataclass(frozen=True)
class SimTick:
    t: float
    drone: DroneState  # where the drone was when the tick was decided
    rider: tuple[float, float]  # where the track puts the rider at t, east and north
    readings: list[Reading]
    result: TickResult
    flown: Command  # what the drone did: the council's command, or the one it held

    @property
    def distance(self) -> float:
        return math.hypot(self.rider[0] - self.drone.east, self.rider[1] - self.drone.north)


def follow_band(council: Council, person_height_m: float = PERSON_HEIGHT_M) -> tuple[float, float]:
    """The distances between which the controller asks neither to approach nor to back off."""
    ctrl = council.controller
    k = person_height_m / (2.0 * math.tan(council.vfov_rad / 2.0))
    near = k / (ctrl.target_height + ctrl.deadband)
    low = ctrl.target_height - ctrl.deadband
    return near, (k / low if low > 0 else math.inf)


def default_start(fixes: list[RiderFix], council: Council) -> DroneState:
    """Mid-band behind the rider's first fix, facing the rider.

    Behind means against the direction to the first fix 10 m away, so GNSS jitter
    while standing does not set it. A rider who never moves 10 m faces the drone north.
    """
    near, far = follow_band(council)
    d = (near + far) / 2.0
    first = fixes[0]
    heading = 0.0
    for f in fixes[1:]:
        de, dn = f.east - first.east, f.north - first.north
        if math.hypot(de, dn) >= 10.0:
            heading = math.degrees(math.atan2(de, dn)) % 360.0
            break
    h = math.radians(heading)
    return DroneState(first.east - d * math.sin(h), first.north - d * math.cos(h), heading)


def example_track() -> list[RiderFix]:
    """A made-up 145 s ride for the website: standing, riding with turns, a stretch with
    weak fixes, a 15 s gap with no fixes, then a stop. One fix a second."""
    # (last second of the leg, speed in m/s, heading in degrees, accuracy in m or None for no fix)
    legs = [
        (10, 0.0, 0.0, 2.0),
        (50, 3.0, 0.0, 2.0),
        (80, 3.0, 90.0, 4.0),
        (95, 3.0, 90.0, None),
        (130, 2.5, 135.0, 2.0),
        (145, 0.0, 135.0, 2.0),
    ]
    fixes = []
    east = north = heading = 0.0
    leg = 0
    for t in range(legs[-1][0] + 1):
        while t > legs[leg][0]:
            leg += 1
        _, speed, target, accuracy = legs[leg]
        heading += max(-22.5, min(22.5, (target - heading + 540.0) % 360.0 - 180.0))  # turn over a few seconds
        east += speed * math.sin(math.radians(heading))
        north += speed * math.cos(math.radians(heading))
        if accuracy is not None:
            fixes.append(RiderFix(float(t), round(east, 2), round(north, 2), accuracy))
    return fixes


def _check(fixes: list[RiderFix], dt: float) -> None:
    if dt <= 0:
        raise ValueError("dt must be positive")
    if len(fixes) < 2:
        raise ValueError("need at least two fixes")
    for a, b in zip(fixes, fixes[1:]):
        if b.t <= a.t:
            raise ValueError("fix times must increase")
    if any(f.accuracy_m <= 0 for f in fixes):
        raise ValueError("accuracy_m must be positive")


def _rider_at(fixes: list[RiderFix], i: int, t: float) -> tuple[float, float]:
    """The track between fix i and the next, at time t."""
    a = fixes[i]
    if i + 1 == len(fixes):
        return a.east, a.north
    b = fixes[i + 1]
    s = min(1.0, max(0.0, (t - a.t) / (b.t - a.t)))
    return a.east + s * (b.east - a.east), a.north + s * (b.north - a.north)


def _camera_reading(
    camera: Camera, rng: random.Random, council: Council, drone: DroneState, rider: tuple[float, float],
) -> Reading | None:
    x, y = to_body(drone, rider[0] - drone.east, rider[1] - drone.north)
    distance, bearing = math.hypot(x, y), math.atan2(y, x)
    if distance < 0.5 or distance > camera.max_range_m or abs(bearing) > council.hfov_rad / 2.0:
        return None
    height_px = camera.frame_px * PERSON_HEIGHT_M / (2.0 * distance * math.tan(council.vfov_rad / 2.0))
    if rng.random() >= recall_at(height_px, camera.recall):
        return None
    seen_range = distance * max(0.2, 1.0 + rng.gauss(0.0, camera.range_sigma_frac))
    seen_bearing = bearing + rng.gauss(0.0, camera.bearing_sigma_rad)
    box = Detection(
        cx=0.5 - seen_bearing / council.hfov_rad,
        cy=0.5,
        height=PERSON_HEIGHT_M / (2.0 * seen_range * math.tan(council.vfov_rad / 2.0)),
    )
    est = camera_estimate(
        box, council.hfov_rad, council.vfov_rad,
        bearing_sigma_rad=camera.bearing_sigma_rad, range_sigma_frac=camera.range_sigma_frac,
    )
    return Reading("camera", est)


def _clamp1(v: float) -> float:
    return max(-1.0, min(1.0, v))


def _move(drone: DroneState, cmd: Command, limits: Limits, dt: float) -> DroneState:
    # Yaw + turns right, which is clockwise, so the heading grows.
    heading = (drone.heading_deg + _clamp1(cmd.yaw) * limits.max_yaw_rate_dps * dt) % 360.0
    speed = _clamp1(cmd.forward) * limits.max_speed_mps
    h = math.radians(heading)
    return DroneState(
        drone.east + speed * math.sin(h) * dt,
        drone.north + speed * math.cos(h) * dt,
        heading,
    )


def simulate(
    fixes: list[RiderFix],
    council: Council | None = None,
    dt: float = 0.5,
    limits: Limits = Limits(),
    start: DroneState | None = None,
    max_age_s: float = 2.0,
    noise_m: float = 0.0,
    seed: int = 0,
    camera: Camera | None = None,
) -> list[SimTick]:
    """Fly the point drone after the rider, one council tick every dt seconds.

    Each tick uses the latest fix no older than max_age_s, seen from where the drone
    is, as a phone_gnss reading carrying the fix's age. An older fix gives no reading,
    as in companion.py. While the mode machine allows it (dead reckoning), the drone
    keeps flying the last command from a tick that had an estimate.

    noise_m adds made-up Gaussian error to each fix, drawn once per fix from `seed`,
    to test how the follow logic copes with a noisy receiver. The track stays the truth.
    A `camera` adds a camera reading on each tick the rider is in view.
    """
    _check(fixes, dt)
    if noise_m < 0:
        raise ValueError("noise_m must not be negative")
    council = council or Council()
    drone = start or default_start(fixes, council)
    rng = random.Random(seed)
    errors = [(rng.gauss(0.0, noise_m), rng.gauss(0.0, noise_m)) if noise_m else (0.0, 0.0) for _ in fixes]
    camera_rng = random.Random(camera.seed) if camera else None
    held = Command(0.0, 0.0, 0.0)
    ticks = []
    t0 = fixes[0].t
    i = 0
    for k in range(int((fixes[-1].t - t0) / dt + EPS) + 1):
        t = t0 + k * dt
        while i + 1 < len(fixes) and fixes[i + 1].t <= t + EPS:
            i += 1
        fix = fixes[i]
        readings = []
        if t - fix.t <= max_age_s + EPS:
            de, dn = errors[i]
            est = offset_estimate(
                fix.east + de - drone.east, fix.north + dn - drone.north, fix.accuracy_m, drone.heading_deg
            )
            readings.append(Reading("phone_gnss", est, age_s=max(0.0, t - fix.t)))
        rider = _rider_at(fixes, i, t)
        if camera is not None:
            seen = _camera_reading(camera, camera_rng, council, drone, rider)
            if seen is not None:
                readings.append(seen)
        result = council.tick(readings, Conditions(), now=t, pose=drone)
        if result.estimate is not None:
            held = result.command
        flown = held if result.hold_last_command else result.command
        ticks.append(SimTick(t, drone, rider, readings, result, flown))
        drone = _move(drone, flown, limits, dt)
    return ticks


def summarize(ticks: list[SimTick], council: Council, dt: float) -> dict:
    """Time in each mode, and how far the drone stayed from the rider's track."""
    near, far = follow_band(council)
    distances = [s.distance for s in ticks]
    seconds: dict[str, float] = {}
    for s in ticks:
        seconds[s.result.mode.value] = seconds.get(s.result.mode.value, 0.0) + dt
    return {
        "duration_s": round(ticks[-1].t - ticks[0].t, 3),
        "seconds_in_mode": {mode: round(v, 3) for mode, v in seconds.items()},
        "band_m": [round(near, 2), round(far, 2)],
        "in_band_share": round(sum(near <= d <= far for d in distances) / len(distances), 4),
        "too_close_share": round(sum(d < near for d in distances) / len(distances), 4),
        "camera_share": round(sum(any(r.source == "camera" for r in s.readings) for s in ticks) / len(ticks), 4),
        "median_distance_m": round(statistics.median(distances), 2),
        "min_distance_m": round(min(distances), 2),
        "max_distance_m": round(max(distances), 2),
        "return_home_requested": any(s.result.request_return_home for s in ticks),
    }


def _round(value: float, digits: int = 2) -> float:
    return round(value, digits)


def trace_track(
    fixes: list[RiderFix],
    council: Council | None = None,
    dt: float = 0.5,
    limits: Limits = Limits(),
    note: str = "",
    camera: Camera | None = None,
) -> dict:
    """Simulate a track and return a trace the replay viewer reads, with the drone's world."""
    council = council or Council()
    ticks = simulate(fixes, council, dt, limits, camera=camera)
    out = []
    for s in ticks:
        log_tick = {
            "t": s.t,
            "readings": [
                {"source": r.source, "x": r.estimate.x, "y": r.estimate.y,
                 "variance": r.estimate.variance, "reliability": r.reliability}
                for r in s.readings
            ],
        }
        entry = trace_tick(log_tick, s.t, s.result)
        entry["world"] = {
            "drone": [_round(s.drone.east), _round(s.drone.north), _round(s.drone.heading_deg, 1)],
            "rider": [_round(s.rider[0]), _round(s.rider[1])],
            "distance": _round(s.distance),
            "flown": {
                "yaw": _round(s.flown.yaw, 4),
                "forward": _round(s.flown.forward, 4),
            },
        }
        out.append(entry)
    settings = trace_settings(council)
    settings.update({
        "dt_s": dt,
        "max_speed_mps": limits.max_speed_mps,
        "max_yaw_rate_dps": limits.max_yaw_rate_dps,
    })
    return {
        "format": TRACE_FORMAT,
        "kind": "simulation",
        "note": note,
        "settings": settings,
        "summary": summarize(ticks, council, dt),
        "ticks": out,
    }
