import pytest

from follow_me.fusion import Estimate
from follow_me.mode import Mode, ModeMachine


def good(var=1.0):
    return Estimate(10.0, 0.0, var)


def test_good_estimate_is_tracking_at_full_gain():
    s = ModeMachine().step(good())
    assert s.mode is Mode.TRACKING
    assert s.gain_scale == 1.0


def test_high_variance_is_degraded_at_half_gain():
    s = ModeMachine(degraded_variance=4.0).step(good(var=9.0))
    assert s.mode is Mode.DEGRADED
    assert s.gain_scale == 0.5


def test_short_loss_is_dead_reckoning_and_may_hold_last_command():
    m = ModeMachine(dead_reckon_ticks=3, hold_ticks=10)
    s = m.step(None)
    assert s.mode is Mode.DEAD_RECKONING
    assert s.hold_last_command is True
    assert s.gain_scale == 0.0


def test_longer_loss_is_hold_without_holding_command():
    m = ModeMachine(dead_reckon_ticks=2, hold_ticks=5)
    for _ in range(2):
        m.step(None)
    s = m.step(None)
    assert s.mode is Mode.HOLD
    assert s.hold_last_command is False


def test_very_long_loss_requests_return_home():
    m = ModeMachine(dead_reckon_ticks=2, hold_ticks=4)
    for _ in range(4):
        m.step(None)
    s = m.step(None)
    assert s.mode is Mode.RETURN_HOME_REQUESTED
    assert s.request_return_home is True


def test_reacquiring_resets_the_loss_counter():
    m = ModeMachine(dead_reckon_ticks=2, hold_ticks=4)
    m.step(None)
    m.step(None)
    m.step(good())
    s = m.step(None)
    assert s.mode is Mode.DEAD_RECKONING


def test_thresholds_must_be_ordered():
    with pytest.raises(ValueError):
        ModeMachine(dead_reckon_ticks=10, hold_ticks=5)
