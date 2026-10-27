"""One camera box at a time through the council, for the website's camera page.

The page finds the rider's box in the visitor's camera and sends it here, run in the
browser by Pyodide. A council is kept between frames, so the mode machine times a
lost rider as it would on the drone, and each step comes back in the replay trace's
format. The drone does not move, so there is no motion estimate or feed-forward.
"""

import math

from follow_me.context import Conditions
from follow_me.controller import Detection
from follow_me.council import Council
from follow_me.fusion import Reading
from follow_me.replay import trace_tick
from follow_me.sources import camera_estimate

# Laptop and phone cameras are usually 60 to 80 degrees across. A guess the page can change.
DEFAULT_HFOV_DEG = 70.0


def vertical_fov_deg(hfov_deg: float, aspect: float) -> float:
    """The vertical field of view of a frame `aspect` times wider than tall."""
    return math.degrees(2.0 * math.atan(math.tan(math.radians(hfov_deg) / 2.0) / aspect))


class CameraView:
    def __init__(self, hfov_deg: float = DEFAULT_HFOV_DEG, aspect: float = 4.0 / 3.0) -> None:
        if not 10.0 <= hfov_deg <= 170.0 or aspect <= 0:
            raise ValueError("need a field of view between 10 and 170 degrees and a positive aspect")
        self.hfov_rad = math.radians(hfov_deg)
        self.vfov_rad = math.radians(vertical_fov_deg(hfov_deg, aspect))
        self.council = Council(hfov_rad=self.hfov_rad, vfov_rad=self.vfov_rad)

    def step(self, now: float, box: dict | None) -> dict:
        """One frame at time `now` (seconds). `box` is the rider's box as shares of the
        frame, {"cx", "cy", "height"}, or None when no rider is followed."""
        readings = []
        if box is not None and float(box["height"]) > 0:
            det = Detection(cx=float(box["cx"]), cy=float(box["cy"]), height=float(box["height"]))
            readings.append(Reading("camera", camera_estimate(det, self.hfov_rad, self.vfov_rad)))
        result = self.council.tick(readings, Conditions(), now=now)
        log_tick = {
            "t": now,
            "readings": [
                {"source": r.source, "x": r.estimate.x, "y": r.estimate.y, "variance": r.estimate.variance}
                for r in readings
            ],
        }
        return trace_tick(log_tick, now, result)
