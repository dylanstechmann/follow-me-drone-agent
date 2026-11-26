"""Deterministic 3D retrieval and consenting-rider scenarios.

This module is an independent, transparent kinematic sandbox for a future UI. It
uses synthetic local metre offsets only (no map coordinates), seconds, kilograms,
and a z-up world. It is not flight validation, an autopilot, or a claim about
hardware. Objects stay still until grasped; illustrative buoyancy holds shallow
water objects at their initial depth and drag is zero. There is no fluid physics.

``drone_flight`` is the aircraft pose, ``onboard_camera_pose`` is its ideal
stabilized camera, and ``viewer_orbit_camera`` is only a suggested external UI
camera. The old 2D ``sim.py``/``motion.py`` contracts are deliberately unused.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, replace
from typing import Any

SCENARIO_FORMAT = "follow-me-scenario-v1"  # SECRETS-GUARD-IGNORE: public format ID
MODEL_NOTE = (
    "Simplified deterministic kinematics in synthetic local offsets; illustrative "
    "object dimensions/masses, fixed-depth buoyancy and zero drag. Not flight "
    "validation, fluid physics, or a hardware capability claim."
)
@dataclass(frozen=True)
class Vec3:
    """A finite 3D vector or position in metres, with z up."""

    x: float
    y: float
    z: float = 0.0

    def __post_init__(self) -> None:
        if not all(math.isfinite(v) for v in (self.x, self.y, self.z)):
            raise ValueError("3D coordinates must be finite")

    def __add__(self, other: "Vec3") -> "Vec3":
        return Vec3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: "Vec3") -> "Vec3":
        return Vec3(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scale: float) -> "Vec3":
        return Vec3(self.x * scale, self.y * scale, self.z * scale)

    def __truediv__(self, scale: float) -> "Vec3":
        return Vec3(self.x / scale, self.y / scale, self.z / scale)

    def dot(self, other: "Vec3") -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other: "Vec3") -> "Vec3":
        return Vec3(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x,
        )

    @property
    def length(self) -> float:
        return math.sqrt(self.dot(self))

    def distance(self, other: "Vec3") -> float:
        return (self - other).length

    def normalized(self) -> "Vec3":
        if self.length <= 1e-12:
            return Vec3(0.0, 0.0, 0.0)
        return self / self.length


GRIPPER_TO_TARGET = Vec3(0.0, 0.0, -0.08)
ZERO = Vec3(0.0, 0.0, 0.0)
UP = Vec3(0.0, 0.0, 1.0)


@dataclass(frozen=True)
class ObjectSpec:
    """Illustrative object properties, not measured hardware specifications."""

    kind: str
    mass_kg: float
    dimensions_m: Vec3  # full x/y/z extents
    description: str
    illustrative: bool = True


OBJECT_SPECS = {
    "soccer_ball": ObjectSpec(
        "soccer_ball", 0.43, Vec3(0.22, 0.22, 0.22), "illustrative size-5 soccer ball"
    ),
    "soda_can": ObjectSpec(
        "soda_can", 0.39, Vec3(0.066, 0.066, 0.122), "illustrative full 330 ml soda can"
    ),
    "pennyboard": ObjectSpec(
        "pennyboard", 2.4, Vec3(0.57, 0.15, 0.10), "illustrative small plastic pennyboard"
    ),
    "object": ObjectSpec(
        "object", 0.25, Vec3(0.12, 0.08, 0.06), "illustrative small generic object"
    ),
}


@dataclass(frozen=True)
class DroneState:
    """The drone's flight pose/state; this is not either camera pose."""

    position: Vec3
    velocity: Vec3 = ZERO
    yaw_deg: float = 0.0
    in_water: bool = False
    submersion_depth_m: float = 0.0


@dataclass(frozen=True)
class TargetObject:
    kind: str
    position: Vec3  # object centre
    dimensions_m: Vec3
    mass_kg: float
    attached: bool = False
    in_water: bool = False
    submersion_depth_m: float = 0.0
    illustrative: bool = True
    object_id: str = "target"


@dataclass(frozen=True)
class TentacleConfig:
    waterproof: bool
    max_reach_m: float = 3.2
    extension_speed_mps: float = 1.0
    carry_extension_m: float = 0.45
    gripper_to_target_m: Vec3 = GRIPPER_TO_TARGET
    model_note: str = "One idealized prismatic tentacle; no contact or fluid dynamics."


@dataclass(frozen=True)
class TentacleState:
    extension_m: float
    tip_position: Vec3
    waterproof: bool
    in_water: bool = False
    submersion_depth_m: float = 0.0
    grasped: bool = False


@dataclass(frozen=True)
class OnboardCameraPose:
    """Ideal stabilized onboard camera, separate from the drone flight pose."""

    position: Vec3
    look_at: Vec3
    up: Vec3 = UP
    horizontal_fov_deg: float = 90.0
    vertical_fov_deg: float = 60.0
    model: str = "ideal stabilized gimbal; no occlusion, lens distortion, or detection noise"


@dataclass(frozen=True)
class CameraFraming:
    target_visible: bool
    in_frame: bool
    normalized_error: float
    target_uv: tuple[float, float] | None
    target_distance_m: float


@dataclass(frozen=True)
class FollowMetadata:
    rider_id: str
    synthetic: bool
    consent_given: bool
    consent_note: str
    rider_position: Vec3
    rider_velocity: Vec3
    bystander_privacy: str = "Synthetic rider only; no bystanders or real footage are represented."


@dataclass(frozen=True)
class ViewerOrbitCamera:
    """Optional external UI camera; never used by the onboard follow logic."""

    position: Vec3
    look_at: Vec3
    orbit_radius_m: float


@dataclass(frozen=True)
class ScenarioEvent:
    t_s: float
    kind: str
    message: str
    phase: str


@dataclass(frozen=True)
class ScenarioConfig:
    """A serializable immutable preset or sandbox configuration."""

    preset_id: str
    mode: str = "retrieval"  # retrieval or follow
    target_kind: str = "object"
    setting: str = "outdoor"  # independently indoor or outdoor
    surface: str = "land"  # independently land or water
    waterproof: bool = True
    target_position: Vec3 | None = None
    generic_mass_kg: float = 0.25
    generic_dimensions_m: Vec3 = Vec3(0.12, 0.08, 0.06)
    initial_drone_position: Vec3 = Vec3(-4.0, -3.0, 4.0)
    drop_zone: Vec3 = Vec3(-5.0, -4.0, 0.0)  # centre of a safe synthetic dry pad
    drop_zone_radius_m: float = 1.0
    world_min: Vec3 = Vec3(-30.0, -30.0, -2.0)
    world_max: Vec3 = Vec3(100.0, 40.0, 20.0)
    dt_s: float = 0.1
    max_frames: int = 1200
    max_payload_kg: float = 3.0
    max_grip_width_m: float = 0.25
    tentacle_reach_m: float = 3.2
    tentacle_speed_mps: float = 1.0
    carry_extension_m: float = 0.45
    cruise_altitude_m: float = 4.0
    pickup_hover_above_target_m: float = 1.0
    min_drone_water_clearance_m: float = 0.8
    horizontal_speed_mps: float = 3.0
    vertical_speed_mps: float = 1.2
    follow_duration_s: float = 24.0
    follow_distance_m: float = 6.0
    follow_altitude_m: float = 3.2
    rider_consent: bool = True
    viewer_orbit: bool = True
    model_note: str = MODEL_NOTE

    def __post_init__(self) -> None:
        if self.mode not in {"retrieval", "follow"}:
            raise ValueError("mode must be 'retrieval' or 'follow'")
        if self.target_kind not in OBJECT_SPECS:
            raise ValueError("target_kind must be soccer_ball, soda_can, pennyboard, or object")
        if self.setting not in {"indoor", "outdoor"}:
            raise ValueError("setting must be 'indoor' or 'outdoor'")
        if self.surface not in {"land", "water"}:
            raise ValueError("surface must be 'land' or 'water'")
        if not math.isfinite(self.dt_s) or self.dt_s <= 0:
            raise ValueError("dt_s must be positive and finite")
        if not isinstance(self.max_frames, int) or isinstance(self.max_frames, bool) or self.max_frames < 1:
            raise ValueError("max_frames must be a positive integer")
        positive = {
            "generic_mass_kg": self.generic_mass_kg,
            "drop_zone_radius_m": self.drop_zone_radius_m,
            "max_payload_kg": self.max_payload_kg,
            "max_grip_width_m": self.max_grip_width_m,
            "tentacle_reach_m": self.tentacle_reach_m,
            "tentacle_speed_mps": self.tentacle_speed_mps,
            "carry_extension_m": self.carry_extension_m,
            "cruise_altitude_m": self.cruise_altitude_m,
            "pickup_hover_above_target_m": self.pickup_hover_above_target_m,
            "min_drone_water_clearance_m": self.min_drone_water_clearance_m,
            "horizontal_speed_mps": self.horizontal_speed_mps,
            "vertical_speed_mps": self.vertical_speed_mps,
            "follow_duration_s": self.follow_duration_s,
            "follow_distance_m": self.follow_distance_m,
            "follow_altitude_m": self.follow_altitude_m,
        }
        if any(not math.isfinite(v) or v <= 0 for v in positive.values()):
            raise ValueError("physical limits, speeds, and durations must be positive and finite")
        if min(self.generic_dimensions_m.x, self.generic_dimensions_m.y, self.generic_dimensions_m.z) <= 0:
            raise ValueError("generic object dimensions must be positive")
        if any(
            a >= b
            for a, b in zip(
                (self.world_min.x, self.world_min.y, self.world_min.z),
                (self.world_max.x, self.world_max.y, self.world_max.z),
            )
        ):
            raise ValueError("world_min must be below world_max on every axis")
        if self.carry_extension_m > self.tentacle_reach_m:
            raise ValueError("carry_extension_m must not exceed tentacle_reach_m")
        if self.mode == "follow" and self.target_kind != "pennyboard":
            raise ValueError("follow mode follows a consenting synthetic rider on a pennyboard")

    def tentacle_config(self) -> TentacleConfig:
        return TentacleConfig(
            waterproof=self.waterproof,
            max_reach_m=self.tentacle_reach_m,
            extension_speed_mps=self.tentacle_speed_mps,
            carry_extension_m=self.carry_extension_m,
        )


@dataclass(frozen=True)
class ScenarioFrame:
    t_s: float
    phase: str
    status: str
    drone_flight: DroneState
    target: TargetObject
    tentacle: TentacleState
    onboard_camera_pose: OnboardCameraPose
    camera_framing: CameraFraming
    follow: FollowMetadata | None
    viewer_orbit_camera: ViewerOrbitCamera | None
    events: tuple[ScenarioEvent, ...] = ()

    @property
    def drone(self) -> DroneState:
        """Short read-only alias for UI callers; the serialized name stays explicit."""
        return self.drone_flight


@dataclass(frozen=True)
class ScenarioSummary:
    success: bool
    reason: str
    duration_s: float
    target_kind: str
    setting: str
    surface: str
    final_phase: str
    frame_count: int
    pickup_achieved: bool
    released: bool
    water_contact: bool
    drone_water_contact: bool
    max_tentacle_depth_m: float
    final_target_position: Vec3
    drop_zone: Vec3
    drop_error_m: float | None
    follow_frames: int = 0
    follow_in_frame_share: float | None = None
    follow_mean_framing_error: float | None = None
    follow_max_framing_error: float | None = None
    consenting_synthetic_rider: bool | None = None
    model_note: str = MODEL_NOTE


@dataclass(frozen=True)
class ScenarioResult:
    config: ScenarioConfig
    frames: tuple[ScenarioFrame, ...]
    events: tuple[ScenarioEvent, ...]
    summary: ScenarioSummary
    format: str = SCENARIO_FORMAT

    def to_dict(self) -> dict[str, Any]:
        """Return only JSON-compatible dataclass/dict/list/scalar structures."""
        return asdict(self)


def _presets() -> dict[str, ScenarioConfig]:
    return {
        "follow_ride": ScenarioConfig(
            preset_id="follow_ride", mode="follow", target_kind="pennyboard",
            setting="outdoor", surface="land", initial_drone_position=Vec3(-6, 0, 3.2),
        ),
        "soccer_land": ScenarioConfig(
            preset_id="soccer_land", target_kind="soccer_ball", target_position=Vec3(6, 4, 0.11),
        ),
        "soccer_water": ScenarioConfig(
            preset_id="soccer_water", target_kind="soccer_ball", surface="water",
            waterproof=True, target_position=Vec3(6, 4, -0.25),
        ),
        "indoor_soda": ScenarioConfig(
            preset_id="indoor_soda", target_kind="soda_can", setting="indoor",
            target_position=Vec3(3.5, 2.0, 0.061), initial_drone_position=Vec3(-2, -1, 3.0),
            cruise_altitude_m=3.0, world_max=Vec3(15, 15, 8),
        ),
        "pennyboard_land": ScenarioConfig(
            preset_id="pennyboard_land", target_kind="pennyboard", target_position=Vec3(7, 2, 0.05),
        ),
        "object_sandbox": ScenarioConfig(preset_id="object_sandbox", target_kind="object"),
    }


PRESETS = _presets()
PRESET_IDS = tuple(PRESETS)


def preset_catalog() -> dict[str, ScenarioConfig]:
    """Return all six stable presets in stable insertion order."""
    return dict(PRESETS)


def get_preset(preset_id: str) -> ScenarioConfig:
    try:
        return PRESETS[preset_id]
    except (KeyError, TypeError) as exc:
        raise ValueError(f"unknown scenario preset: {preset_id!r}") from exc


def sandbox_config(
    target_kind: str = "object",
    setting: str = "outdoor",
    surface: str = "land",
    waterproof: bool = True,
    *,
    generic_mass_kg: float | None = None,
    generic_dimensions_m: Vec3 | None = None,
    target_position: Vec3 | None = None,
    **overrides: Any,
) -> ScenarioConfig:
    """Build an independent object/setting/surface/waterproof sandbox selection."""
    if target_kind in {"generic", "generic_object"}:
        target_kind = "object"
    values = dict(
        preset_id="object_sandbox", mode="retrieval", target_kind=target_kind,
        setting=setting, surface=surface, waterproof=waterproof,
        target_position=target_position,
    )
    if generic_mass_kg is not None:
        values["generic_mass_kg"] = generic_mass_kg
    if generic_dimensions_m is not None:
        values["generic_dimensions_m"] = generic_dimensions_m
    unknown = set(overrides) - set(ScenarioConfig.__dataclass_fields__)
    if unknown:
        raise ValueError(f"unknown sandbox settings: {sorted(unknown)}")
    values.update(overrides)
    return ScenarioConfig(**values)


def make_sandbox(*args: Any, **kwargs: Any) -> ScenarioConfig:
    """Alias for :func:`sandbox_config` for interactive/Pyodide callers."""
    return sandbox_config(*args, **kwargs)


def run_preset(preset_id: str, **overrides: Any) -> ScenarioResult:
    """Run a preset, optionally using ``dataclasses.replace``-style overrides."""
    unknown = set(overrides) - set(ScenarioConfig.__dataclass_fields__)
    if unknown:
        raise ValueError(f"unknown scenario overrides: {sorted(unknown)}")
    return run_scenario(replace(get_preset(preset_id), **overrides))


def _spec(config: ScenarioConfig) -> ObjectSpec:
    if config.target_kind != "object":
        return OBJECT_SPECS[config.target_kind]
    return ObjectSpec(
        "object", config.generic_mass_kg, config.generic_dimensions_m,
        "illustrative configurable generic object",
    )


def _target_at(spec: ObjectSpec, position: Vec3, attached: bool, in_water: bool) -> TargetObject:
    return TargetObject(
        kind=spec.kind, position=position, dimensions_m=spec.dimensions_m,
        mass_kg=spec.mass_kg, attached=attached, in_water=in_water,
        submersion_depth_m=max(0.0, -position.z) if in_water else 0.0,
    )


def _is_drop_pad(config: ScenarioConfig, position: Vec3) -> bool:
    return math.hypot(position.x - config.drop_zone.x, position.y - config.drop_zone.y) <= config.drop_zone_radius_m


def _in_water(config: ScenarioConfig, position: Vec3) -> bool:
    return config.surface == "water" and not _is_drop_pad(config, position) and position.z <= 0.0


def _drone_at(config: ScenarioConfig, position: Vec3, velocity: Vec3 = ZERO, yaw_deg: float = 0.0) -> DroneState:
    wet = _in_water(config, position)
    return DroneState(position, velocity, yaw_deg, wet, max(0.0, -position.z) if wet else 0.0)


def _tentacle(config: ScenarioConfig, drone: DroneState, extension: float, grasped: bool) -> TentacleState:
    tip = drone.position + Vec3(0, 0, -extension)
    wet = _in_water(config, tip)
    return TentacleState(
        extension_m=extension, tip_position=tip, waterproof=config.waterproof,
        in_water=wet, submersion_depth_m=max(0.0, -tip.z) if wet else 0.0,
        grasped=grasped,
    )


def _inside(config: ScenarioConfig, point: Vec3) -> bool:
    return (
        config.world_min.x <= point.x <= config.world_max.x
        and config.world_min.y <= point.y <= config.world_max.y
        and config.world_min.z <= point.z <= config.world_max.z
    )


def _move_toward(position: Vec3, destination: Vec3, max_distance: float) -> Vec3:
    delta = destination - position
    if delta.length <= max_distance or delta.length <= 1e-12:
        return destination
    return position + delta * (max_distance / delta.length)


def _move_drone(
    config: ScenarioConfig, drone: DroneState, destination: Vec3, speed: float,
) -> DroneState:
    position = _move_toward(drone.position, destination, speed * config.dt_s)
    return _drone_at(config, position, (position - drone.position) / config.dt_s, drone.yaw_deg)


def _rest_position(config: ScenarioConfig, spec: ObjectSpec) -> Vec3:
    return config.drop_zone + Vec3(0, 0, spec.dimensions_m.z / 2.0)


def _hover_position(config: ScenarioConfig, target: Vec3) -> Vec3:
    z = target.z + config.pickup_hover_above_target_m
    if config.surface == "water":
        z = max(z, config.min_drone_water_clearance_m)
    return Vec3(target.x, target.y, z)


def _rider_at(t_s: float) -> tuple[Vec3, Vec3]:
    # Entirely synthetic path and analytic velocity; no recorded or real-place data.
    position = Vec3(3.0 * t_s, 1.5 * math.sin(0.18 * t_s), 0.0)
    velocity = Vec3(3.0, 0.27 * math.cos(0.18 * t_s), 0.0)
    return position, velocity


def _follow_metadata(config: ScenarioConfig, t_s: float) -> FollowMetadata:
    position, velocity = _rider_at(t_s)
    return FollowMetadata(
        rider_id="synthetic_consenting_rider_1", synthetic=True,
        consent_given=config.rider_consent,
        consent_note="Explicit scripted consent for this synthetic rider and simulated footage only.",
        rider_position=position, rider_velocity=velocity,
    )


def _camera(
    config: ScenarioConfig, drone: DroneState, look_at: Vec3, follow: FollowMetadata | None,
) -> tuple[OnboardCameraPose, CameraFraming]:
    pose = OnboardCameraPose(position=drone.position + Vec3(0.12, 0.0, -0.08), look_at=look_at)
    relative = look_at - pose.position
    distance = relative.length
    forward = relative.normalized()
    right = forward.cross(UP).normalized()
    if right.length == 0:
        right = Vec3(1.0, 0.0, 0.0)
    up = right.cross(forward).normalized()
    depth = relative.dot(forward)
    uv = None
    error = math.inf
    visible = depth > 0 and distance <= 100.0 and (follow is None or follow.consent_given)
    in_frame = False
    if depth > 1e-9:
        u = 0.5 + relative.dot(right) / (2 * depth * math.tan(math.radians(pose.horizontal_fov_deg) / 2))
        v = 0.5 - relative.dot(up) / (2 * depth * math.tan(math.radians(pose.vertical_fov_deg) / 2))
        uv = (u, v)
        error = math.hypot(2 * (u - 0.5), 2 * (v - 0.5))
        in_frame = visible and 0.0 <= u <= 1.0 and 0.0 <= v <= 1.0
    return pose, CameraFraming(visible, in_frame, error, uv, distance)


def _viewer(config: ScenarioConfig, drone: DroneState, target: Vec3) -> ViewerOrbitCamera | None:
    if not config.viewer_orbit:
        return None
    look_at = (drone.position + target) / 2.0
    return ViewerOrbitCamera(look_at + Vec3(-8.0, -10.0, 7.0), look_at, 15.0)


def _frame(
    config: ScenarioConfig, t_s: float, phase: str, status: str, drone: DroneState,
    target: TargetObject, extension: float, events: list[ScenarioEvent],
    follow: FollowMetadata | None = None,
) -> ScenarioFrame:
    look_at = follow.rider_position + Vec3(0, 0, 1.2) if follow else target.position
    camera, framing = _camera(config, drone, look_at, follow)
    return ScenarioFrame(
        t_s=t_s, phase=phase, status=status, drone_flight=drone, target=target,
        tentacle=_tentacle(config, drone, extension, target.attached),
        onboard_camera_pose=camera, camera_framing=framing, follow=follow,
        viewer_orbit_camera=_viewer(config, drone, look_at), events=tuple(events),
    )


def _phase_event(t_s: float, phase: str) -> ScenarioEvent:
    return ScenarioEvent(t_s, "phase", f"Mission phase: {phase.replace('_', ' ')}.", phase)


def _event(t_s: float, kind: str, message: str, phase: str) -> ScenarioEvent:
    return ScenarioEvent(t_s, kind, message, phase)


def _initial_target(config: ScenarioConfig) -> TargetObject:
    spec = _spec(config)
    if config.target_position is not None:
        position = config.target_position
    elif config.surface == "water":
        position = Vec3(6, 4, -min(0.15, spec.dimensions_m.z / 2.0))
    else:
        position = Vec3(6, 4, spec.dimensions_m.z / 2.0)
    return _target_at(spec, position, False, _in_water(config, position))


def _unsupported(config: ScenarioConfig, target: TargetObject, drone: DroneState) -> str | None:
    if config.mode == "follow":
        if not config.rider_consent:
            return "stopped: synthetic rider consent is required before follow footage"
        return None
    if not _inside(config, target.position):
        return "stopped: target is outside the bounded synthetic world"
    if not _inside(config, drone.position):
        return "stopped: initial drone position is outside the bounded synthetic world"
    if not _inside(config, config.drop_zone) or not _inside(config, _rest_position(config, _spec(config))):
        return "stopped: safe synthetic drop zone is outside the bounded world"
    if config.drop_zone.z < 0:
        return "stopped: safe drop zone must be a dry pad at or above the water surface"
    if target.mass_kg > config.max_payload_kg:
        return (
            f"stopped: payload {target.mass_kg:g} kg exceeds max payload "
            f"{config.max_payload_kg:g} kg; no pickup attempted"
        )
    grip_width = min(target.dimensions_m.x, target.dimensions_m.y)
    if grip_width > config.max_grip_width_m:
        return (
            f"stopped: object grip width {grip_width:g} m exceeds compatible grip "
            f"{config.max_grip_width_m:g} m; no pickup attempted"
        )
    if config.surface == "water" and not config.waterproof:
        return "stopped: waterproof tentacles are required on water; stopped before submerging"
    if config.surface == "water" and target.submersion_depth_m > 1.0:
        return "stopped: only shallow objects at most 1 m below the surface are supported"
    hover = _hover_position(config, target.position)
    required = hover.z - (target.position - GRIPPER_TO_TARGET).z
    if required > config.tentacle_reach_m + 1e-9:
        return (
            f"stopped: required reach {required:.3f} m exceeds tentacle reach "
            f"{config.tentacle_reach_m:g} m; no pickup attempted"
        )
    return None


def _summary(
    config: ScenarioConfig, frames: list[ScenarioFrame], success: bool, reason: str,
    pickup: bool, released: bool,
) -> ScenarioSummary:
    last = frames[-1]
    follow = [f.camera_framing for f in frames if f.follow is not None]
    rest = _rest_position(config, _spec(config)) if config.mode == "retrieval" else None
    errors = [f.normalized_error for f in follow if math.isfinite(f.normalized_error)]
    return ScenarioSummary(
        success=success, reason=reason, duration_s=round(last.t_s, 6),
        target_kind=config.target_kind, setting=config.setting, surface=config.surface,
        final_phase=last.phase, frame_count=len(frames), pickup_achieved=pickup,
        released=released,
        water_contact=any(f.tentacle.in_water or f.drone_flight.in_water for f in frames),
        drone_water_contact=any(f.drone_flight.in_water for f in frames),
        max_tentacle_depth_m=round(max(f.tentacle.submersion_depth_m for f in frames), 6),
        final_target_position=last.target.position, drop_zone=config.drop_zone,
        drop_error_m=round(last.target.position.distance(rest), 6) if rest is not None else None,
        follow_frames=len(follow),
        follow_in_frame_share=round(sum(f.in_frame for f in follow) / len(follow), 6) if follow else None,
        follow_mean_framing_error=round(sum(errors) / len(errors), 6) if errors else None,
        follow_max_framing_error=round(max(errors), 6) if errors else None,
        consenting_synthetic_rider=(
            frames[-1].follow.synthetic and frames[-1].follow.consent_given
            if frames[-1].follow is not None else None
        ),
    )


def _stopped(
    config: ScenarioConfig, drone: DroneState, target: TargetObject, reason: str,
    t_s: float = 0.0, extension: float = 0.0,
) -> ScenarioResult:
    event = _event(t_s, "stopped", reason, "stopped")
    frame = _frame(config, t_s, "stopped", reason, drone, target, extension, [event])
    summary = _summary(config, [frame], False, reason, False, False)
    return ScenarioResult(config, (frame,), (event,), summary)


def _run_follow(config: ScenarioConfig) -> ScenarioResult:
    rider, velocity = _rider_at(0.0)
    target = _target_at(_spec(config), rider + Vec3(0, 0, 0.05), False, False)
    initial = _drone_at(config, config.initial_drone_position)
    reason = _unsupported(config, target, initial)
    if reason:
        return _stopped(config, initial, target, reason)
    direction = velocity.normalized()
    desired = rider - direction * config.follow_distance_m + Vec3(0, 0, config.follow_altitude_m)
    drone = _drone_at(config, desired)
    frames: list[ScenarioFrame] = []
    events: list[ScenarioEvent] = []
    pending = [_phase_event(0.0, "follow")]
    phase = "follow"
    success = False
    reason = "frame limit reached before synthetic follow footage completed"
    for index in range(config.max_frames):
        t_s = index * config.dt_s
        rider, rider_velocity = _rider_at(t_s)
        direction = rider_velocity.normalized()
        desired = rider - direction * config.follow_distance_m + Vec3(0, 0, config.follow_altitude_m)
        if index:
            correction = (desired - drone.position) * 1.8
            commanded = rider_velocity + correction
            if commanded.length > 7.0:
                commanded = commanded.normalized() * 7.0
            drone = _drone_at(config, drone.position + commanded * config.dt_s, commanded)
        target = _target_at(_spec(config), rider + Vec3(0, 0, 0.05), False, False)
        follow = _follow_metadata(config, t_s)
        current_events = pending
        pending = []
        if not _inside(config, drone.position) or not _inside(config, rider):
            phase = "stopped"
            reason = "stopped: synthetic follow path left the bounded world"
            current_events.append(_event(t_s, "stopped", reason, phase))
        elif t_s + 1e-9 >= config.follow_duration_s:
            phase = "complete"
            success = True
            reason = "completed synthetic consenting-rider follow footage"
            current_events.append(_event(t_s, "complete", reason, phase))
        frame = _frame(config, t_s, phase, phase, drone, target, 0.0, current_events, follow)
        frames.append(frame)
        events.extend(current_events)
        if phase in {"complete", "stopped"}:
            break
    else:
        phase = "stopped"
        reason = f"stopped: {reason}"
        event = _event(frames[-1].t_s, "stopped", reason, phase)
        old = frames[-1]
        frames[-1] = replace(old, phase=phase, status=reason, events=old.events + (event,))
        events.append(event)
    summary = _summary(config, frames, success, reason, False, False)
    return ScenarioResult(config, tuple(frames), tuple(events), summary)


def _run_retrieval(config: ScenarioConfig) -> ScenarioResult:
    spec = _spec(config)
    target = _initial_target(config)
    drone = _drone_at(config, config.initial_drone_position)
    reason = _unsupported(config, target, drone)
    if reason:
        return _stopped(config, drone, target, reason)

    phase = "approach"
    extension = 0.0
    pickup = False
    released = False
    success = False
    reason = "mission did not complete"
    phase_elapsed = 0.0
    was_wet = False
    frames: list[ScenarioFrame] = []
    events: list[ScenarioEvent] = []
    pending = [_phase_event(0.0, phase)]

    for index in range(config.max_frames):
        t_s = index * config.dt_s
        current_events = pending
        pending = []
        next_phase = None
        velocity_zero = _drone_at(config, drone.position, ZERO, drone.yaw_deg)
        drone = velocity_zero

        if phase == "approach":
            destination = Vec3(target.position.x, target.position.y, config.cruise_altitude_m)
            drone = _move_drone(config, drone, destination, config.horizontal_speed_mps)
            horizontal = math.hypot(drone.position.x - target.position.x, drone.position.y - target.position.y)
            if horizontal <= 0.03 and abs(drone.position.z - config.cruise_altitude_m) <= 0.03:
                next_phase = "align"
        elif phase == "align":
            destination = Vec3(target.position.x, target.position.y, config.cruise_altitude_m)
            drone = _move_drone(config, drone, destination, config.horizontal_speed_mps)
            if phase_elapsed >= 0.3 and drone.position.distance(destination) <= 0.03:
                next_phase = "descend"
        elif phase == "descend":
            hover = _hover_position(config, target.position)
            drone = _move_drone(config, drone, hover, config.vertical_speed_mps)
            if drone.position.distance(hover) <= 1e-9:
                next_phase = "extend"
        elif phase == "extend":
            required = drone.position.z - (target.position - GRIPPER_TO_TARGET).z
            extension = min(required, extension + config.tentacle_speed_mps * config.dt_s)
            if required - extension <= 1e-9:
                extension = required
                next_phase = "grasp"
        elif phase == "grasp":
            pickup = True
            target = replace(target, attached=True)
            current_events.append(_event(t_s, "grasp", f"Grasped illustrative {target.kind} at fixed gripper offset.", phase))
            next_phase = "lift"
        elif phase == "lift":
            destination = Vec3(drone.position.x, drone.position.y, config.cruise_altitude_m)
            drone = _move_drone(config, drone, destination, config.vertical_speed_mps)
            if abs(drone.position.z - config.cruise_altitude_m) <= 1e-9:
                next_phase = "carry"
        elif phase == "carry":
            rest = _rest_position(config, spec)
            destination = rest - GRIPPER_TO_TARGET + Vec3(0, 0, config.carry_extension_m)
            drone = _move_drone(config, drone, destination, config.horizontal_speed_mps)
            extension = min(
                config.carry_extension_m,
                extension + config.tentacle_speed_mps * config.dt_s,
            ) if extension < config.carry_extension_m else max(
                config.carry_extension_m,
                extension - config.tentacle_speed_mps * config.dt_s,
            )
            if drone.position.distance(destination) <= 1e-9 and abs(extension - config.carry_extension_m) <= 1e-9:
                next_phase = "release"
        elif phase == "release":
            target = replace(target, position=_rest_position(config, spec), attached=False)
            released = True
            current_events.append(_event(t_s, "release", "Released object on the safe synthetic dry drop zone.", phase))
            next_phase = "complete"
        elif phase == "complete":
            success = True
            reason = "completed: object retrieved and released in the safe synthetic drop zone"
            current_events.append(_event(t_s, "complete", reason, phase))

        tip = drone.position + Vec3(0, 0, -extension)
        if target.attached:
            target = _target_at(spec, tip + GRIPPER_TO_TARGET, True, _in_water(config, tip + GRIPPER_TO_TARGET))
        else:
            target = _target_at(spec, target.position, False, _in_water(config, target.position))
        tentacle = _tentacle(config, drone, extension, target.attached)
        wet = tentacle.in_water or drone.in_water
        if wet and not was_wet:
            current_events.append(_event(
                t_s, "water_contact",
                f"Water contact: waterproof tentacle tip submerged to {tentacle.submersion_depth_m:.3f} m; drone body remains above water.",
                phase,
            ))
        was_wet = wet

        if not _inside(config, drone.position) or not _inside(config, target.position):
            phase = "stopped"
            reason = "stopped: drone or target left the bounded synthetic world"
            current_events.append(_event(t_s, "stopped", reason, phase))
            next_phase = None
        status = phase.replace("_", " ")
        frame = _frame(config, t_s, phase, status, drone, target, extension, current_events)
        frames.append(frame)
        events.extend(current_events)
        if phase in {"complete", "stopped"}:
            break
        if next_phase is not None:
            phase = next_phase
            phase_elapsed = 0.0
            pending.append(_phase_event(t_s + config.dt_s, phase))
        else:
            phase_elapsed += config.dt_s
    else:
        reason = "stopped: frame limit reached before retrieval completed"
        event = _event(frames[-1].t_s, "stopped", reason, "stopped")
        old = frames[-1]
        frames[-1] = replace(old, phase="stopped", status=reason, events=old.events + (event,))
        events.append(event)

    summary = _summary(config, frames, success, reason, pickup, released)
    return ScenarioResult(config, tuple(frames), tuple(events), summary)


def run_scenario(
    config: ScenarioConfig | str = "object_sandbox",
    *,
    dt_s: float | None = None,
    max_frames: int | None = None,
) -> ScenarioResult:
    """Run a deterministic scenario and return immutable frames, events and summary.

    ``config`` may be a :class:`ScenarioConfig` or one of ``PRESET_IDS``. Optional
    ``dt_s``/``max_frames`` overrides are convenient for fixed-step UI replay.
    Malformed settings raise ``ValueError``; supported syntax but impossible missions
    return a stopped result with ``summary.success == False`` and an explicit reason.
    """
    if isinstance(config, str):
        config = get_preset(config)
    if not isinstance(config, ScenarioConfig):
        raise TypeError("config must be a ScenarioConfig or preset ID")
    if dt_s is not None or max_frames is not None:
        config = replace(
            config,
            dt_s=config.dt_s if dt_s is None else dt_s,
            max_frames=config.max_frames if max_frames is None else max_frames,
        )
    if config.mode == "follow":
        return _run_follow(config)
    return _run_retrieval(config)


def trace_scenario(
    config: ScenarioConfig | str = "object_sandbox",
    *,
    dt_s: float | None = None,
    max_frames: int | None = None,
) -> dict[str, Any]:
    """Run and convert to an ``asdict``/``json.dumps``-compatible trace dictionary."""
    return run_scenario(config, dt_s=dt_s, max_frames=max_frames).to_dict()
