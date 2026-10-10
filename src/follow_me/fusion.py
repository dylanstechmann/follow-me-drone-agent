"""Council fusion: combine per-source estimates of the rider's position.

Coordinates are meters in the drone body frame: +x forward, +y left.
Each source reports an isotropic variance (m^2). A reliability multiplier
(from context, see context.py) scales how much information a source contributes.
"""

import math
from dataclasses import dataclass


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


def fuse(readings: list[Reading], gate: float = 9.0) -> Estimate | None:
    """Return one fused estimate, or None when no consensus exists.

    Readings far from a reliability-weighted median reference are rejected. The
    gate is a squared distance in units of variance, roughly a chi-square bound
    for 2 degrees of freedom. The rest are combined by inverse-variance weighting.
    """
    active = [r for r in readings if r.reliability > 0]
    if not active:
        return None
    kept = _gate(active, gate)
    if not kept:
        return None
    return _combine(kept)


def _combine(readings: list[Reading]) -> Estimate:
    info = [r.reliability / r.estimate.variance for r in readings]
    total = sum(info)
    x = sum(w * r.estimate.x for w, r in zip(info, readings)) / total
    y = sum(w * r.estimate.y for w, r in zip(info, readings)) / total
    return Estimate(x, y, 1.0 / total)


def _gate(readings: list[Reading], gate: float) -> list[Reading]:
    # Reliability-weighted median, not mean: a wild outlier cannot drag the
    # reference toward itself, and a trusted source beats an unreliable one even
    # when there are only two sources.
    ref_x = _weighted_median([(r.estimate.x, r.reliability) for r in readings])
    ref_y = _weighted_median([(r.estimate.y, r.reliability) for r in readings])
    kept = []
    for r in readings:
        d2 = (r.estimate.x - ref_x) ** 2 + (r.estimate.y - ref_y) ** 2
        if d2 / r.estimate.variance <= gate:
            kept.append(r)
    return kept


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
