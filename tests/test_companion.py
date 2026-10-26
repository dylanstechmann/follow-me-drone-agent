import math

import pytest

from follow_me.companion import CompanionFix, DronePose, companion_estimate
from follow_me.context import Conditions, WeatherReport
from follow_me.controller import Detection
from follow_me.council import DEFAULT_HFOV, DEFAULT_VFOV, Council
from follow_me.fusion import Reading
from follow_me.geo import EARTH_RADIUS_M
from follow_me.mode import Mode
from follow_me.sources import camera_estimate

# Meters per degree on the sphere. Used only to place test fixes exactly.
DEG_M = EARTH_RADIUS_M * math.pi / 180
ORIGIN = DronePose(0.0, 0.0, heading_deg=0.0)


def fix_at(north_m=0.0, east_m=0.0, accuracy=2.0, t=10.0):
    return CompanionFix(north_m / DEG_M, east_m / DEG_M, accuracy, t)


def test_rider_ahead_when_facing_north():
    e = companion_estimate(fix_at(north_m=10), ORIGIN, now=10.5)
    assert e.x == pytest.approx(10.0, abs=1e-3)
    assert e.y == pytest.approx(0.0, abs=1e-3)


def test_rider_to_the_east_is_on_the_right_when_facing_north():
    e = companion_estimate(fix_at(east_m=10), ORIGIN, now=10.5)
    assert e.x == pytest.approx(0.0, abs=1e-3)
    assert e.y == pytest.approx(-10.0, abs=1e-3)


def test_rider_to_the_east_is_ahead_when_facing_east():
    drone = DronePose(0.0, 0.0, heading_deg=90.0)
    e = companion_estimate(fix_at(east_m=10), drone, now=10.5)
    assert e.x == pytest.approx(10.0, abs=1e-3)
    assert e.y == pytest.approx(0.0, abs=1e-3)


def test_rider_to_the_north_is_on_the_left_when_facing_east():
    drone = DronePose(0.0, 0.0, heading_deg=90.0)
    e = companion_estimate(fix_at(north_m=10), drone, now=10.5)
    assert e.x == pytest.approx(0.0, abs=1e-3)
    assert e.y == pytest.approx(10.0, abs=1e-3)


def test_rider_behind_is_negative_x():
    e = companion_estimate(fix_at(north_m=-10), ORIGIN, now=10.5)
    assert e.x == pytest.approx(-10.0, abs=1e-3)


def test_heading_360_matches_heading_0():
    a = companion_estimate(fix_at(north_m=10), DronePose(0.0, 0.0, 0.0), now=10.5)
    b = companion_estimate(fix_at(north_m=10), DronePose(0.0, 0.0, 360.0), now=10.5)
    assert a.x == pytest.approx(b.x, abs=1e-6)
    assert a.y == pytest.approx(b.y, abs=1e-6)


def test_stale_fix_is_rejected():
    fix = fix_at(north_m=10, t=10.0)
    assert companion_estimate(fix, ORIGIN, now=13.0, max_age_s=2.0) is None


def test_fix_inside_max_age_is_used():
    fix = fix_at(north_m=10, t=10.0)
    assert companion_estimate(fix, ORIGIN, now=11.5, max_age_s=2.0) is not None


def test_future_fix_is_rejected():
    fix = fix_at(north_m=10, t=11.0)
    assert companion_estimate(fix, ORIGIN, now=10.0) is None


def test_variance_includes_reported_accuracy():
    e = companion_estimate(fix_at(north_m=1, accuracy=3.0), ORIGIN, now=10.5)
    # Heading error at 1 m range adds almost nothing, so variance is close to 3^2.
    assert e.variance == pytest.approx(9.0, rel=0.01)


def test_heading_error_grows_variance_with_range():
    near = companion_estimate(fix_at(north_m=2, accuracy=2), ORIGIN, now=10.5)
    far = companion_estimate(fix_at(north_m=40, accuracy=2), ORIGIN, now=10.5)
    assert far.variance > near.variance


def test_rejects_non_positive_accuracy():
    with pytest.raises(ValueError):
        companion_estimate(fix_at(north_m=10, accuracy=0.0), ORIGIN, now=10.5)


def test_phone_tag_and_camera_agree_through_the_council():
    # Rider 10 m ahead of a north-facing drone. All three sources should agree.
    h = 1.75 / (2 * 10.0 * math.tan(DEFAULT_VFOV / 2))
    readings = [
        Reading("phone_gnss", companion_estimate(fix_at(north_m=10, accuracy=3), ORIGIN, now=10.5)),
        Reading("tag_gnss", companion_estimate(fix_at(north_m=10, accuracy=2), ORIGIN, now=10.5)),
        Reading(
            "camera",
            camera_estimate(Detection(cx=0.5, cy=0.5, height=h), DEFAULT_HFOV, DEFAULT_VFOV),
        ),
    ]
    clear = Conditions(weather=WeatherReport(0.0, 2.0, False))
    result = Council().tick(readings, clear)
    assert result.mode is Mode.TRACKING
    assert result.estimate.x == pytest.approx(10.0, abs=0.5)
    assert result.estimate.y == pytest.approx(0.0, abs=0.5)


def test_stale_phone_fix_is_dropped_and_tag_carries_the_estimate():
    phone = companion_estimate(fix_at(north_m=10, t=0.0), ORIGIN, now=10.0)
    assert phone is None  # ten seconds old, far past the two-second limit
    tag = companion_estimate(fix_at(north_m=10, accuracy=2, t=10.0), ORIGIN, now=10.0)
    readings = [Reading("tag_gnss", tag)]
    result = Council().tick(readings, Conditions())
    assert result.mode is Mode.TRACKING
    assert result.estimate.x == pytest.approx(10.0, abs=1e-3)


def test_offset_estimate_rotates_like_a_fix():
    from follow_me.companion import offset_estimate

    by_offset = offset_estimate(10.0, 0.0, 2.0, heading_deg=90.0)
    by_fix = companion_estimate(fix_at(east_m=10), DronePose(0.0, 0.0, 90.0), now=10.5)
    assert by_offset.x == pytest.approx(by_fix.x, abs=1e-3)
    assert by_offset.y == pytest.approx(by_fix.y, abs=1e-3)
    assert by_offset.variance == pytest.approx(by_fix.variance, rel=1e-6)
    with pytest.raises(ValueError):
        offset_estimate(1.0, 1.0, 0.0, heading_deg=0.0)


def test_council_passes_on_the_dead_reckoning_hold():
    council = Council()
    assert council.tick([Reading("phone_gnss", companion_estimate(fix_at(north_m=10), ORIGIN, now=10.5))], Conditions()).hold_last_command is False
    assert council.tick([], Conditions()).hold_last_command is True
