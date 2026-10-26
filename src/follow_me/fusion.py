"""Council fusion: combine per-source estimates of the rider's position.

Coordinates are meters in the drone body frame: +x forward, +y left.
Each source reports an isotropic variance (m^2). A reliability multiplier
(from context, see context.py) scales how much information a source contributes.
"""

import math
from dataclasses import dataclass

# Squared distance in units of variance, roughly a chi-square bound for 2 degrees of freedom.
DEFAULT_GATE = 9.0


@dataclass(frozen=True)
class Estimate:
    x: float  # meters forward of the drone
    y: float  # meters left of the drone
    variance: float  # m^2, isotropic

    @property
    def range(self) -> float:
        return math.hypot(self.x, self.y)

    @property
    def bearing(self) -> float:
        """Radians, positive = left of the drone's nose."""
        return math.atan2(self.y, self.x)


@dataclass(frozen=True)
class Reading:
    source: str
    estimate: Estimate
    reliability: float = 1.0  # 0 disables the source; context scales this


@dataclass(frozen=True)
class FuseReport:
    """What fusion did with each reading, for logs and the replay viewer."""

    estimate: Estimate | None
    reference: tuple[float, float] | None  # the gate centre; None when no reading was active
    status: tuple[str, ...]  # one per input reading, in order: "kept", "rejected" or "off"


def fuse(readings: list[Reading], gate: float = DEFAULT_GATE) -> Estimate | None:
    """Return one fused estimate, or None when no consensus exists.

    Readings far from a reliability-weighted median reference are rejected. The
    gate is a squared distance in units of variance, roughly a chi-square bound
    for 2 degrees of freedom. The rest are combined by inverse-variance weighting.
    """
    return fuse_report(readings, gate).estimate


def fuse_report(readings: list[Reading], gate: float = DEFAULT_GATE) -> FuseReport:
    """Fuse, and say which readings were kept, rejected by the gate, or off (zero reliability)."""
    status = ["off"] * len(readings)
    active = [i for i, r in enumerate(readings) if r.reliability > 0]
    if not active:
        return FuseReport(None, None, tuple(status))
    ref = _reference([readings[i] for i in active])
    kept = []
    for i in active:
        if _inside_gate(readings[i], ref, gate):
            status[i] = "kept"
            kept.append(readings[i])
        else:
            status[i] = "rejected"
    estimate = _combine(kept) if kept else None
    return FuseReport(estimate, ref, tuple(status))


def _combine(readings: list[Reading]) -> Estimate:
    info = [r.reliability / r.estimate.variance for r in readings]
    total = sum(info)
    x = sum(w * r.estimate.x for w, r in zip(info, readings)) / total
    y = sum(w * r.estimate.y for w, r in zip(info, readings)) / total
    return Estimate(x, y, 1.0 / total)


def _reference(readings: list[Reading]) -> tuple[float, float]:
    # Reliability-weighted median, not mean: a wild outlier cannot drag the
    # reference toward itself, and a trusted source beats an unreliable one even
    # when there are only two sources.
    ref_x = _weighted_median([(r.estimate.x, r.reliability) for r in readings])
    ref_y = _weighted_median([(r.estimate.y, r.reliability) for r in readings])
    return ref_x, ref_y


def _inside_gate(r: Reading, ref: tuple[float, float], gate: float) -> bool:
    d2 = (r.estimate.x - ref[0]) ** 2 + (r.estimate.y - ref[1]) ** 2
    return d2 / r.estimate.variance <= gate


def _weighted_median(pairs: list[tuple[float, float]]) -> float:
    """Median of values with weights. An exact weight tie returns the midpoint."""
    ordered = sorted(pairs)
    half = sum(w for _, w in ordered) / 2.0
    cum = 0.0
    for i, (value, weight) in enumerate(ordered):
        cum += weight
        if math.isclose(cum, half, rel_tol=1e-12) and i + 1 < len(ordered):
            return (value + ordered[i + 1][0]) / 2.0
        if cum > half:
            return value
    return ordered[-1][0]
