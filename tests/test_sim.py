"""The kinematic follow simulation: a point drone flown by the council's commands."""

import itertools
import json
import math

import pytest

from follow_me.controller import Command
from follow_me.council import Council
from follow_me.mode import Mode
from follow_me.sim import (
    PERSON_HEIGHT_M,
    DroneState,
    Limits,
    RiderFix,
    default_start,
    follow_band,
    simulate,
    summarize,
    trace_track,
)


def standing(east, north, seconds=60.0, accuracy=1.0, every=0.5):
    return [RiderFix(k * every, east, north, accuracy) for k in range(int(seconds / every) + 1)]


def legs(*parts, every=1.0, accuracy=1.0):
    """A track from (seconds, speed, heading) legs, one fix every `every` seconds."""
    fixes, east, north, t = [RiderFix(0.0, 0.0, 0.0, accuracy)], 0.0, 0.0, 0.0
    for seconds, speed, heading in parts:
        for _ in range(int(round(seconds / every))):
            t += every
            east += speed * every * math.sin(math.radians(heading))
            north += speed * every * math.cos(math.radians(heading))
            fixes.append(RiderFix(round(t, 3), east, north, accuracy))
    return fixes


def path_length(ticks):
    return sum(math.hypot(b.drone.east - a.drone.east, b.drone.north - a.drone.north) for a, b in zip(ticks, ticks[1:]))


def moving(speed, heading_deg=0.0, seconds=120.0, accuracy=1.0, every=0.5):
    h = math.radians(heading_deg)
    return [
        RiderFix(k * every, speed * k * every * math.sin(h), speed * k * every * math.cos(h), accuracy)
        for k in range(int(seconds / every) + 1)
    ]


def runs(ticks):
    return [(mode, len(list(group))) for mode, group in itertools.groupby(s.result.mode for s in ticks)]


def test_follow_band_comes_from_the_controller_deadband():
    near, far = follow_band(Council())
    # Box heights of 0.40 and 0.30 of the frame, for a 1.75 m person and a 60 degree camera.
    assert near == pytest.approx(3.79, abs=0.01)
    assert far == pytest.approx(5.05, abs=0.01)


def test_standing_rider_is_approached_and_held_at_the_band_edge():
    ticks = simulate(standing(0.0, 20.0), start=DroneState(0.0, 0.0, 0.0))
    near, far = follow_band(Council())
    assert ticks[0].distance == pytest.approx(20.0)
    settled = [s.distance for s in ticks if s.t >= 20.0]
    # The command ramps to zero at the band edge, so the drone stops just outside it.
    assert all(far <= d <= far + 0.05 for d in settled)
    assert all(s.result.mode is Mode.TRACKING for s in ticks)


def test_rider_to_one_side_is_turned_toward():
    ticks = simulate(standing(20.0, 0.0), start=DroneState(0.0, 0.0, 0.0))
    assert ticks[0].flown.yaw > 0  # the rider is due east, on the right: turn right
    # At the end the rider sits at the edge of the yaw deadband, 0.05 of a 90 degree
    # frame, where the turn command ramps down to zero.
    assert abs(math.degrees(ticks[-1].result.estimate.bearing)) == pytest.approx(4.5, abs=0.01)


# Without feed-forward: the controller as it was before iteration 27. These tests keep
# the findings of iteration 21 as a record and for the website's comparison.
P_ONLY = dict(feed_forward=False)


@pytest.mark.parametrize("speed", [2.0, 3.0, 4.0])
def test_without_feed_forward_a_moving_rider_is_trailed_at_the_distance_the_gain_predicts(speed):
    # The controller acts on distance alone, so the drone settles where the forward
    # command times the top speed equals the rider's speed: 7.6 m behind at 2 m/s,
    # 10.1 m at 3 m/s, 15.2 m at 4 m/s.
    council, limits = Council(**P_ONLY), Limits()
    ctrl = council.controller
    ticks = simulate(moving(speed, seconds=180.0), council=council, limits=limits)
    h = ctrl.target_height - ctrl.deadband - speed / (limits.max_speed_mps * ctrl.gain)
    expected = PERSON_HEIGHT_M / (2 * h * math.tan(council.vfov_rad / 2))
    late = [s.distance for s in ticks if s.t >= 120.0]
    assert min(late) == pytest.approx(expected, rel=0.01)
    assert max(late) == pytest.approx(expected, rel=0.01)


def test_without_feed_forward_a_rider_faster_than_the_command_ceiling_pulls_away():
    # The forward command tops out at gain * (target_height - deadband) = 0.6, so the
    # point drone never passes 6 m/s with the 10 m/s placeholder limit.
    ticks = simulate(moving(7.0, seconds=60.0), council=Council(**P_ONLY))
    d = [s.distance for s in ticks]
    assert d[-1] > d[len(d) // 2] > d[20]
    assert max(abs(s.flown.forward) for s in ticks) <= 0.6 + 1e-9


def test_without_feed_forward_a_phone_alone_is_degraded_and_halves_the_speed():
    # A 4 m fix has a 16 m^2 variance, above the 9 m^2 threshold, so every tick is
    # degraded at half gain: a 2 m/s rider is trailed as far as a 4 m/s one at full gain.
    phone = simulate(moving(2.0, accuracy=4.0, seconds=180.0), council=Council(**P_ONLY))
    assert {s.result.mode for s in phone} == {Mode.DEGRADED}
    clean = simulate(moving(4.0, accuracy=1.0, seconds=180.0), council=Council(**P_ONLY))
    assert phone[-1].distance == pytest.approx(clean[-1].distance, rel=0.01)


def test_stale_fixes_give_no_reading():
    fixes = [RiderFix(0.0, 0.0, 10.0, 1.0), RiderFix(10.0, 0.0, 10.0, 1.0)]
    ticks = simulate(fixes, start=DroneState(0.0, 0.0, 0.0))
    # A fix is used for up to 2 s, as in companion.py.
    assert [s.t for s in ticks if s.readings] == [0.0, 0.5, 1.0, 1.5, 2.0, 10.0]


def test_dead_reckoning_keeps_the_last_command_and_hold_stops():
    fixes = [f for f in moving(3.0, seconds=90.0) if not 10.0 < f.t < 70.0]
    ticks = simulate(fixes)
    assert runs(ticks)[:4] == [
        (Mode.TRACKING, 25),  # 0 to 12 s: the last fix stays fresh for 2 s
        (Mode.DEAD_RECKONING, 10),
        (Mode.HOLD, 90),
        (Mode.RETURN_HOME_REQUESTED, 15),
    ]
    last_tracked = ticks[24].flown
    assert last_tracked != Command(0.0, 0.0, 0.0)
    assert all(s.flown == last_tracked for s in ticks[25:35])
    assert all(s.flown.forward == 0 and s.flown.yaw == 0 for s in ticks[35:140])


def test_default_start_is_behind_the_rider_facing_the_way_they_go():
    council = Council()
    near, far = follow_band(council)
    start = default_start(moving(3.0, heading_deg=90.0), council)
    assert start.heading_deg == pytest.approx(90.0)
    assert start.east == pytest.approx(-(near + far) / 2)
    assert start.north == pytest.approx(0.0, abs=1e-9)


def test_same_track_gives_the_same_trace():
    fixes = moving(3.0, heading_deg=30.0, seconds=20.0)
    assert trace_track(fixes) == trace_track(fixes)


def test_trace_carries_the_world_and_a_summary():
    trace = trace_track(moving(3.0, seconds=30.0), note="made up")
    assert trace["kind"] == "simulation"
    assert trace["note"] == "made up"
    assert trace["settings"]["dt_s"] == 0.5
    assert trace["settings"]["max_speed_mps"] == 10.0
    first = trace["ticks"][0]
    assert set(first["world"]) == {"drone", "rider", "distance", "flown"}
    assert first["readings"][0]["source"] == "phone_gnss"
    summary = trace["summary"]
    assert summary["band_m"] == [3.79, 5.05]
    assert summary["seconds_in_mode"] == {"tracking": 30.5}
    assert summary["return_home_requested"] is False
    text = json.dumps(trace)
    assert '"lat' not in text and '"lon' not in text


def test_summary_counts_seconds_and_the_share_in_the_band():
    council = Council()
    ticks = simulate(standing(0.0, 4.4, seconds=10.0), council=council, start=DroneState(0.0, 0.0, 0.0))
    summary = summarize(ticks, council, 0.5)
    assert summary["duration_s"] == 10.0
    assert summary["in_band_share"] == 1.0
    assert summary["median_distance_m"] == pytest.approx(4.4)


@pytest.mark.parametrize("fixes, dt, message", [
    ([RiderFix(0.0, 0.0, 0.0, 1.0)], 0.5, "two fixes"),
    ([RiderFix(0.0, 0.0, 0.0, 1.0), RiderFix(0.0, 1.0, 0.0, 1.0)], 0.5, "increase"),
    ([RiderFix(0.0, 0.0, 0.0, 1.0), RiderFix(1.0, 1.0, 0.0, 0.0)], 0.5, "accuracy"),
    ([RiderFix(0.0, 0.0, 0.0, 1.0), RiderFix(1.0, 1.0, 0.0, 1.0)], 0.0, "dt"),
])
def test_bad_tracks_are_refused(fixes, dt, message):
    with pytest.raises(ValueError, match=message):
        simulate(fixes, dt=dt)


def test_fallback_timing_is_the_same_at_two_loop_rates():
    # The mode machine times losses in seconds, so a 10 Hz loop and a 2 Hz loop reach
    # hold and return-home at the same time, within one tick, after the fixes stop at 10 s.
    fixes = [f for f in moving(3.0, seconds=90.0) if not 10.0 < f.t < 70.0]

    def first(ticks, mode):
        return next(s.t for s in ticks if s.result.mode is mode)

    slow, fast = simulate(fixes, dt=0.5), simulate(fixes, dt=0.1)
    for mode, expected in [(Mode.DEAD_RECKONING, 12.0), (Mode.HOLD, 17.0), (Mode.RETURN_HOME_REQUESTED, 62.0)]:
        for ticks, dt in [(slow, 0.5), (fast, 0.1)]:
            assert expected < first(ticks, mode) <= expected + dt + 1e-9


# With feed-forward (iteration 27). Fixes once a second, like a phone.

@pytest.mark.parametrize("speed", [2.0, 3.0, 4.0, 5.0])
def test_feed_forward_keeps_a_moving_rider_near_the_band(speed):
    near, far = follow_band(Council())
    late = [s.distance for s in simulate(legs((150, speed, 0))) if s.t >= 100]
    assert far <= min(late) and max(late) <= 8.5  # was 8 to 31 m behind without it
    old = [s.distance for s in simulate(legs((150, speed, 0)), council=Council(**P_ONLY)) if s.t >= 100]
    assert max(late) < min(old)


def test_feed_forward_keeps_up_past_the_old_ceiling():
    late = [s.distance for s in simulate(legs((120, 7.0, 0))) if s.t >= 60]
    assert max(late) < 12.0  # without it the drone falls behind without limit


def test_a_rider_who_stops_suddenly_is_not_run_into():
    # The speed estimate takes a moment to fall after a stop. The approaching part of
    # the feed-forward fades across the band, so the drone stays clear of the rider.
    near, far = follow_band(Council())
    ticks = simulate(legs((40, 4.0, 0), (30, 0.0, 0)))
    after = [s for s in ticks if s.t >= 40]
    assert min(s.distance for s in after) >= 3.0
    assert near - 0.1 <= after[20].distance <= far + 0.1  # settled 10 s after the stop


def test_a_turning_rider_is_followed_without_a_large_overshoot():
    ticks = simulate(legs((40, 4.0, 0), (60, 4.0, 90)))
    after = [s.distance for s in ticks if s.t >= 40]
    assert max(after) < 9.0 and min(after) > 3.5


def test_feed_forward_does_not_make_noisy_fixes_much_worse():
    # A standing rider, with made-up 3 m errors on each fix. The drone chases the noise
    # with or without feed-forward (see simulation.md); feed-forward may add a little.
    fixes = [RiderFix(float(k), 0.0, 20.0, 3.0) for k in range(121)]
    for seed in range(3):
        new = path_length(simulate(fixes, noise_m=3.0, seed=seed))
        old = path_length(simulate(fixes, council=Council(**P_ONLY), noise_m=3.0, seed=seed))
        assert new <= 1.25 * old


def test_degraded_still_halves_the_whole_command():
    # A phone-like 4 m fix keeps every tick degraded; the gain scales the feed-forward too.
    ticks = simulate(legs((150, 2.0, 0), accuracy=4.0))
    assert {s.result.mode for s in ticks} == {Mode.DEGRADED}
    assert all(abs(s.result.command.forward) <= 0.5 + 1e-9 for s in ticks)


def test_noise_is_drawn_once_per_fix_and_repeatable():
    fixes = [RiderFix(float(k), 0.0, 20.0, 3.0) for k in range(11)]
    a = simulate(fixes, noise_m=3.0, seed=4)
    b = simulate(fixes, noise_m=3.0, seed=4)
    assert [s.drone for s in a] == [s.drone for s in b]
    assert a[0].rider == (0.0, 20.0)  # the track stays the truth
    with pytest.raises(ValueError):
        simulate(fixes, noise_m=-1.0)


def test_summary_reports_the_closest_approach():
    council = Council()
    ticks = simulate(standing(0.0, 20.0), council=council, start=DroneState(0.0, 0.0, 0.0))
    assert summarize(ticks, council, 0.5)["min_distance_m"] == pytest.approx(min(s.distance for s in ticks), abs=0.01)
