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
import statistics
from dataclasses import dataclass

from follow_me.companion import offset_estimate
from follow_me.context import Conditions
from follow_me.controller import Command
from follow_me.council import Council, TickResult
from follow_me.fusion import Reading
from follow_me.replay import TRACE_FORMAT, trace_settings, trace_tick

PERSON_HEIGHT_M = 1.75  # the default in sources.estimate_to_detection
EPS = 1e-9


@dataclass(frozen=True)
class Limits:
    """Map normalized commands to motion. Placeholders: an autopilot would set these."""

    max_speed_mps: float = 10.0
    max_yaw_rate_dps: float = 90.0


@dataclass(frozen=True)
class RiderFix:
    """One fix from the rider's phone, as an offset from the track's first fix."""

    t: float  # seconds since the first fix
    east: float  # meters east of the first fix
    north: float  # meters north of the first fix
    accuracy_m: float  # reported 1-sigma horizontal accuracy


@dataclass(frozen=True)
class DroneState:
    east: float
    north: float
    heading_deg: float  # clockwise from north


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
) -> list[SimTick]:
    """Fly the point drone after the rider, one council tick every dt seconds.

    Each tick uses the latest fix no older than max_age_s, seen from where the drone
    is, as a phone_gnss reading. An older fix gives no reading, as in companion.py.
    While the mode machine allows it (dead reckoning), the drone keeps flying the last
    command from a tick that had an estimate.
    """
    _check(fixes, dt)
    council = council or Council()
    drone = start or default_start(fixes, council)
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
            est = offset_estimate(
                fix.east - drone.east, fix.north - drone.north, fix.accuracy_m, drone.heading_deg
            )
            readings.append(Reading("phone_gnss", est))
        result = council.tick(readings, Conditions(), now=t)
        if result.estimate is not None:
            held = result.command
        flown = held if result.hold_last_command else result.command
        ticks.append(SimTick(t, drone, _rider_at(fixes, i, t), readings, result, flown))
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
        "median_distance_m": round(statistics.median(distances), 2),
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
) -> dict:
    """Simulate a track and return a trace the replay viewer reads, with the drone's world."""
    council = council or Council()
    ticks = simulate(fixes, council, dt, limits)
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
