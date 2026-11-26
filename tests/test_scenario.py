"""Focused checks for the independent, synthetic 3D scenario sandbox."""

from dataclasses import FrozenInstanceError, asdict, replace
import json
import math

import pytest

from follow_me.scenario import (
    GRIPPER_TO_TARGET,
    MODEL_NOTE,
    OBJECT_SPECS,
    PRESET_IDS,
    SCENARIO_FORMAT,
    ScenarioConfig,
    Vec3,
    get_preset,
    make_sandbox,
    preset_catalog,
    run_preset,
    run_scenario,
    sandbox_config,
    trace_scenario,
)


RETRIEVAL_PRESETS = (
    "soccer_land",
    "soccer_water",
    "indoor_soda",
    "pennyboard_land",
    "object_sandbox",
)
PHASES = [
    "approach", "align", "descend", "extend", "grasp", "lift", "carry", "release", "complete"
]


def phase_sequence(result):
    return [phase for index, phase in enumerate(f.phase for f in result.frames)
            if index == 0 or phase != result.frames[index - 1].phase]


def test_preset_catalog_is_complete_and_immutable():
    assert PRESET_IDS == (
        "follow_ride", "soccer_land", "soccer_water", "indoor_soda", "pennyboard_land", "object_sandbox"
    )
    assert tuple(preset_catalog()) == PRESET_IDS
    assert get_preset("follow_ride").mode == "follow"
    assert all(config.model_note == MODEL_NOTE for config in preset_catalog().values())
    assert all(spec.illustrative for spec in OBJECT_SPECS.values())
    with pytest.raises(FrozenInstanceError):
        get_preset("soccer_land").surface = "land"
    with pytest.raises(ValueError, match="unknown scenario preset"):
        get_preset("real_lake")


def test_every_preset_and_trace_is_deterministic():
    for preset_id in PRESET_IDS:
        first = run_scenario(preset_id)
        second = run_scenario(preset_id)
        assert first == second
        assert asdict(first) == asdict(second)
        assert trace_scenario(preset_id) == trace_scenario(preset_id)
        assert len(first.frames) < 1200


@pytest.mark.parametrize("preset_id", RETRIEVAL_PRESETS)
def test_default_retrievals_follow_the_mission_sequence_and_release_at_the_drop_zone(preset_id):
    result = run_scenario(preset_id)
    summary = result.summary
    assert summary.success is True
    assert summary.final_phase == "complete"
    assert summary.pickup_achieved and summary.released
    assert summary.frame_count < 1200
    assert phase_sequence(result) == PHASES

    attached = [frame for frame in result.frames if frame.target.attached]
    assert attached
    assert {frame.phase for frame in attached} >= {"grasp", "lift", "carry"}
    for frame in attached:
        expected = frame.tentacle.tip_position + GRIPPER_TO_TARGET
        assert frame.target.position.distance(expected) == pytest.approx(0.0, abs=1e-9)
        assert frame.tentacle.grasped
    last = result.frames[-1]
    assert not last.target.attached and not last.tentacle.grasped
    assert last.target.position.x == pytest.approx(result.config.drop_zone.x)
    assert last.target.position.y == pytest.approx(result.config.drop_zone.y)
    assert last.target.position.z == pytest.approx(
        result.config.drop_zone.z + last.target.dimensions_m.z / 2
    )
    assert summary.drop_error_m == pytest.approx(0.0, abs=1e-9)
    kinds = {event.kind for event in result.events}
    assert {"phase", "grasp", "release", "complete"} <= kinds
    assert all(event.message.strip() for event in result.events)


def test_submerged_soccer_uses_wet_waterproof_tentacle_while_drone_stays_dry():
    result = run_scenario("soccer_water")
    assert result.frames[0].target.in_water
    assert result.frames[0].target.submersion_depth_m == pytest.approx(0.25)
    assert result.summary.water_contact
    assert not result.summary.drone_water_contact
    assert result.summary.max_tentacle_depth_m > 0.0
    assert all(frame.drone_flight.position.z > 0.0 for frame in result.frames)
    assert all(not frame.drone_flight.in_water for frame in result.frames)
    wet = [frame for frame in result.frames if frame.tentacle.in_water]
    assert wet and all(frame.tentacle.waterproof for frame in wet)
    assert any(frame.tentacle.submersion_depth_m > 0.1 for frame in wet)
    assert any(event.kind == "water_contact" and "drone body remains above" in event.message
               for event in result.events)
    assert result.frames[-1].target.position.z > 0
    assert not result.frames[-1].target.in_water
    assert "zero drag" in result.summary.model_note
    assert "Not flight validation" in result.summary.model_note


def test_non_waterproof_water_mission_stops_before_submerging_or_pickup():
    result = run_preset("soccer_water", waterproof=False)
    assert not result.summary.success
    assert result.summary.final_phase == "stopped"
    assert "waterproof" in result.summary.reason and "before submerging" in result.summary.reason
    assert not result.summary.pickup_achieved and not result.summary.released
    assert not result.summary.water_contact
    assert len(result.frames) == 1
    assert result.frames[0].phase == "stopped"
    assert result.frames[0].tentacle.submersion_depth_m == 0.0
    assert not any(event.kind == "grasp" for event in result.events)


def test_overweight_generic_object_is_rejected_without_false_pickup():
    config = sandbox_config("object", generic_mass_kg=12.0)
    result = run_scenario(config)
    assert not result.summary.success
    assert result.summary.final_phase == "stopped"
    assert "payload 12 kg exceeds max payload 3 kg" in result.summary.reason
    assert not result.summary.pickup_achieved
    assert not any(frame.target.attached for frame in result.frames)


def test_indoor_soda_and_land_pennyboard_keep_their_independent_settings():
    soda = run_scenario("indoor_soda")
    assert soda.summary.success
    assert (soda.summary.target_kind, soda.summary.setting, soda.summary.surface) == (
        "soda_can", "indoor", "land"
    )
    assert soda.frames[0].target.mass_kg == pytest.approx(0.39)
    board = run_scenario("pennyboard_land")
    assert board.summary.success
    assert (board.summary.target_kind, board.summary.setting, board.summary.surface) == (
        "pennyboard", "outdoor", "land"
    )
    assert board.frames[0].target.dimensions_m.x == pytest.approx(0.57)
    assert not board.summary.water_contact


@pytest.mark.parametrize("kind", ["soccer_ball", "soda_can", "pennyboard", "object"])
@pytest.mark.parametrize("setting", ["indoor", "outdoor"])
@pytest.mark.parametrize("surface", ["land", "water"])
@pytest.mark.parametrize("waterproof", [False, True])
def test_sandbox_combines_object_setting_surface_and_waterproof_independently(
    kind, setting, surface, waterproof
):
    config = sandbox_config(kind, setting, surface, waterproof)
    result = run_scenario(config)
    assert (result.summary.target_kind, result.summary.setting, result.summary.surface) == (
        kind, setting, surface
    )
    if surface == "water" and not waterproof:
        assert not result.summary.success
        assert "waterproof" in result.summary.reason
    else:
        assert result.summary.success
        assert result.summary.drop_error_m == pytest.approx(0.0, abs=1e-9)
        assert result.summary.released


def test_generic_alias_and_custom_small_object_are_supported():
    config = make_sandbox(
        "generic_object", "indoor", "land", False,
        generic_mass_kg=0.4, generic_dimensions_m=Vec3(0.1, 0.07, 0.05),
    )
    result = run_scenario(config)
    assert result.summary.success
    assert result.frames[0].target.kind == "object"
    assert result.frames[0].target.mass_kg == pytest.approx(0.4)
    assert not result.frames[0].tentacle.waterproof


def test_follow_footage_is_finite_in_frame_and_explicitly_consensual():
    result = run_scenario("follow_ride")
    assert result.summary.success
    assert result.summary.follow_frames == len(result.frames)
    assert result.summary.follow_in_frame_share == pytest.approx(1.0)
    assert result.summary.follow_mean_framing_error == pytest.approx(0.0)
    assert result.summary.consenting_synthetic_rider is True
    for frame in result.frames:
        assert frame.follow is not None
        assert frame.follow.synthetic and frame.follow.consent_given
        assert "synthetic rider" in frame.follow.consent_note
        assert "bystanders" in frame.follow.bystander_privacy
        assert frame.camera_framing.target_visible and frame.camera_framing.in_frame
        assert math.isfinite(frame.camera_framing.normalized_error)
        assert all(math.isfinite(value) for value in frame.camera_framing.target_uv)
        assert frame.onboard_camera_pose.position != frame.viewer_orbit_camera.position
        assert frame.drone_flight.position != frame.onboard_camera_pose.position
        distance = frame.drone_flight.position.distance(frame.follow.rider_position)
        assert 6.0 <= distance <= 7.0
        assert frame.target.kind == "pennyboard" and not frame.target.attached
    assert not any(event.kind == "grasp" for event in result.events)


def test_follow_without_consent_never_starts():
    result = run_preset("follow_ride", rider_consent=False)
    assert not result.summary.success
    assert result.summary.final_phase == "stopped"
    assert "consent" in result.summary.reason
    assert len(result.frames) == 1
    assert result.frames[0].follow is None


def test_serialization_is_plain_json_and_preserves_explicit_camera_names():
    for preset_id in PRESET_IDS:
        trace = trace_scenario(preset_id)
        encoded = json.dumps(trace, allow_nan=False, sort_keys=True)
        decoded = json.loads(encoded)
        assert decoded["format"] == SCENARIO_FORMAT
        assert decoded["summary"]["target_kind"] == get_preset(preset_id).target_kind
        assert decoded["frames"][0]["drone_flight"]["position"].keys() == {"x", "y", "z"}
        assert "onboard_camera_pose" in decoded["frames"][0]
        assert "viewer_orbit_camera" in decoded["frames"][0]
        assert '"lat"' not in encoded and '"lon"' not in encoded


@pytest.mark.parametrize("overrides, message", [
    ({"setting": "garage"}, "setting"),
    ({"surface": "mud"}, "surface"),
    ({"target_kind": "person"}, "target_kind"),
    ({"mode": "unknown"}, "mode"),
    ({"dt_s": 0.0}, "dt_s"),
    ({"dt_s": math.nan}, "dt_s"),
    ({"max_frames": 0}, "max_frames"),
    ({"max_frames": 1.5}, "max_frames"),
    ({"generic_mass_kg": -1}, "positive"),
    ({"generic_dimensions_m": Vec3(0.1, 0, 0.1)}, "dimensions"),
    ({"world_min": Vec3(1, 0, 0), "world_max": Vec3(0, 1, 1)}, "world_min"),
])
def test_malformed_or_invalid_settings_are_refused(overrides, message):
    with pytest.raises(ValueError, match=message):
        replace(get_preset("object_sandbox"), **overrides)


def test_invalid_api_inputs_are_clear():
    with pytest.raises(ValueError, match="target_kind"):
        sandbox_config("person")
    with pytest.raises(ValueError, match="unknown sandbox settings"):
        sandbox_config(water_proof=True)
    with pytest.raises(TypeError, match="ScenarioConfig"):
        run_scenario({"preset_id": "soccer_land"})
    with pytest.raises(ValueError, match="unknown scenario overrides"):
        run_preset("soccer_land", imaginary=True)


def test_grip_reach_drop_zone_and_frame_limit_checks_stop_cleanly():
    too_wide = run_preset("soccer_land", max_grip_width_m=0.05)
    assert not too_wide.summary.success and "grip width" in too_wide.summary.reason
    out_of_reach = run_preset("soccer_land", tentacle_reach_m=0.1, carry_extension_m=0.05)
    assert not out_of_reach.summary.success and "required reach" in out_of_reach.summary.reason
    bad_drop = run_preset("soccer_land", drop_zone=Vec3(500, 0, 0))
    assert not bad_drop.summary.success and "drop zone" in bad_drop.summary.reason
    for result in (too_wide, out_of_reach, bad_drop):
        assert result.summary.final_phase == "stopped"
        assert not result.summary.pickup_achieved
        assert not any(frame.target.attached for frame in result.frames)
    limited = run_scenario("soccer_land", max_frames=2)
    assert not limited.summary.success and "frame limit" in limited.summary.reason
    assert limited.summary.final_phase == "stopped"


def test_fixed_dt_override_is_deterministic_and_default_missions_stay_bounded():
    coarse = run_scenario("indoor_soda", dt_s=0.2)
    again = run_scenario("indoor_soda", dt_s=0.2)
    assert coarse == again
    assert coarse.summary.success
    assert coarse.summary.frame_count < 1200
    assert all(frame.drone_flight.position.z >= 0 for frame in coarse.frames)
