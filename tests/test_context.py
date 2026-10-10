import pytest

from follow_me.context import (
    BASE_RELIABILITY,
    Conditions,
    OpenMeteoProvider,
    WeatherCache,
    WeatherReport,
    apply_attention,
    attention,
)
from follow_me.fusion import Estimate, Reading

CLEAR = WeatherReport(precipitation_mm=0.0, wind_mps=2.0, fog=False)


def test_clear_conditions_keep_base_weights():
    w = attention(Conditions(weather=CLEAR))
    assert w == pytest.approx(BASE_RELIABILITY)


def test_rain_lowers_camera_weight():
    rain = WeatherReport(precipitation_mm=1.5, wind_mps=2.0, fog=False)
    w = attention(Conditions(weather=rain))
    assert w["camera"] < BASE_RELIABILITY["camera"]
    assert w["companion_gnss"] == pytest.approx(BASE_RELIABILITY["companion_gnss"])


def test_fog_lowers_camera_weight():
    fog = WeatherReport(precipitation_mm=0.0, wind_mps=1.0, fog=True)
    assert attention(Conditions(weather=fog))["camera"] < 1.0


def test_high_wind_lowers_camera_weight():
    gusty = WeatherReport(precipitation_mm=0.0, wind_mps=12.0, fog=False)
    assert attention(Conditions(weather=gusty))["camera"] < 1.0


def test_unknown_weather_is_conservative_for_camera():
    w = attention(Conditions(weather=None))
    assert w["camera"] == pytest.approx(0.8)


def test_weak_link_lowers_companion_gnss_only():
    w = attention(Conditions(weather=CLEAR, link_quality=0.25))
    assert w["companion_gnss"] == pytest.approx(0.25)
    assert w["camera"] == pytest.approx(1.0)


def test_poor_gnss_fix_lowers_companion_gnss():
    w = attention(Conditions(weather=CLEAR, gnss_quality=0.5))
    assert w["companion_gnss"] == pytest.approx(0.5)


def test_place_override_multiplies_a_source():
    w = attention(Conditions(weather=CLEAR), overrides={"camera": 0.2})
    assert w["camera"] == pytest.approx(0.2)


def test_weights_are_clamped_and_never_negative():
    w = attention(Conditions(weather=CLEAR), overrides={"camera": -5.0, "tof": 100.0})
    assert w["camera"] == 0.0
    assert w["tof"] == 2.0


def test_apply_attention_scales_reliability():
    readings = [Reading("camera", Estimate(10, 0, 1.0), reliability=1.0)]
    out = apply_attention(readings, {"camera": 0.4})
    assert out[0].reliability == pytest.approx(0.4)


def test_openmeteo_parses_current_fields_with_injected_fetch():
    calls = []

    def fake_fetch(url):
        calls.append(url)
        return {"current": {"precipitation": 0.5, "wind_speed_10m": 3.2, "weather_code": 45}}

    report = OpenMeteoProvider(fetch=fake_fetch).current(1.0, 2.0)
    assert report == WeatherReport(precipitation_mm=0.5, wind_mps=3.2, fog=True)
    assert "latitude=1.0" in calls[0] and "wind_speed_unit=ms" in calls[0]


class FakeClock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


class CountingProvider:
    def __init__(self, fail=False):
        self.calls = 0
        self.fail = fail

    def current(self, lat, lon):
        self.calls += 1
        if self.fail:
            raise OSError("offline")
        return CLEAR


def test_cache_queries_once_per_ttl():
    clock = FakeClock()
    provider = CountingProvider()
    cache = WeatherCache(provider, ttl_s=600, clock=clock)
    cache.get(0, 0)
    clock.t = 300
    cache.get(0, 0)
    assert provider.calls == 1
    clock.t = 601
    cache.get(0, 0)
    assert provider.calls == 2


def test_cache_returns_none_when_provider_never_worked():
    cache = WeatherCache(CountingProvider(fail=True), clock=FakeClock())
    assert cache.get(0, 0) is None


def test_cache_keeps_last_good_report_after_failure():
    clock = FakeClock()
    provider = CountingProvider()
    cache = WeatherCache(provider, ttl_s=60, clock=clock)
    assert cache.get(0, 0) == CLEAR
    provider.fail = True
    clock.t = 120
    assert cache.get(0, 0) == CLEAR
    assert provider.calls == 2  # a failed refresh counts as an attempt; no retry until the TTL passes
