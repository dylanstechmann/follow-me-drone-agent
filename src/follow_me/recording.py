"""Read a rider's recorded track (GPX) as offsets, and run it through the simulation.

A recording from a phone's GPS-logging app says where the rider went. This module
keeps only what the simulation needs: for each fix, the seconds since the first fix,
the meters east and north of the first fix, and the fix's accuracy. Coordinates,
dates, names and everything else in the file are dropped as each point is read, so
nothing downstream holds a real position or time. Nothing is written to disk.

GPX has no standard field for accuracy, so each fix's accuracy comes from the first
of these that applies, and the summary says how many fixes used each:
  - "recorded": an `accuracy` or `hacc` element in the point's extensions, in meters;
    or, in files from OsmAnd, `hdop`, where OsmAnd stores the phone's accuracy in
    meters (its SavingTrackHelper saves Location.getAccuracy() in that field);
  - "hdop": in other files `hdop` is the unitless dilution of precision (GPSLogger
    writes it from NMEA), so the accuracy is taken as hdop times 4 m, a guess for a
    phone's single-frequency receiver;
  - "default": 5 m, also a guess.

Usage:
  python -m follow_me.recording walk.gpx                    # a summary of the simulated follow
  python -m follow_me.recording --json walk.gpx > walk.trace.json   # a trace for the replay viewer
Keep recordings and their traces out of the repo: they hold a real route.
"""

import json
import math
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from follow_me.geo import enu_offset_m
from follow_me.sim import RiderFix, trace_track

MAX_CHARS = 50_000_000
MAX_SPAN_M = 200_000.0  # beyond this the flat-earth offsets are not trusted
MAX_DURATION_S = 7200.0  # longer tracks make traces too large for a browser tab
DEFAULT_ACCURACY_M = 5.0
HDOP_TO_M = 4.0
ACCURACY_NAMES = {"accuracy", "hacc", "horizontalaccuracy", "horizontal_accuracy"}
NOTE = (
    "A recorded track run through the kinematic follow simulation. Positions are meters "
    "from the first fix and times are seconds from it. The drone is simulated, with "
    "placeholder limits; it is not a flight simulator."
)

_TIME = re.compile(
    r"(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(\.\d+)?\s*(Z|[+-]\d{2}:?\d{2})?$"
)


@dataclass(frozen=True)
class Recording:
    fixes: list[RiderFix]
    skipped: int  # points with no usable time or position, or a repeated time
    accuracy_from: dict[str, int]  # how many fixes took their accuracy from each source


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _seconds(text: str | None) -> float:
    """An ISO 8601 time as POSIX seconds. A time with no zone is read as UTC."""
    m = _TIME.match((text or "").strip())
    if not m:
        raise ValueError("unreadable time")
    year, month, day, hour, minute, second, frac, zone = m.groups()
    t = datetime(int(year), int(month), int(day), int(hour), int(minute), int(second),
                 tzinfo=timezone.utc).timestamp()
    if frac:
        t += float(frac)
    if zone and zone != "Z":
        sign = 1 if zone[0] == "+" else -1
        t -= sign * (int(zone[1:3]) * 3600 + int(zone[-2:]) * 60)
    return t


def _positive(text: str | None) -> float | None:
    try:
        value = float(text)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) and value > 0 else None


def _accuracy(point: ET.Element, osmand: bool, default_m: float) -> tuple[float, str]:
    hdop = None
    for el in point.iter():
        name = _local(el.tag)
        if name in ACCURACY_NAMES and _positive(el.text):
            return _positive(el.text), "recorded"
        if name == "hdop":
            hdop = _positive(el.text)
    if hdop:
        return (hdop, "recorded") if osmand else (hdop * HDOP_TO_M, "hdop")
    return default_m, "default"


def read_gpx(text: str, default_accuracy_m: float = DEFAULT_ACCURACY_M) -> Recording:
    """The track points of a GPX file as offsets from its first fix, in time order."""
    if len(text) > MAX_CHARS:
        raise ValueError("the file is too large")
    # GPX needs no document type, and refusing one rules out entity expansion tricks.
    if "<!DOCTYPE" in text or "<!ENTITY" in text:
        raise ValueError("the file declares a document type, which GPX does not need")
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        raise ValueError("not a readable GPX file") from None
    if _local(root.tag) != "gpx":
        raise ValueError("not a GPX file")
    osmand = "osmand" in (root.get("creator") or "").lower()

    raw = []
    skipped = 0
    for point in root.iter():
        if _local(point.tag) != "trkpt":
            continue
        try:
            lat, lon = float(point.get("lat")), float(point.get("lon"))
            if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
                raise ValueError("position out of range")
            time = next((c.text for c in point if _local(c.tag) == "time"), None)
            t = _seconds(time)
        except (TypeError, ValueError):
            skipped += 1
            continue
        raw.append((t, lat, lon, *_accuracy(point, osmand, default_accuracy_m)))
    if len(raw) < 2:
        raise ValueError("the file needs at least two track points with times")

    raw.sort(key=lambda p: p[0])
    t0, lat0, lon0 = raw[0][0], raw[0][1], raw[0][2]
    fixes: list[RiderFix] = []
    counts: dict[str, int] = {}
    for t, lat, lon, accuracy, source in raw:
        rel = round(t - t0, 3)
        if fixes and rel <= fixes[-1].t:
            skipped += 1
            continue
        east, north = enu_offset_m(lat0, lon0, lat, lon)
        if math.hypot(east, north) > MAX_SPAN_M:
            raise ValueError("the track spans more than 200 km")
        fixes.append(RiderFix(rel, east, north, accuracy))
        counts[source] = counts.get(source, 0) + 1
    if len(fixes) < 2:
        raise ValueError("the file needs at least two track points with different times")
    return Recording(fixes, skipped, counts)


def run_gpx(text: str, dt: float = 0.5) -> dict:
    """Read a GPX file and simulate a drone following it. Returns a trace with a summary."""
    rec = read_gpx(text)
    if rec.fixes[-1].t > MAX_DURATION_S:
        raise ValueError("the recording is longer than 2 hours: trim it or split it")
    trace = trace_track(rec.fixes, dt=dt, note=NOTE)
    path = sum(
        math.hypot(b.east - a.east, b.north - a.north) for a, b in zip(rec.fixes, rec.fixes[1:])
    )
    trace["recording"] = {
        "fixes": len(rec.fixes),
        "skipped": rec.skipped,
        "accuracy_from": rec.accuracy_from,
        "duration_s": rec.fixes[-1].t,
        "path_m": round(path, 1),
    }
    return trace


def summary_lines(trace: dict) -> list[str]:
    rec, s = trace["recording"], trace["summary"]
    sources = ", ".join(f"{k} {v}" for k, v in sorted(rec["accuracy_from"].items()))
    modes = ", ".join(f"{k} {v:g} s" for k, v in s["seconds_in_mode"].items())
    near, far = s["band_m"]
    return [
        f"fixes: {rec['fixes']} (skipped {rec['skipped']}); accuracy from: {sources}",
        f"recording: {rec['duration_s']:g} s, {rec['path_m']:g} m of track; "
        f"simulated every {trace['settings']['dt_s']:g} s",
        f"time in each mode: {modes}",
        f"follow band {near:g} to {far:g} m: the rider was inside it {s['in_band_share']:.0%} of the time",
        f"distance to the rider: median {s['median_distance_m']:g} m, max {s['max_distance_m']:g} m",
        f"return-home requested: {'yes' if s['return_home_requested'] else 'no'}",
    ]


def main(argv: list[str]) -> int:
    args = argv[1:]
    as_json = "--json" in args
    files = [a for a in args if a != "--json"]
    if len(files) != 1 or not files[0].lower().endswith(".gpx"):
        print("usage: python -m follow_me.recording [--json] RECORDING.gpx", file=sys.stderr)
        return 2
    try:
        trace = run_gpx(Path(files[0]).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as e:
        print(f"could not use the recording: {e}", file=sys.stderr)
        return 1
    if as_json:
        print(json.dumps(trace, separators=(",", ":")))
    else:
        print("\n".join(summary_lines(trace)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
