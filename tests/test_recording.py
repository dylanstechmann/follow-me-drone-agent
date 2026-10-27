"""Reading a recorded GPX track as offsets. Every track here is made up in the test,
placed near 0 degrees north, 0 degrees east, in the open ocean."""

import json
from pathlib import Path

import pytest

from follow_me import recording
from follow_me.geo import EARTH_RADIUS_M
from follow_me.recording import read_gpx, run_gpx, summary_lines

DEG_M = EARTH_RADIUS_M * 3.141592653589793 / 180  # meters per degree of latitude
GPX11 = "http://www.topografix.com/GPX/1/1"
ROOT = Path(__file__).resolve().parents[1]


def point(north_m=0.0, east_m=0.0, time="2026-10-26T12:00:00Z", inner=""):
    return (f'<trkpt lat="{north_m / DEG_M:.9f}" lon="{east_m / DEG_M:.9f}">'
            f"<time>{time}</time>{inner}</trkpt>")


def gpx(points, creator="test", ns=GPX11):
    return (f'<?xml version="1.0" encoding="UTF-8"?>\n<gpx version="1.1" creator="{creator}" xmlns="{ns}">'
            f"<trk><name>made up</name><trkseg>{''.join(points)}</trkseg></trk></gpx>")


def walk(seconds=60, speed=3.0, inner=""):
    """Northward at a steady speed, one fix a second."""
    return gpx([point(north_m=speed * s, time=f"2026-10-26T12:{s // 60:02d}:{s % 60:02d}Z", inner=inner)
                for s in range(seconds + 1)])


def test_offsets_start_at_zero_and_follow_the_track():
    rec = read_gpx(walk())
    first, tenth = rec.fixes[0], rec.fixes[10]
    assert (first.t, first.east, first.north) == (0.0, 0.0, 0.0)
    assert tenth.t == 10.0
    assert tenth.north == pytest.approx(30.0, abs=0.01)
    assert tenth.east == pytest.approx(0.0, abs=0.01)
    assert rec.skipped == 0


def test_coordinates_names_and_dates_are_dropped():
    trace = run_gpx(walk())
    text = json.dumps(trace)
    assert '"lat' not in text and '"lon' not in text
    assert "2026" not in text and "made up" not in text
    assert set(vars(read_gpx(walk()).fixes[0])) == {"t", "east", "north", "accuracy_m"}


@pytest.mark.parametrize("creator, inner, accuracy, source", [
    ("test", "<extensions><accuracy>3.5</accuracy></extensions>", 3.5, "recorded"),
    ("test", '<extensions><x:hAcc xmlns:x="urn:x">2.0</x:hAcc></extensions>', 2.0, "recorded"),
    ("OsmAnd Maps 5.1", "<hdop>6.0</hdop>", 6.0, "recorded"),
    ("GPSLogger 131 - http://gpslogger.mendhak.com/", "<hdop>1.5</hdop>", 6.0, "hdop"),
    ("test", "", 5.0, "default"),
    ("test", "<hdop>junk</hdop>", 5.0, "default"),
])
def test_accuracy_comes_from_the_best_field_there_is(creator, inner, accuracy, source):
    text = gpx([point(0, time="2026-10-26T12:00:00Z", inner=inner),
                point(3, time="2026-10-26T12:00:01Z", inner=inner)], creator=creator)
    rec = read_gpx(text)
    assert rec.fixes[0].accuracy_m == pytest.approx(accuracy)
    assert rec.accuracy_from == {source: 2}


def test_times_with_zones_and_fractions_are_read():
    text = gpx([
        point(0, time="2026-10-26T14:00:00.250+02:00"),
        point(1, time="2026-10-26T12:00:01.750Z"),
        point(2, time="2026-10-26T07:00:03-0500"),
        point(3, time="2026-10-26T12:00:04"),  # no zone: read as UTC
    ])
    assert [f.t for f in read_gpx(text).fixes] == [0.0, 1.5, 2.75, 3.75]


def test_points_are_sorted_and_bad_or_repeated_ones_skipped():
    text = gpx([
        point(6, time="2026-10-26T12:00:02Z"),
        point(0, time="2026-10-26T12:00:00Z"),
        point(9, time="2026-10-26T12:00:02Z"),  # repeats a time
        point(1, time="not a time"),
        '<trkpt lat="91" lon="0"><time>2026-10-26T12:00:05Z</time></trkpt>',
        '<trkpt lon="0"><time>2026-10-26T12:00:06Z</time></trkpt>',
        point(3, time="2026-10-26T12:00:01Z"),
    ])
    rec = read_gpx(text)
    assert [f.t for f in rec.fixes] == [0.0, 1.0, 2.0]
    assert rec.skipped == 4


def test_gpx_1_0_files_are_read():
    text = gpx([point(0, time="2026-10-26T12:00:00Z"), point(3, time="2026-10-26T12:00:01Z")],
               ns="http://www.topografix.com/GPX/1/0")
    assert len(read_gpx(text).fixes) == 2


@pytest.mark.parametrize("text, message", [
    ('<?xml version="1.0"?><!DOCTYPE gpx [<!ENTITY a "aaaa">]><gpx>&a;</gpx>', "document type"),
    ("<kml></kml>", "not a GPX file"),
    ("<gpx><trk>", "not a readable"),
    (gpx([point(0)]), "at least two"),
    (gpx([point(0, time="2026-10-26T12:00:00Z"), point(3e5, time="2026-10-26T12:00:01Z")]), "200 km"),
])
def test_bad_files_are_refused(text, message):
    with pytest.raises(ValueError, match=message):
        read_gpx(text)


def test_run_simulates_the_track_and_describes_the_recording():
    trace = run_gpx(walk(seconds=120))
    assert trace["kind"] == "simulation"
    assert trace["recording"] == {
        "fixes": 121, "skipped": 0, "accuracy_from": {"default": 121},
        "duration_s": 120.0, "path_m": pytest.approx(360.0, abs=0.1),
    }
    # The 5 m default is above the 3 m threshold, so a phone-like track is degraded.
    assert set(trace["summary"]["seconds_in_mode"]) == {"degraded"}
    assert len(trace["ticks"]) == 241


def test_recordings_longer_than_two_hours_are_refused(monkeypatch):
    monkeypatch.setattr(recording, "MAX_DURATION_S", 30.0)
    with pytest.raises(ValueError, match="longer than 2 hours"):
        run_gpx(walk(seconds=60))


def test_main_prints_a_summary_or_a_trace(tmp_path, capsys):
    path = tmp_path / "walk.gpx"
    path.write_text(walk(), encoding="utf-8")
    assert recording.main(["recording", str(path)]) == 0
    out = capsys.readouterr().out
    assert out.splitlines() == summary_lines(run_gpx(walk()))
    assert "accuracy from: default 61" in out
    assert recording.main(["recording", "--json", str(path)]) == 0
    assert json.loads(capsys.readouterr().out)["kind"] == "simulation"


def test_main_refuses_other_files_and_reports_bad_ones(tmp_path, capsys):
    assert recording.main(["recording", "walk.json"]) == 2
    bad = tmp_path / "bad.gpx"
    bad.write_text("<kml></kml>", encoding="utf-8")
    assert recording.main(["recording", str(bad)]) == 1
    assert "not a GPX file" in capsys.readouterr().err


def test_git_ignores_recordings_and_their_traces():
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "*.gpx" in ignored and "*.trace.json" in ignored


# Two phones on the same walk (iteration 36).

import random as _random

from follow_me.recording import apart, read_gpx_pair


def noisy_walk(seconds=300, speed=1.5, start=0, sigma=0.0, reported=None, seed=0, east_bias=0.0):
    """A made-up walk north, one fix a second, with made-up per-axis error and an accuracy extension."""
    rng = _random.Random(seed)
    pts = []
    for s in range(start, start + seconds + 1):
        e = east_bias + (rng.gauss(0.0, sigma) if sigma else 0.0)
        n = speed * s + (rng.gauss(0.0, sigma) if sigma else 0.0)
        inner = f"<extensions><accuracy>{reported}</accuracy></extensions>" if reported else ""
        pts.append(point(north_m=n, east_m=e, time=f"2026-10-27T12:{s // 60:02d}:{s % 60:02d}Z", inner=inner))
    return gpx(pts)


def test_two_recordings_share_one_origin_and_clock():
    a, b = read_gpx_pair(noisy_walk(seconds=60), noisy_walk(seconds=60, start=10, east_bias=1.0))
    assert (a.fixes[0].t, a.fixes[0].north) == (0.0, 0.0)
    assert b.fixes[0].t == 10.0  # the second phone started 10 s later
    assert b.fixes[0].north == pytest.approx(15.0, abs=0.01)  # where the walk was at 10 s
    assert b.fixes[0].east == pytest.approx(1.0, abs=0.01)


def test_recordings_that_do_not_overlap_are_refused():
    with pytest.raises(ValueError, match="overlap"):
        read_gpx_pair(noisy_walk(seconds=30), noisy_walk(seconds=30, start=100))


def test_honest_phones_are_apart_about_as_their_accuracy_predicts():
    # 2 m of error per axis on each phone, reported as a 68% radius of 3.02 m, as Android does.
    a, b = read_gpx_pair(noisy_walk(sigma=2.0, reported=3.02, seed=1), noisy_walk(sigma=2.0, reported=3.02, seed=2))
    gap = apart(a, b)
    assert gap["verdict"] == "about right"
    assert gap["median_m"] == pytest.approx(gap["predicted_median_m"], rel=0.25)


def test_phones_that_understate_their_error_are_called_optimistic():
    a, b = read_gpx_pair(noisy_walk(sigma=2.0, reported=1.0, seed=1), noisy_walk(sigma=2.0, reported=1.0, seed=2))
    gap = apart(a, b)
    assert gap["verdict"] == "optimistic" and gap["ratio"] > 2.0


def test_two_phones_run_as_phone_and_tag():
    trace = run_gpx(noisy_walk(sigma=1.0, reported=2.0, seed=1), second=noisy_walk(sigma=1.0, reported=2.0, seed=2))
    sources = {r["source"] for t in trace["ticks"] for r in t["readings"]}
    assert sources == {"phone_gnss", "tag_gnss"}
    assert "second" in trace["ticks"][10]["world"]
    assert set(trace["recording"]["apart"]) >= {"median_m", "predicted_median_m", "verdict"}
    assert trace["recording"]["second"]["fixes"] == 301


def test_the_gate_rejects_a_phone_that_disagrees_badly():
    # The second phone is 15 m east of the first throughout: the council cannot trust both.
    trace = run_gpx(noisy_walk(reported=2.0), second=noisy_walk(reported=2.0, east_bias=15.0))
    statuses = [r["status"] for t in trace["ticks"] for r in t["readings"]]
    assert "rejected" in statuses


def test_main_compares_two_phones(tmp_path, capsys):
    first, second = tmp_path / "android.gpx", tmp_path / "iphone.gpx"
    first.write_text(noisy_walk(sigma=1.0, reported=2.0, seed=1), encoding="utf-8")
    second.write_text(noisy_walk(sigma=1.0, reported=2.0, seed=2), encoding="utf-8")
    assert recording.main(["recording", str(first), str(second)]) == 0
    out = capsys.readouterr().out
    assert "second phone, as the tag" in out and "the phones were apart by a median" in out
    assert recording.main(["recording", str(first), str(second), str(first)]) == 2
