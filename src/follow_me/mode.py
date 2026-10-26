"""Mode machine: decides how much to trust the fused estimate each tick.

Fallback order: TRACKING, then DEGRADED, then DEAD_RECKONING, then HOLD, then
RETURN_HOME_REQUESTED. The machine only reports a request. The mission layer
decides whether to latch return-home.

Losses are timed in seconds from each tick's timestamp, so the fallback timing does
not depend on how often the loop runs.
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


EPS = 1e-9  # so a loss of exactly 5 s, summed from 0.1 s ticks, still counts as 5 s


class ModeMachine:
    def __init__(
        self,
        # 9 m^2 is a 3 m one-sigma error. A 2 m GNSS fix at 10 m range is still tracking.
        # Tune on real logs; the bench data should set this, not this guess.
        degraded_variance: float = 9.0,
        # Seconds without an estimate. Guesses, like the variance: at 2 ticks per second
        # they match the earlier windows of 10 and 100 ticks.
        dead_reckon_s: float = 5.0,
        return_home_s: float = 50.0,
    ) -> None:
        if not 0 < dead_reckon_s < return_home_s:
            raise ValueError("need 0 < dead_reckon_s < return_home_s")
        self.degraded_variance = degraded_variance
        self.dead_reckon_s = dead_reckon_s
        self.return_home_s = return_home_s
        self._last_seen: float | None = None  # last estimate, or the first tick of a loss with none before
        self._last_now: float | None = None

    def step(self, estimate: Estimate | None, now: float) -> Status:
        """One tick at time `now`, in seconds on any clock that does not go backwards."""
        if self._last_now is not None and now < self._last_now:
            raise ValueError("tick times must not go backwards")
        self._last_now = now
        if estimate is None:
            if self._last_seen is None:
                self._last_seen = now
            lost = now - self._last_seen
            if lost <= self.dead_reckon_s + EPS:
                return Status(Mode.DEAD_RECKONING, 0.0, True, False)
            if lost <= self.return_home_s + EPS:
                return Status(Mode.HOLD, 0.0, False, False)
            return Status(Mode.RETURN_HOME_REQUESTED, 0.0, False, True)

        self._last_seen = now
        if estimate.variance <= self.degraded_variance:
            return Status(Mode.TRACKING, 1.0, False, False)
        return Status(Mode.DEGRADED, 0.5, False, False)
