"""The council: one tick of sense -> context -> fusion -> mode -> control."""

from dataclasses import dataclass, field

from follow_me.context import Conditions, apply_attention, attention
from follow_me.controller import Command, FollowController
from follow_me.fusion import Estimate, FuseReport, Reading, fuse_report
from follow_me.mode import Mode, ModeMachine
from follow_me.sources import estimate_to_detection

DEFAULT_HFOV = 1.5708  # 90 degrees, a placeholder camera
DEFAULT_VFOV = 1.0472  # 60 degrees, a placeholder camera


@dataclass(frozen=True)
class TickResult:
    estimate: Estimate | None
    mode: Mode
    gain_scale: float
    request_return_home: bool
    command: Command
    # How the tick was decided, for logs and the replay viewer. Not used for control.
    weights: dict[str, float] = field(default_factory=dict)  # attention multiplier per source
    fusion: FuseReport | None = None


class Council:
    def __init__(
        self,
        controller: FollowController | None = None,
        machine: ModeMachine | None = None,
        hfov_rad: float = DEFAULT_HFOV,
        vfov_rad: float = DEFAULT_VFOV,
    ) -> None:
        self.controller = controller or FollowController()
        self.machine = machine or ModeMachine()
        self.hfov_rad = hfov_rad
        self.vfov_rad = vfov_rad

    def tick(
        self,
        readings: list[Reading],
        conditions: Conditions,
        overrides: dict[str, float] | None = None,
    ) -> TickResult:
        weights = attention(conditions, overrides)
        report = fuse_report(apply_attention(readings, weights))
        fused = report.estimate
        status = self.machine.step(fused)
        detection = None
        if fused is not None:
            detection = estimate_to_detection(fused, self.hfov_rad, self.vfov_rad)
        raw = self.controller.update(detection)
        command = Command(
            yaw=raw.yaw * status.gain_scale,
            forward=raw.forward * status.gain_scale,
            climb=raw.climb * status.gain_scale,
        )
        return TickResult(
            estimate=fused,
            mode=status.mode,
            gain_scale=status.gain_scale,
            request_return_home=status.request_return_home,
            command=command,
            weights=weights,
            fusion=report,
        )
