"""Convert raw sensor observations into body-frame estimates for fusion."""

import math

from follow_me.controller import Detection
from follow_me.fusion import Estimate


def camera_estimate(
    det: Detection,
    hfov_rad: float,
    vfov_rad: float,
    person_height_m: float = 1.75,
    bearing_sigma_rad: float = 0.05,
    range_sigma_frac: float = 0.15,
) -> Estimate:
    """Estimate the person's position from one camera box.

    Uses the pinhole relation h = H / (2 * d * tan(vfov / 2)) for range and a
    linear angle-per-pixel bearing, which is a small-angle approximation. Assumes
    a level camera, an upright person and no lens distortion.
    """
    if det.height <= 0:
        raise ValueError("box height must be positive")
    bearing = (0.5 - det.cx) * hfov_rad  # right of center -> negative (right side)
    rng = person_height_m / (2.0 * det.height * math.tan(vfov_rad / 2.0))
    x = rng * math.cos(bearing)
    y = rng * math.sin(bearing)
    sigma = max(rng * range_sigma_frac, rng * bearing_sigma_rad)
    return Estimate(x, y, sigma**2)
