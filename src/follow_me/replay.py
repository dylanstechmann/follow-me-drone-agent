"""Replay a sensor log through the council (gate 2: no hardware needed).

Log format (JSON): {"ticks": [ ... ]}, each tick:
  {
    "t": 0.0,
    "weather": null | {"precipitation_mm": 0.0, "wind_mps": 2.0, "fog": false},
    "link_quality": 1.0,
    "gnss_quality": 1.0,
    "overrides": {"camera": 0.3},          # already-combined place attention
    "readings": [{"source": "camera", "x": 10.0, "y": 0.0, "variance": 1.0,
                  "reliability": 1.0}, ...]
  }
Missing optional fields take the defaults shown in the code.

Usage: python -m follow_me.replay path/to/log.json
"""

import json
import sys
from pathlib import Path

from follow_me.context import Conditions, WeatherReport
from follow_me.council import Council, TickResult
from follow_me.fusion import Estimate, Reading


def _parse_conditions(tick: dict) -> Conditions:
    wx = tick.get("weather")
    weather = None
    if wx is not None:
        weather = WeatherReport(
            precipitation_mm=float(wx.get("precipitation_mm", 0.0)),
            wind_mps=float(wx.get("wind_mps", 0.0)),
            fog=bool(wx.get("fog", False)),
        )
    return Conditions(
        weather=weather,
        link_quality=float(tick.get("link_quality", 1.0)),
        gnss_quality=float(tick.get("gnss_quality", 1.0)),
    )


def _parse_readings(tick: dict) -> list[Reading]:
    out = []
    for r in tick.get("readings", []):
        out.append(
            Reading(
                source=r["source"],
                estimate=Estimate(float(r["x"]), float(r["y"]), float(r["variance"])),
                reliability=float(r.get("reliability", 1.0)),
            )
        )
    return out


def replay(log: dict, council: Council | None = None) -> list[tuple[float, TickResult]]:
    council = council or Council()
    results = []
    for tick in log["ticks"]:
        result = council.tick(
            _parse_readings(tick),
            _parse_conditions(tick),
            overrides=tick.get("overrides"),
        )
        results.append((float(tick["t"]), result))
    return results


def _format(t: float, r: TickResult) -> str:
    est = "none" if r.estimate is None else f"x={r.estimate.x:6.2f} y={r.estimate.y:6.2f}"
    cmd = r.command
    return (
        f"t={t:6.2f}  {r.mode.value:<20} gain={r.gain_scale:.1f}  {est}  "
        f"cmd yaw={cmd.yaw:+.2f} fwd={cmd.forward:+.2f} climb={cmd.climb:+.2f}"
    )


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: python -m follow_me.replay LOG.json", file=sys.stderr)
        return 2
    log = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    for t, result in replay(log):
        print(_format(t, result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
