import pytest

from follow_me.fusion import Estimate
from follow_me.mode import Mode, ModeMachine


def good(var=1.0):
    return Estimate(10.0, 0.0, var)


def first_time_in(machine, mode, dt, until=60.0):
    """Lose the estimate after t=0 and return the first tick time spent in `mode`."""
    machine.step(good(), now=0.0)
    for k in range(1, int(until / dt) + 1):
        if machine.step(None, now=k * dt).mode is mode:
            return k * dt
    return None


def test_good_estimate_is_tracking_at_full_gain():
    s = ModeMachine().step(good(), now=0.0)
    assert s.mode is Mode.TRACKING
    assert s.gain_scale == 1.0


def test_high_variance_is_degraded_at_half_gain():
    s = ModeMachine(degraded_variance=4.0).step(good(var=9.0), now=0.0)
    assert s.mode is Mode.DEGRADED
    assert s.gain_scale == 0.5


def test_short_loss_is_dead_reckoning_and_may_hold_last_command():
    m = ModeMachine(dead_reckon_s=3.0, return_home_s=10.0)
    m.step(good(), now=0.0)
    s = m.step(None, now=1.0)
    assert s.mode is Mode.DEAD_RECKONING
    assert s.hold_last_command is True
    assert s.gain_scale == 0.0


def test_longer_loss_is_hold_without_holding_command():
    m = ModeMachine(dead_reckon_s=2.0, return_home_s=5.0)
    m.step(good(), now=0.0)
    assert m.step(None, now=2.0).mode is Mode.DEAD_RECKONING  # the limit itself still counts
    s = m.step(None, now=2.5)
    assert s.mode is Mode.HOLD
    assert s.hold_last_command is False


def test_very_long_loss_requests_return_home():
    m = ModeMachine(dead_reckon_s=2.0, return_home_s=4.0)
    m.step(good(), now=0.0)
    assert m.step(None, now=4.0).mode is Mode.HOLD
    s = m.step(None, now=4.5)
    assert s.mode is Mode.RETURN_HOME_REQUESTED
    assert s.request_return_home is True


def test_reacquiring_resets_the_loss_timer():
    m = ModeMachine(dead_reckon_s=2.0, return_home_s=4.0)
    m.step(None, now=0.0)
    assert m.step(None, now=3.0).mode is Mode.HOLD
    m.step(good(), now=3.5)
    assert m.step(None, now=5.0).mode is Mode.DEAD_RECKONING


@pytest.mark.parametrize("dt", [0.1, 0.5, 2.5])
def test_timing_follows_seconds_not_the_loop_rate(dt):
    # Ten ticks a second or one every 2.5 s: hold starts after 5 s and return-home
    # after 50 s, at the first tick past each limit.
    hold = first_time_in(ModeMachine(), Mode.HOLD, dt)
    home = first_time_in(ModeMachine(), Mode.RETURN_HOME_REQUESTED, dt)
    assert 5.0 < hold <= 5.0 + dt + 1e-9
    assert 50.0 < home <= 50.0 + dt + 1e-9


def test_a_loss_with_no_estimate_yet_is_timed_from_the_first_tick():
    m = ModeMachine(dead_reckon_s=1.0, return_home_s=3.0)
    modes = [m.step(None, now=t).mode for t in (10.0, 11.0, 12.0, 14.0)]
    assert modes == [Mode.DEAD_RECKONING, Mode.DEAD_RECKONING, Mode.HOLD, Mode.RETURN_HOME_REQUESTED]


def test_tick_times_must_not_go_backwards():
    m = ModeMachine()
    m.step(None, now=5.0)
    with pytest.raises(ValueError, match="backwards"):
        m.step(None, now=4.0)


@pytest.mark.parametrize("dead_reckon_s, return_home_s", [(10.0, 5.0), (0.0, 5.0), (5.0, 5.0)])
def test_thresholds_must_be_ordered(dead_reckon_s, return_home_s):
    with pytest.raises(ValueError):
        ModeMachine(dead_reckon_s=dead_reckon_s, return_home_s=return_home_s)
