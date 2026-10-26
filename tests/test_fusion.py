import math

import pytest

from follow_me.controller import Detection
from follow_me.fusion import Estimate, Reading, fuse, fuse_report
from follow_me.sources import camera_estimate


def est(x, y=0.0, var=1.0):
    return Estimate(x, y, var)


def test_no_readings_gives_none():
    assert fuse([]) is None


def test_single_reading_passes_through():
    out = fuse([Reading("camera", est(10.0, 2.0, 1.0))])
    assert out.x == pytest.approx(10.0)
    assert out.y == pytest.approx(2.0)


def test_agreeing_readings_are_weighted_by_information():
    # info: 1/1 = 1 and 1/4 = 0.25 -> mean x = (10*1 + 12*0.25) / 1.25 = 10.4
    out = fuse([Reading("a", est(10.0, 0, 1.0)), Reading("b", est(12.0, 0, 4.0))])
    assert out.x == pytest.approx(10.4)
    assert out.variance == pytest.approx(0.8)


def test_more_agreeing_sources_reduce_variance():
    one = fuse([Reading("a", est(10.0, 0, 1.0))])
    two = fuse([Reading("a", est(10.0, 0, 1.0)), Reading("b", est(10.1, 0, 1.0))])
    assert two.variance < one.variance


def test_outlier_is_rejected():
    readings = [
        Reading("camera", est(10.0, 0, 1.0)),
        Reading("gnss", est(10.2, 0, 1.0)),
        Reading("ble", est(40.0, 0, 1.0)),  # wild disagreement
    ]
    out = fuse(readings)
    assert out.x == pytest.approx(10.1, abs=0.05)


def test_two_strong_disagreements_have_no_consensus():
    readings = [Reading("a", est(0.0, 0, 1.0)), Reading("b", est(10.0, 0, 1.0))]
    assert fuse(readings) is None


def test_zero_reliability_source_is_ignored():
    readings = [
        Reading("camera", est(10.0, 0, 1.0)),
        Reading("ble", est(-50.0, 0, 1.0), reliability=0.0),
    ]
    out = fuse(readings)
    assert out.x == pytest.approx(10.0)


def test_estimate_range_and_bearing():
    e = est(3.0, 4.0)
    assert e.range == pytest.approx(5.0)
    assert e.bearing == pytest.approx(math.atan2(4.0, 3.0))


def test_camera_centered_at_known_distance():
    vfov = math.radians(60)
    hfov = math.radians(90)
    # Build the box height a 1.75 m person would have at 10 m.
    h = 1.75 / (2 * 10.0 * math.tan(vfov / 2))
    e = camera_estimate(Detection(cx=0.5, cy=0.5, height=h), hfov, vfov)
    assert e.x == pytest.approx(10.0, rel=1e-6)
    assert e.y == pytest.approx(0.0, abs=1e-9)


def test_camera_person_on_left_gives_positive_y():
    vfov = math.radians(60)
    hfov = math.radians(90)
    h = 1.75 / (2 * 10.0 * math.tan(vfov / 2))
    e = camera_estimate(Detection(cx=0.25, cy=0.5, height=h), hfov, vfov)
    assert e.y > 0


def test_camera_person_on_right_gives_negative_y():
    vfov = math.radians(60)
    hfov = math.radians(90)
    h = 1.75 / (2 * 10.0 * math.tan(vfov / 2))
    e = camera_estimate(Detection(cx=0.75, cy=0.5, height=h), hfov, vfov)
    assert e.y < 0


def test_camera_uncertainty_grows_with_range():
    vfov = math.radians(60)
    hfov = math.radians(90)
    near = camera_estimate(Detection(0.5, 0.5, 0.5), hfov, vfov)
    far = camera_estimate(Detection(0.5, 0.5, 0.05), hfov, vfov)
    assert far.variance > near.variance


def test_camera_rejects_zero_height():
    with pytest.raises(ValueError):
        camera_estimate(Detection(0.5, 0.5, 0.0), 1.0, 1.0)


def test_report_says_which_readings_were_kept_rejected_or_off():
    readings = [
        Reading("camera", est(4.0), reliability=0.4),
        Reading("phone_gnss", est(10.0), reliability=1.0),
        Reading("tag_gnss", est(10.2), reliability=1.0),
        Reading("tof", est(9.0), reliability=0.0),
    ]
    report = fuse_report(readings)
    assert report.status == ("rejected", "kept", "kept", "off")
    assert report.reference == (10.0, 0.0)
    assert report.estimate == fuse(readings)


def test_report_with_nothing_active_has_no_reference():
    report = fuse_report([Reading("camera", est(4.0), reliability=0.0)])
    assert report == type(report)(None, None, ("off",))


def test_report_when_the_gate_rejects_everything():
    report = fuse_report([Reading("a", est(0.0)), Reading("b", est(10.0))])
    assert report.estimate is None
    assert report.reference == (5.0, 0.0)
    assert report.status == ("rejected", "rejected")

