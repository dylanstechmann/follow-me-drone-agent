"""Place profiles: known locations with sensor trouble or a predictable pattern.

Real profiles hold personal coordinates and live outside the repo. Load them
from a path (default ~/.config/follow-me/places.json or the FOLLOW_ME_PLACES
environment variable). Only fake examples belong in examples/.
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from follow_me.geo import angle_diff_deg, bearing_deg, haversine_m


@dataclass(frozen=True)
class Place:
    name: str
    lat: float
    lon: float
    radius_m: float = 50.0
    attention: dict[str, float] = field(default_factory=dict)  # source -> multiplier
    note: str = ""


def default_places_path() -> Path:
    env = os.environ.get("FOLLOW_ME_PLACES")
    if env:
        return Path(env).expanduser()
    return Path.home() / ".config" / "follow-me" / "places.json"


def load_places(path: Path | str | None = None) -> list[Place]:
    p = Path(path).expanduser() if path else default_places_path()
    if not p.exists():
        return []
    data = json.loads(p.read_text(encoding="utf-8"))
    return [
        Place(
            name=item["name"],
            lat=float(item["lat"]),
            lon=float(item["lon"]),
            radius_m=float(item.get("radius_m", 50.0)),
            attention={k: float(v) for k, v in item.get("attention", {}).items()},
            note=item.get("note", ""),
        )
        for item in data.get("places", [])
    ]


def is_approaching(
    place: Place,
    lat: float,
    lon: float,
    heading_deg: float,
    lookahead_m: float = 150.0,
    cone_deg: float = 45.0,
) -> bool:
    """True when the rider is inside the place, or close and heading toward it."""
    dist = haversine_m(lat, lon, place.lat, place.lon)
    if dist <= place.radius_m:
        return True
    if dist > place.radius_m + lookahead_m:
        return False
    to_place = bearing_deg(lat, lon, place.lat, place.lon)
    return angle_diff_deg(heading_deg, to_place) <= cone_deg


def active_places(
    places: list[Place],
    lat: float,
    lon: float,
    heading_deg: float,
    **kwargs,
) -> list[Place]:
    return [p for p in places if is_approaching(p, lat, lon, heading_deg, **kwargs)]


def combined_attention(places: list[Place]) -> dict[str, float]:
    """Multiply the overrides of all active places together."""
    out: dict[str, float] = {}
    for p in places:
        for source, factor in p.attention.items():
            out[source] = out.get(source, 1.0) * factor
    return out
