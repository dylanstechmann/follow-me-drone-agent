"""Follow controller: turns a tracked person's box into normalized flight commands.

Pure logic with no hardware, camera, or autopilot dependency. Outputs are
normalized to [-1, 1] so a later adapter can map them to real units (m/s, deg/s)
with limits set by the autopilot, not by this code alone.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Detection:
    """A person box in normalized image coordinates (0..1, origin top-left)."""

    cx: float  # box center x
    cy: float  # box center y
    height: float  # box height as a fraction of frame height (distance proxy)


@dataclass(frozen=True)
class Command:
    yaw: float  # turn toward (+) / away (-) from target
    forward: float  # approach (+) / back off (-)
    climb: float  # climb (+) / descend (-) to keep target framed


def _clamp(value: float, limit: float) -> float:
    return max(-limit, min(limit, value))


class FollowController:
    def __init__(
        self,
        target_height: float = 0.35,
        target_cy: float = 0.5,
        deadband: float = 0.05,
        gain: float = 2.0,
        max_command: float = 1.0,
        lost_frames_before_stop: int = 15,
    ) -> None:
        self.target_height = target_height
        self.target_cy = target_cy
        self.deadband = deadband
        self.gain = gain
        self.max_command = max_command
        self.lost_frames_before_stop = lost_frames_before_stop
        self._lost_frames = 0

    def _apply_deadband(self, error: float) -> float:
        if abs(error) <= self.deadband:
            return 0.0
        # Subtract the deadband so the command ramps up from zero, not from a jump.
        return error - self.deadband if error > 0 else error + self.deadband

    def update(self, detection: Detection | None) -> Command:
        """Return one command. Pass None when the person is not detected this frame."""
        if detection is None:
            # Never chase a stale box: hold still on any loss. The counter is kept
            # so a later layer can escalate (e.g. return-to-home) after a long loss.
            self._lost_frames += 1
            return Command(0.0, 0.0, 0.0)

        self._lost_frames = 0

        # Image x error: person right of center (cx > 0.5) means yaw right.
        yaw_err = self._apply_deadband(detection.cx - 0.5)
        # Image y error: person below the setpoint means the drone is too high relative
        # to them, so it must descend to re-center (assumes a level, fixed camera).
        climb_err = self._apply_deadband(detection.cy - self.target_cy)
        # Box too small means too far: approach. Box too big means too close: back off.
        dist_err = self._apply_deadband(self.target_height - detection.height)

        return Command(
            yaw=_clamp(self.gain * yaw_err, self.max_command),
            forward=_clamp(self.gain * dist_err, self.max_command),
            climb=_clamp(-self.gain * climb_err, self.max_command),
        )
