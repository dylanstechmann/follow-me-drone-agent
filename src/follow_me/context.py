"""Context ("attention"): per-source reliability from weather, links, GNSS and places.

Multipliers scale each source's information weight in fusion.py. They are
clamped to [0, 2] so a bad rule can never make a source negative or dominant.
"""

import json
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, replace
from typing import Callable, Protocol

from follow_me.fusion import Reading

BASE_RELIABILITY = {
    "camera": 1.0,
    "companion_gnss": 1.0,
    "companion_ble": 0.5,
    "tof": 0.8,
}

UNKNOWN_WEATHER_CAMERA_FACTOR = 0.8
MAX_MULTIPLIER = 2.0


@dataclass(frozen=True)
class WeatherReport:
    precipitation_mm: float
    wind_mps: float
    fog: bool


@dataclass(frozen=True)
class Conditions:
    weather: WeatherReport | None = None  # None means unknown
    link_quality: float = 1.0  # 0..1, companion radio or cellular link
    gnss_quality: float = 1.0  # 0..1, rider device's own satellite fix


def _clamp01(v: float) -> float:
    return max(0.0, min(1.0, v))


def attention(
    conditions: Conditions,
    overrides: dict[str, float] | None = None,
) -> dict[str, float]:
    """Return the reliability multiplier for each source, given current conditions."""
    w = dict(BASE_RELIABILITY)

    if conditions.weather is None:
        w["camera"] *= UNKNOWN_WEATHER_CAMERA_FACTOR
    else:
        wx = conditions.weather
        if wx.precipitation_mm > 0.2 or wx.fog:
            w["camera"] *= 0.4
        if wx.wind_mps > 8.0:
            w["camera"] *= 0.7  # gimbal and frame vibration

    w["companion_gnss"] *= _clamp01(conditions.link_quality)
    w["companion_gnss"] *= _clamp01(conditions.gnss_quality)

    for source, factor in (overrides or {}).items():
        if source in w:
            w[source] *= factor

    return {k: max(0.0, min(MAX_MULTIPLIER, v)) for k, v in w.items()}


def apply_attention(readings: list[Reading], weights: dict[str, float]) -> list[Reading]:
    """Scale each reading's reliability by its source's attention weight."""
    return [
        replace(r, reliability=r.reliability * weights.get(r.source, 1.0))
        for r in readings
    ]


class WeatherProvider(Protocol):
    def current(self, lat: float, lon: float) -> WeatherReport: ...


Fetch = Callable[[str], dict]


def _http_get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=5) as resp:
        return json.loads(resp.read().decode("utf-8"))


class OpenMeteoProvider:
    """Current weather from Open-Meteo. Field names should be re-checked against
    its docs before relying on them in the field. The fetch function is injected,
    so tests never touch the network.
    """

    BASE_URL = "https://api.open-meteo.com/v1/forecast"

    def __init__(self, fetch: Fetch | None = None) -> None:
        self._fetch = fetch or _http_get_json

    def current(self, lat: float, lon: float) -> WeatherReport:
        query = urllib.parse.urlencode(
            {
                "latitude": lat,
                "longitude": lon,
                "current": "precipitation,wind_speed_10m,weather_code",
                "wind_speed_unit": "ms",
            }
        )
        data = self._fetch(f"{self.BASE_URL}?{query}")
        cur = data["current"]
        code = int(cur.get("weather_code", 0))
        return WeatherReport(
            precipitation_mm=float(cur["precipitation"]),
            wind_mps=float(cur["wind_speed_10m"]),
            fog=code in (45, 48),  # WMO codes for fog and rime fog
        )


class WeatherCache:
    """Queries the provider at most once per ttl_s. Keeps the last good report
    if a refresh fails, and returns None only when nothing has ever worked.
    """

    def __init__(
        self,
        provider: WeatherProvider,
        ttl_s: float = 600.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._provider = provider
        self._ttl = ttl_s
        self._clock = clock
        self._report: WeatherReport | None = None
        self._fetched_at: float | None = None

    def get(self, lat: float, lon: float) -> WeatherReport | None:
        now = self._clock()
        fresh = self._fetched_at is not None and now - self._fetched_at < self._ttl
        if fresh:
            return self._report
        try:
            self._report = self._provider.current(lat, lon)
            self._fetched_at = now
        except (OSError, ValueError, KeyError):
            # Network or parse failure: keep the old report, do not retry every tick.
            self._fetched_at = now
        return self._report
