import json
import math

import pytest

from follow_me.geo import angle_diff_deg, bearing_deg, enu_offset_m, haversine_m
from follow_me.places import (
    Place,
    active_places,
    combined_attention,
    is_approaching,
    load_places,
)


def test_one_degree_of_latitude_is_about_111_km():
    d = haversine_m(0.0, 0.0, 1.0, 0.0)
    assert d == pytest.approx(111195, rel=0.01)


def test_enu_offset_east_and_north():
    east, north = enu_offset_m(0.0, 0.0, 0.0, 0.001)
    assert east == pytest.approx(111.3, rel=0.01)
    assert north == pytest.approx(0.0, abs=1e-6)
    east, north = enu_offset_m(0.0, 0.0, 0.001, 0.0)
    assert north == pytest.approx(111.2, rel=0.01)


def test_bearing_cardinal_directions():
    assert bearing_deg(0, 0, 1, 0) == pytest.approx(0.0, abs=1e-6)  # north
    assert bearing_deg(0, 0, 0, 1) == pytest.approx(90.0, abs=1e-6)  # east


def test_angle_diff_wraps_around():
    assert angle_diff_deg(350, 10) == pytest.approx(20)
    assert angle_diff_deg(0, 180) == pytest.approx(180)


def north_of_origin(meters):
    return meters / 111195.0, 0.0  # lat, lon


def test_inside_radius_is_always_active():
    place = Place("shed", 0.0, 0.0, radius_m=40)
    assert is_approaching(place, 0.0, 0.0, heading_deg=180)


def test_ahead_within_lookahead_is_approaching():
    lat, lon = north_of_origin(100)  # 100 m north of the place
    place = Place("shed", 0.0, 0.0, radius_m=40)
    # Rider is north of the place, heading south toward it.
    assert is_approaching(place, lat, lon, heading_deg=180)


def test_heading_away_is_not_approaching():
    lat, lon = north_of_origin(100)
    place = Place("shed", 0.0, 0.0, radius_m=40)
    assert not is_approaching(place, lat, lon, heading_deg=0)


def test_beyond_lookahead_is_not_approaching():
    lat, lon = north_of_origin(500)
    place = Place("shed", 0.0, 0.0, radius_m=40)
    assert not is_approaching(place, lat, lon, heading_deg=180)


def test_combined_attention_multiplies_overrides():
    a = Place("a", 0, 0, attention={"camera": 0.5})
    b = Place("b", 0, 0, attention={"camera": 0.5, "tof": 2.0})
    assert combined_attention([a, b]) == {"camera": 0.25, "tof": 2.0}


def test_active_places_filters_by_approach():
    lat, lon = north_of_origin(100)
    near = Place("near", 0.0, 0.0, radius_m=40)
    far = Place("far", 0.5, 0.5, radius_m=40)
    assert [p.name for p in active_places([near, far], lat, lon, heading_deg=180)] == ["near"]


def test_load_places_from_json(tmp_path):
    path = tmp_path / "places.json"
    path.write_text(
        json.dumps(
            {
                "places": [
                    {"name": "shed", "lat": 1.0, "lon": 2.0, "attention": {"camera": 0.3}},
                    {"name": "dip", "lat": 3.0, "lon": 4.0, "radius_m": 25, "note": "n"},
                ]
            }
        ),
        encoding="utf-8",
    )
    places = load_places(path)
    assert places[0].radius_m == 50.0 and places[0].attention == {"camera": 0.3}
    assert places[1].radius_m == 25.0 and places[1].note == "n"


def test_missing_places_file_gives_empty_list(tmp_path):
    assert load_places(tmp_path / "nope.json") == []


def test_example_file_loads_with_fake_coordinates():
    from pathlib import Path

    example = Path(__file__).resolve().parents[1] / "examples" / "places.example.json"
    places = load_places(example)
    assert len(places) == 2
    assert all(abs(p.lat) < 1 and abs(p.lon) < 1 for p in places)
