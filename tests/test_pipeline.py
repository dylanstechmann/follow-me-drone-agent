"""Integration: readings -> context attention -> fusion -> mode -> controller."""

import math

import pytest

from follow_me.context import Conditions, WeatherReport, apply_attention, attention
from follow_me.controller import Command, Detection, FollowController
from follow_me.fusion import Estimate, Reading, fuse
from follow_me.mode import Mode, ModeMachine
from follow_me.places import Place, active_places, combined_attention
from follow_me.sources import camera_estimate

VFOV = math.radians(60)
HFOV = math.radians(90)
H_PERSON = 1.75


def camera_box_at(distance_m, cx=0.5):
    h = H_PERSON / (2 * distance_m * math.tan(VFOV / 2))
    return Detection(cx=cx, cy=0.5, height=h)


def run_tick(readings, conditions, places=(), ctrl=None, machine=None):
    overrides = combined_attention(list(places))
    weights = attention(conditions, overrides)
    fused = fuse(apply_attention(readings, weights))
    status = (machine or ModeMachine()).step(fused)
    cmd = (ctrl or FollowController()).update(None if fused is None else _as_detection(fused))
    return fused, status, cmd


def _as_detection(e: Estimate) -> Detection:
    # Convert the fused body-frame estimate back to the controller's image-style input
    # for this integration check: bearing -> cx, range -> box height.
    cx = 0.5 - e.bearing / HFOV
    h = H_PERSON / (2 * e.range * math.tan(VFOV / 2))
    return Detection(cx=cx, cy=0.5, height=h)


def test_clear_day_both_sources_agree_and_tracks():
    clear = WeatherReport(0.0, 2.0, False)
    readings = [
        Reading("camera", camera_estimate(camera_box_at(10.0), HFOV, VFOV)),
        Reading("companion_gnss", Estimate(10.3, 0.0, 1.0)),
    ]
    fused, status, cmd = run_tick(readings, Conditions(weather=clear))
    assert status.mode is Mode.TRACKING
    assert fused.x == pytest.approx(10.0, abs=0.5)
    assert abs(cmd.forward) < 0.5  # near the setpoint, little approach


def test_rain_plus_shed_place_lets_gnss_carry_the_estimate():
    rain = WeatherReport(2.0, 2.0, False)
    shed = Place("shed", 0.0, 0.0, attention={"camera": 0.0})
    # Camera sees a wrong box (a reflection placing the person 4 m away, not 10 m).
    readings = [
        Reading("camera", camera_estimate(camera_box_at(4.0), HFOV, VFOV)),
        Reading("companion_gnss", Estimate(10.0, 0.0, 1.0)),
    ]
    fused, status, _ = run_tick(readings, Conditions(weather=rain), places=[shed])
    assert fused.x == pytest.approx(10.0, abs=0.01)  # camera fully discounted by the place
    assert status.mode is Mode.TRACKING


def test_total_loss_walks_down_the_fallback_ladder():
    machine = ModeMachine(dead_reckon_ticks=2, hold_ticks=4)
    ctrl = FollowController()
    conditions = Conditions(weather=WeatherReport(0.0, 0.0, False))
    modes = []
    for _ in range(6):
        _, status, cmd = run_tick([], conditions, machine=machine, ctrl=ctrl)
        modes.append(status.mode)
        assert cmd == Command(0.0, 0.0, 0.0)  # never chase when lost
    assert modes == [
        Mode.DEAD_RECKONING,
        Mode.DEAD_RECKONING,
        Mode.HOLD,
        Mode.HOLD,
        Mode.RETURN_HOME_REQUESTED,
        Mode.RETURN_HOME_REQUESTED,
    ]


def test_sources_that_disagree_badly_leave_no_consensus():
    clear = WeatherReport(0.0, 0.0, False)
    readings = [
        Reading("camera", Estimate(10.0, 0.0, 0.5)),
        Reading("companion_gnss", Estimate(-30.0, 0.0, 0.5)),
    ]
    fused, status, _ = run_tick(readings, Conditions(weather=clear))
    assert fused is None
    assert status.mode is Mode.DEAD_RECKONING


def test_active_places_selection_feeds_attention():
    # Place is 100 m north; rider heading south toward it, so the profile applies.
    lat = 100 / 111195.0
    place = Place("shed", 0.0, 0.0, attention={"camera": 0.1})
    active = active_places([place], lat, 0.0, heading_deg=180)
    clear = WeatherReport(0.0, 0.0, False)
    assert attention(Conditions(weather=clear), combined_attention(active))["camera"] == pytest.approx(0.1)
