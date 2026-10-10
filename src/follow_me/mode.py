"""Mode machine: decides how much to trust the fused estimate each tick.

Fallback order: TRACKING, then DEGRADED, then DEAD_RECKONING, then HOLD, then
RETURN_HOME_REQUESTED. The machine only reports a request. The mission layer
decides whether to latch return-home.
"""

from dataclasses import dataclass
from enum import Enum

from follow_me.fusion import Estimate


class Mode(Enum):
    TRACKING = "tracking"
    DEGRADED = "degraded"
    DEAD_RECKONING = "dead_reckoning"
    HOLD = "hold"
    RETURN_HOME_REQUESTED = "return_home_requested"


@dataclass(frozen=True)
class Status:
    mode: Mode
    gain_scale: float  # multiply controller commands by this
    hold_last_command: bool  # caller may keep the previous command for a short time
    request_return_home: bool


class ModeMachine:
    def __init__(
        self,
        # 9 m^2 is a 3 m one-sigma error. A 2 m GNSS fix at 10 m range is still tracking.
        # Tune on real logs; the bench data should set this, not this guess.
        degraded_variance: float = 9.0,
        dead_reckon_ticks: int = 10,
        hold_ticks: int = 100,
    ) -> None:
        if not 0 < dead_reckon_ticks < hold_ticks:
            raise ValueError("need 0 < dead_reckon_ticks < hold_ticks")
        self.degraded_variance = degraded_variance
        self.dead_reckon_ticks = dead_reckon_ticks
        self.hold_ticks = hold_ticks
        self._lost_ticks = 0

    def step(self, estimate: Estimate | None) -> Status:
        if estimate is None:
            self._lost_ticks += 1
            n = self._lost_ticks
            if n <= self.dead_reckon_ticks:
                return Status(Mode.DEAD_RECKONING, 0.0, True, False)
            if n <= self.hold_ticks:
                return Status(Mode.HOLD, 0.0, False, False)
            return Status(Mode.RETURN_HOME_REQUESTED, 0.0, False, True)

        self._lost_ticks = 0
        if estimate.variance <= self.degraded_variance:
            return Status(Mode.TRACKING, 1.0, False, False)
        return Status(Mode.DEGRADED, 0.5, False, False)
