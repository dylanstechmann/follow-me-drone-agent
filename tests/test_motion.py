"""The rider's motion estimate: a constant-velocity Kalman filter in the drone's local frame."""

import math
import random

import pytest

from follow_me.companion import offset_estimate
from follow_me.context import Conditions
from follow_me.council import Council
from follow_me.fusion import Estimate, Reading
from follow_me.motion import Pose, RiderTracker, to_body, to_local


def seen_from(pose, east, north, variance=1.0):
    """The rider at a local east, north position, as the drone at `pose` would estimate it."""
    est = offset_estimate(east - pose.east, north - pose.north, math.sqrt(variance), pose.heading_deg, heading_sigma_rad=1e-9)
    return Estimate(est.x, est.y, variance)


def test_frames_turn_the_right_way():
    facing_east = Pose(10.0, 5.0, 90.0)
    assert to_local(facing_east, Estimate(3.0, 0.0, 1.0)) == pytest.approx((13.0, 5.0))
    assert to_local(facing_east, Estimate(0.0, 2.0, 1.0)) == pytest.approx((10.0, 7.0))  # left of east is north
    assert to_body(facing_east, 3.0, 0.0) == pytest.approx((3.0, 0.0))
    assert to_body(Pose(0.0, 0.0, 0.0), 3.0, 0.0) == pytest.approx((0.0, -3.0))  # east is on the right facing north


def test_rider_speed_converges_from_a_still_drone():
    tracker, drone = RiderTracker(), Pose(0.0, 0.0, 0.0)
    for t in range(21):
        motion = tracker.step(float(t), drone, seen_from(drone, 0.0, 10.0 + 3.0 * t))
    assert motion.forward_mps == pytest.approx(3.0, abs=0.1)
    assert motion.left_mps == pytest.approx(0.0, abs=0.1)
    assert motion.sigma_mps < 0.5 * 5.0  # well below the 5 m/s it starts with


def test_the_drones_own_motion_is_taken_out():
    # The drone flies 5 m behind the rider at the rider's speed, so every estimate says
    # "5 m ahead"; the rider is still moving at 3 m/s over the ground.
    tracker = RiderTracker()
    for t in range(21):
        drone = Pose(0.0, 3.0 * t - 5.0, 0.0)
        motion = tracker.step(float(t), drone, seen_from(drone, 0.0, 3.0 * t))
    assert motion.forward_mps == pytest.approx(3.0, abs=0.1)


def test_a_spinning_drone_does_not_make_a_still_rider_move():
    tracker = RiderTracker()
    for k in range(41):
        drone = Pose(0.0, 0.0, 12.0 * k)  # 24 degrees a second, at 2 ticks a second
        motion = tracker.step(k * 0.5, drone, seen_from(drone, 4.0, 6.0))
    assert motion.speed_mps == pytest.approx(0.0, abs=0.05)


def test_noisier_estimates_leave_a_less_certain_speed():
    rng = random.Random(1)

    def final_sigma(noise):
        tracker, drone = RiderTracker(), Pose(0.0, 0.0, 0.0)
        for t in range(30):
            motion = tracker.step(float(t), drone, seen_from(
                drone, rng.gauss(0.0, noise), 10.0 + rng.gauss(0.0, noise), variance=noise**2))
        return motion.sigma_mps

    assert final_sigma(4.0) > 1.5 * final_sigma(0.5)


def test_the_same_measurement_seen_again_adds_nothing():
    tracker, drone = RiderTracker(), Pose(0.0, 0.0, 0.0)
    for t in range(10):
        first = tracker.step(float(t), drone, seen_from(drone, 0.0, 3.0 * t))
    again = tracker.step(9.5, drone, seen_from(drone, 0.0, 27.0), measured_at=9.0)
    assert (again.forward_mps, again.left_mps) == (first.forward_mps, first.left_mps)
    assert again.sigma_mps > first.sigma_mps  # half a second older


def test_a_one_hertz_fix_on_a_two_hertz_loop_gives_a_steady_speed():
    # Without ages, every repeated fix would look like the rider stopping.
    tracker, speeds = RiderTracker(), []
    for k in range(60):
        t = k * 0.5
        fix_t = math.floor(t)
        drone = Pose(0.0, 0.0, 0.0)
        motion = tracker.step(t, drone, seen_from(drone, 0.0, 3.0 * fix_t), measured_at=float(fix_t))
        speeds.append(motion.forward_mps)
    assert max(speeds[-20:]) - min(speeds[-20:]) < 0.05
    assert speeds[-1] == pytest.approx(3.0, abs=0.1)


def test_nothing_before_the_first_estimate_and_nothing_after_a_long_gap():
    tracker, drone = RiderTracker(max_gap_s=5.0), Pose(0.0, 0.0, 0.0)
    assert tracker.step(0.0, drone, None) is None
    for t in range(1, 11):
        motion = tracker.step(float(t), drone, seen_from(drone, 0.0, 3.0 * t))
    assert tracker.step(13.0, drone, None) is not None  # 3 s without an estimate: still predicting
    assert tracker.step(16.0, drone, None) is None  # 6 s: stale
    fresh = tracker.step(17.0, drone, seen_from(drone, 0.0, 50.0))
    assert fresh.speed_mps == 0.0 and fresh.sigma_mps == pytest.approx(5.0)  # started afresh


def test_tick_times_must_not_go_backwards():
    tracker, drone = RiderTracker(), Pose(0.0, 0.0, 0.0)
    tracker.step(5.0, drone, None)
    with pytest.raises(ValueError, match="backwards"):
        tracker.step(4.0, drone, None)


def test_bad_settings_are_refused():
    with pytest.raises(ValueError):
        RiderTracker(accel_sigma_mps2=0.0)


def test_council_estimates_motion_only_when_given_the_drones_pose():
    reading = [Reading("tag_gnss", Estimate(10.0, 0.0, 1.0))]
    assert Council().tick(reading, Conditions(), now=0.0).motion is None
    council = Council()
    council.tick(reading, Conditions(), now=0.0, pose=Pose(0.0, 0.0, 0.0))
    assert council.tick(reading, Conditions(), now=0.5, pose=Pose(0.0, 0.0, 0.0)).motion is not None


def test_forward_feed_is_the_speed_along_the_nose_shrunk_by_its_uncertainty():
    from follow_me.council import forward_feed
    from follow_me.motion import Motion

    assert forward_feed(None, 10.0) == 0.0
    assert forward_feed(Motion(0.0, 0.0, 1.0), 10.0) == 0.0
    assert forward_feed(Motion(4.0, 0.0, 0.0), 10.0) == pytest.approx(0.4)
    assert forward_feed(Motion(4.0, 0.0, 4.0), 10.0) == pytest.approx(0.2)  # as uncertain as it is fast: half
    assert forward_feed(Motion(0.3, 0.0, 3.0), 10.0) < 0.001  # noise around standing still


def test_without_a_pose_the_commands_are_as_before():
    readings = [Reading("tag_gnss", Estimate(15.0, 2.0, 1.0))]
    for t in (0.0, 0.5, 1.0):
        new = Council().tick(readings, Conditions(), now=t)
        old = Council(feed_forward=False).tick(readings, Conditions(), now=t)
        assert new.command == old.command and new.feed == 0.0
