"""Replay a sensor log through the council (gate 2: no hardware needed).

Log format (JSON): {"ticks": [ ... ]}, each tick:
  {
    "t": 0.0,                              # seconds; the mode machine times losses with it
    "weather": null | {"precipitation_mm": 0.0, "wind_mps": 2.0, "fog": false},
    "link_quality": 1.0 | {"phone_gnss": 0.1},   # a number applies to all companions
    "gnss_quality": 1.0 | {"tag_gnss": 0.5},
    "overrides": {"camera": 0.3},          # already-combined place attention
    "readings": [{"source": "camera", "x": 10.0, "y": 0.0, "variance": 1.0,
                  "reliability": 1.0, "age_s": 0.0}, ...]   # age_s: seconds since measured
  }
Missing optional fields take the defaults shown in the code.

Usage:
  python -m follow_me.replay path/to/log.json          # one line per tick
  python -m follow_me.replay --json path/to/log.json   # a trace for the website's replay viewer
"""

import json
import math
import sys
from pathlib import Path

from follow_me.context import COMPANION_GNSS_SOURCES, Conditions, WeatherReport
from follow_me.council import Council, TickResult
from follow_me.fusion import DEFAULT_GATE, Estimate, Reading

TRACE_FORMAT = "follow-me-trace/1"


def _per_source(value) -> dict[str, float]:
    """A number applies to every companion source. A dict names each source."""
    if value is None:
        return {}
    if isinstance(value, dict):
        return {src: float(q) for src, q in value.items()}
    return {src: float(value) for src in COMPANION_GNSS_SOURCES}


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
        link_quality=_per_source(tick.get("link_quality")),
        gnss_quality=_per_source(tick.get("gnss_quality")),
    )


def _parse_readings(tick: dict) -> list[Reading]:
    out = []
    for r in tick.get("readings", []):
        out.append(
            Reading(
                source=r["source"],
                estimate=Estimate(float(r["x"]), float(r["y"]), float(r["variance"])),
                reliability=float(r.get("reliability", 1.0)),
                age_s=float(r.get("age_s", 0.0)),
            )
        )
    return out


def replay(log: dict, council: Council | None = None) -> list[tuple[float, TickResult]]:
    council = council or Council()
    results = []
    for tick in log["ticks"]:
        t = float(tick["t"])
        result = council.tick(
            _parse_readings(tick),
            _parse_conditions(tick),
            overrides=tick.get("overrides"),
            now=t,
        )
        results.append((t, result))
    return results


def _round(value: float) -> float:
    return round(value, 4)


def trace_tick(tick: dict, t: float, r: TickResult) -> dict:
    """One tick of a trace: a log tick and what the council decided from it."""
    readings = []
    status = r.fusion.status if r.fusion else ()
    for reading, state in zip(_parse_readings(tick), status):
        trust = reading.reliability * r.weights.get(reading.source, 1.0)
        readings.append({
            "source": reading.source,
            "x": _round(reading.estimate.x),
            "y": _round(reading.estimate.y),
            "variance": _round(reading.estimate.variance),
            "trust": _round(trust),
            "status": state,
        })
    ref = r.fusion.reference if r.fusion else None
    est = r.estimate
    out = {
        "t": t,
        "weather": tick.get("weather"),
        "link_quality": tick.get("link_quality"),
        "gnss_quality": tick.get("gnss_quality"),
        "overrides": tick.get("overrides"),
        "attention": {src: _round(w) for src, w in r.weights.items()},
        "readings": readings,
        "reference": None if ref is None else [_round(ref[0]), _round(ref[1])],
        "estimate": None if est is None else {
            "x": _round(est.x), "y": _round(est.y), "variance": _round(est.variance),
        },
        "mode": r.mode.value,
        "gain": r.gain_scale,
        "return_home": r.request_return_home,
        "command": {
            "yaw": _round(r.command.yaw),
            "forward": _round(r.command.forward),
            "climb": _round(r.command.climb),
        },
    }
    if r.motion is not None:  # only when the drone's pose was known
        out["motion"] = {
            "forward": _round(r.motion.forward_mps),
            "left": _round(r.motion.left_mps),
            "sigma": _round(r.motion.sigma_mps),
            "feed": _round(r.feed),
        }
    return out


def trace_settings(council: Council) -> dict:
    """The council settings a trace was made with."""
    machine = council.machine
    return {
        "gate": DEFAULT_GATE,
        "degraded_variance": machine.degraded_variance,
        "dead_reckon_s": machine.dead_reckon_s,
        "return_home_s": machine.return_home_s,
        "hfov_deg": _round(math.degrees(council.hfov_rad)),
        "vfov_deg": _round(math.degrees(council.vfov_rad)),
    }


def trace(log: dict, council: Council | None = None) -> dict:
    """The replay as data: per tick, the inputs, attention, gate decisions, estimate, mode and command."""
    council = council or Council()
    ticks = [
        trace_tick(tick, t, result)
        for tick, (t, result) in zip(log["ticks"], replay(log, council))
    ]
    return {
        "format": TRACE_FORMAT,
        "note": log.get("_note", ""),
        "settings": trace_settings(council),
        "ticks": ticks,
    }


def _format(t: float, r: TickResult) -> str:
    est = "none" if r.estimate is None else f"x={r.estimate.x:6.2f} y={r.estimate.y:6.2f}"
    cmd = r.command
    return (
        f"t={t:6.2f}  {r.mode.value:<20} gain={r.gain_scale:.1f}  {est}  "
        f"cmd yaw={cmd.yaw:+.2f} fwd={cmd.forward:+.2f} climb={cmd.climb:+.2f}"
    )


def main(argv: list[str]) -> int:
    args = argv[1:]
    as_json = "--json" in args
    files = [a for a in args if a != "--json"]
    if len(files) != 1:
        print("usage: python -m follow_me.replay [--json] LOG.json", file=sys.stderr)
        return 2
    log = json.loads(Path(files[0]).read_text(encoding="utf-8"))
    if as_json:
        print(json.dumps(trace(log), indent=1))
        return 0
    for t, result in replay(log):
        print(_format(t, result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
