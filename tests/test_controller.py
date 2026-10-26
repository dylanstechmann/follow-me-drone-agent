import pytest

from follow_me.controller import Command, Detection, FollowController


def test_centered_and_at_distance_gives_no_command():
    ctrl = FollowController()
    cmd = ctrl.update(Detection(cx=0.5, cy=0.5, height=0.35))
    assert cmd == Command(0.0, 0.0, 0.0)


def test_person_right_of_center_yaws_right():
    cmd = FollowController().update(Detection(cx=0.8, cy=0.5, height=0.35))
    assert cmd.yaw > 0
    assert cmd.forward == 0.0


def test_person_left_of_center_yaws_left():
    cmd = FollowController().update(Detection(cx=0.2, cy=0.5, height=0.35))
    assert cmd.yaw < 0


def test_small_box_means_too_far_so_approach():
    cmd = FollowController().update(Detection(cx=0.5, cy=0.5, height=0.1))
    assert cmd.forward > 0


def test_large_box_means_too_close_so_back_off():
    cmd = FollowController().update(Detection(cx=0.5, cy=0.5, height=0.8))
    assert cmd.forward < 0


def test_person_low_in_frame_descends_to_recenter():
    # Person low in frame means the drone is too high relative to them: descend.
    cmd = FollowController().update(Detection(cx=0.5, cy=0.9, height=0.35))
    assert cmd.climb < 0


def test_person_high_in_frame_climbs_to_recenter():
    cmd = FollowController().update(Detection(cx=0.5, cy=0.1, height=0.35))
    assert cmd.climb > 0


def test_deadband_suppresses_jitter():
    ctrl = FollowController(deadband=0.05)
    cmd = ctrl.update(Detection(cx=0.52, cy=0.52, height=0.36))
    assert cmd == Command(0.0, 0.0, 0.0)


def test_commands_are_clamped():
    cmd = FollowController(gain=100.0).update(Detection(cx=1.0, cy=0.0, height=0.0))
    assert -1.0 <= cmd.yaw <= 1.0
    assert -1.0 <= cmd.forward <= 1.0
    assert -1.0 <= cmd.climb <= 1.0


def test_brief_loss_stops_the_drone():
    ctrl = FollowController(lost_frames_before_stop=3)
    assert ctrl.update(None) == Command(0.0, 0.0, 0.0)
    assert ctrl.update(None) == Command(0.0, 0.0, 0.0)


def test_detection_resets_loss_counter():
    ctrl = FollowController(lost_frames_before_stop=2)
    ctrl.update(None)
    ctrl.update(Detection(cx=0.5, cy=0.5, height=0.35))
    assert ctrl._lost_frames == 0


@pytest.mark.parametrize("cx", [0.0, 0.25, 0.75, 1.0])
def test_yaw_sign_is_antisymmetric_about_center(cx):
    left = FollowController().update(Detection(cx=cx, cy=0.5, height=0.35)).yaw
    mirror = FollowController().update(Detection(cx=1 - cx, cy=0.5, height=0.35)).yaw
    assert left == pytest.approx(-mirror)


def test_feed_forward_adds_to_the_forward_command_beyond_the_band():
    ctrl = FollowController()
    far = Detection(cx=0.5, cy=0.5, height=0.2)  # well beyond the band
    assert ctrl.update(far, forward_feed=0.3).forward == pytest.approx(ctrl.update(far).forward + 0.3)


def test_approaching_feed_fades_out_across_the_band_but_backing_off_does_not():
    ctrl = FollowController()
    edge_far = Detection(cx=0.5, cy=0.5, height=0.30)  # the band's far edge: full feed
    middle = Detection(cx=0.5, cy=0.5, height=0.35)
    edge_near = Detection(cx=0.5, cy=0.5, height=0.40)  # the near edge: none
    assert ctrl.update(edge_far, forward_feed=0.4).forward == pytest.approx(0.4)
    assert ctrl.update(middle, forward_feed=0.4).forward == pytest.approx(0.2)
    assert ctrl.update(edge_near, forward_feed=0.4).forward == pytest.approx(0.0)
    assert ctrl.update(edge_near, forward_feed=-0.4).forward == pytest.approx(-0.4)


def test_feed_forward_never_acts_without_a_detection():
    assert FollowController().update(None, forward_feed=0.5) == Command(0.0, 0.0, 0.0)
