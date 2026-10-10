"""Companion GNSS: a rider-carried receiver (phone or tag) as a body-frame estimate.

Each companion is its own source (phone_gnss, tag_gnss). Two receivers have
independent errors, so when they agree the council gets more confidence, and
when they disagree the gate can tell which one to trust.
"""

import math
from dataclasses import dataclass

from follow_me.fusion import Estimate
from follow_me.geo import enu_offset_m


@dataclass(frozen=True)
class DronePose:
    lat: float
    lon: float
    heading_deg: float  # clockwise from north, the direction the drone's nose points


@dataclass(frozen=True)
class CompanionFix:
    lat: float
    lon: float
    accuracy_m: float  # reported 1-sigma horizontal accuracy, meters
    t: float  # timestamp in seconds, same clock as `now`


def companion_estimate(
    fix: CompanionFix,
    drone: DronePose,
    now: float,
    max_age_s: float = 2.0,
    heading_sigma_rad: float = math.radians(3.0),
) -> Estimate | None:
    """Rider position relative to the drone, in the body frame (+x forward, +y left).

    Returns None for a stale or future fix, so old radio or cellular data is never
    fused as if it were current. The heading error adds variance in proportion to
    range. The variance is isotropic, a simplification.
    """
    if fix.accuracy_m <= 0:
        raise ValueError("accuracy_m must be positive")
    age = now - fix.t
    if age < 0 or age > max_age_s:
        return None

    east, north = enu_offset_m(drone.lat, drone.lon, fix.lat, fix.lon)
    h = math.radians(drone.heading_deg)
    # Rotate the east/north offset into the drone's frame (nose = +x, left = +y).
    x = east * math.sin(h) + north * math.cos(h)
    y = -east * math.cos(h) + north * math.sin(h)
    rng = math.hypot(x, y)
    variance = fix.accuracy_m**2 + (rng * heading_sigma_rad) ** 2
    return Estimate(x, y, variance)
