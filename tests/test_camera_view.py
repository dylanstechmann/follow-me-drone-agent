"""The camera page's Python: one rider box at a time through the council."""

import math

import pytest

from follow_me.camera_view import CameraView, vertical_fov_deg
from follow_me.sources import camera_estimate


def test_vertical_field_of_view_follows_the_frame_shape():
    assert vertical_fov_deg(90.0, 1.0) == pytest.approx(90.0)
    assert vertical_fov_deg(70.0, 4.0 / 3.0) == pytest.approx(55.0, abs=0.5)


def test_a_centred_box_gives_a_rider_straight_ahead():
    tick = CameraView().step(0.0, {"cx": 0.5, "cy": 0.5, "height": 0.35})
    assert tick["mode"] == "tracking"
    assert tick["readings"][0]["source"] == "camera"
    assert tick["estimate"]["y"] == pytest.approx(0.0, abs=1e-9)
    assert tick["command"]["yaw"] == 0.0
    # The safety margin shows the controller the rider closer than the box says, so it backs off.
    assert tick["margin"] > 0 and tick["command"]["forward"] < 0


def test_the_estimate_is_camera_estimates():
    view = CameraView(hfov_deg=60.0, aspect=16 / 9)
    tick = view.step(0.0, {"cx": 0.7, "cy": 0.5, "height": 0.2})
    from follow_me.controller import Detection

    est = camera_estimate(Detection(0.7, 0.5, 0.2), view.hfov_rad, view.vfov_rad)
    assert tick["readings"][0]["x"] == pytest.approx(est.x, abs=1e-3)
    assert tick["readings"][0]["y"] == pytest.approx(est.y, abs=1e-3)
    assert tick["command"]["yaw"] > 0  # the rider is right of centre: turn right


def test_losing_the_rider_walks_down_the_fallback_ladder_in_seconds():
    view = CameraView()
    view.step(0.0, {"cx": 0.5, "cy": 0.5, "height": 0.3})
    modes = {t: view.step(t, None)["mode"] for t in (1.0, 5.0, 6.0, 50.0, 51.0)}
    assert modes == {1.0: "dead_reckoning", 5.0: "dead_reckoning", 6.0: "hold", 50.0: "hold", 51.0: "return_home_requested"}
    assert view.step(52.0, {"cx": 0.5, "cy": 0.5, "height": 0.3})["mode"] == "tracking"


def test_bad_settings_and_empty_boxes():
    with pytest.raises(ValueError):
        CameraView(hfov_deg=5.0)
    assert CameraView().step(0.0, {"cx": 0.5, "cy": 0.5, "height": 0.0})["readings"] == []
    assert math.isclose(CameraView(aspect=1.0).vfov_rad, CameraView(aspect=1.0).hfov_rad)
