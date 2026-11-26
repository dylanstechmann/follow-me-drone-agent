import itertools
import json
from pathlib import Path

import pytest

from follow_me.context import Conditions, WeatherReport
from follow_me.council import Council
from follow_me.fusion import Estimate, Reading, fuse
from follow_me.mode import Mode, ModeMachine
from follow_me.replay import OUTAGE_FORMAT, TRACE_FORMAT, main, outage_report, replay, trace

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "replay.example.json"


def test_weighted_median_rejects_unreliable_source_when_only_two_sources():
    # Old median rejected both here. The trusted GNSS reading must survive.
    readings = [
        Reading("camera", Estimate(4.0, 0.0, 1.0), reliability=0.4),
        Reading("phone_gnss", Estimate(10.2, 0.0, 1.0), reliability=1.0),
    ]
    out = fuse(readings)
    assert out is not None
    assert out.x == pytest.approx(10.2)


def test_two_equal_disagreeing_sources_still_have_no_consensus():
    readings = [
        Reading("a", Estimate(0.0, 0.0, 1.0)),
        Reading("b", Estimate(10.0, 0.0, 1.0)),
    ]
    assert fuse(readings) is None


def test_council_tracks_on_clear_agreement():
    clear = Conditions(weather=WeatherReport(0.0, 2.0, False))
    result = Council().tick(
        [Reading("camera", Estimate(10.0, 0.0, 1.0)),
         Reading("phone_gnss", Estimate(10.0, 0.0, 1.0))],
        clear,
        now=0.0,
    )
    assert result.mode is Mode.TRACKING
    assert result.estimate.x == pytest.approx(10.0)


def test_council_scales_command_by_mode_gain():
    council = Council(machine=ModeMachine(degraded_variance=0.1))
    result = council.tick([Reading("camera", Estimate(12.0, 3.0, 1.0))], Conditions(), now=0.0)
    assert result.mode is Mode.DEGRADED
    assert result.gain_scale == 0.5
    full = Council(machine=ModeMachine(degraded_variance=10.0)).tick(
        [Reading("camera", Estimate(12.0, 3.0, 1.0))], Conditions(), now=0.0
    )
    assert result.command.yaw == pytest.approx(full.command.yaw * 0.5)


def test_replay_example_walks_the_whole_ladder_at_default_settings():
    # The docs say the example shows every mode, so check it with the defaults the
    # replay tool uses, not with shortened thresholds.
    log = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    modes = [r.mode for _, r in replay(log)]
    runs = [(mode, len(list(group))) for mode, group in itertools.groupby(modes)]
    assert runs == [
        # Rain, a wrong camera reading, a trouble spot and a phone link loss: tracking holds.
        (Mode.TRACKING, 5),
        # Only a weak tag fix is left.
        (Mode.DEGRADED, 2),
        # No readings at all: dead reckoning up to 5 s, hold up to 50 s, at 2 ticks a second.
        (Mode.DEAD_RECKONING, 10),
        (Mode.HOLD, 90),
        (Mode.RETURN_HOME_REQUESTED, 4),
        # Recovered at the end.
        (Mode.TRACKING, 2),
    ]


def test_short_thresholds_reach_hold_and_return_home_sooner():
    log = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    council = Council(machine=ModeMachine(dead_reckon_s=1.0, return_home_s=1.5))
    modes = [r.mode for _, r in replay(log, council)]
    assert modes[7:11] == [
        Mode.DEAD_RECKONING,
        Mode.DEAD_RECKONING,
        Mode.HOLD,
        Mode.RETURN_HOME_REQUESTED,
    ]


def test_rain_tick_estimate_follows_the_companions():
    log = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    results = replay(log)
    _, rain_tick = results[2]
    assert rain_tick.estimate.x == pytest.approx(10.0, abs=0.5)


def test_phone_link_loss_leaves_tag_as_sole_source():
    log = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    _, link_loss = replay(log)[4]
    assert link_loss.estimate is not None
    assert link_loss.estimate.x == pytest.approx(10.0, abs=0.01)


def test_replay_never_chases_while_lost():
    log = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    for _, r in replay(log):
        if r.estimate is None:
            assert r.command.yaw == 0.0 and r.command.forward == 0.0


def test_main_prints_one_line_per_tick(capsys):
    assert main(["replay", str(EXAMPLE)]) == 0
    lines = capsys.readouterr().out.strip().splitlines()
    log = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    assert len(lines) == len(log["ticks"])


def test_main_usage_error(capsys):
    assert main(["replay"]) == 2


def test_trace_records_gate_decisions_and_matches_the_replay():
    log = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    data = trace(log)
    assert data["format"] == TRACE_FORMAT
    assert data["settings"]["dead_reckon_s"] == 5.0 and data["settings"]["return_home_s"] == 50.0
    assert len(data["ticks"]) == len(log["ticks"])
    assert [t["mode"] for t in data["ticks"]] == [r.mode.value for _, r in replay(log)]
    rain, spot = data["ticks"][2], data["ticks"][3]
    assert [r["status"] for r in rain["readings"]] == ["rejected", "kept", "kept"]
    assert rain["attention"]["camera"] == pytest.approx(0.4)
    assert [r["status"] for r in spot["readings"]] == ["off", "kept", "kept"]
    lost = data["ticks"][10]
    assert lost["estimate"] is None and lost["reference"] is None and lost["readings"] == []


def test_main_json_prints_a_trace(capsys):
    assert main(["replay", "--json", str(EXAMPLE)]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["format"] == TRACE_FORMAT
    assert data["note"].startswith("Synthetic")


def test_main_outages_reports_the_full_fallback_sequence(capsys):
    assert main(["replay", "--outages", str(EXAMPLE)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report == {"format": OUTAGE_FORMAT, "outages": [{
        "last_estimate_s": 3.0,
        "first_missing_s": 3.5,
        "last_missing_s": 55.0,
        "recovered_s": 55.5,
        "recovered_mode": "tracking",
        "missing_ticks": 104,
        "mode_transitions": [
            {"time_s": 3.5, "mode": "dead_reckoning"},
            {"time_s": 8.5, "mode": "hold"},
            {"time_s": 53.5, "mode": "return_home_requested"},
        ],
    }]}


def test_outages_distinguish_startup_recovery_and_end_of_log():
    # A degraded estimate still closes an outage. Irregular timestamps are retained.
    weak_fix = {"source": "camera", "x": 10.0, "y": 0.0, "variance": 20.0}
    log = {"ticks": [
        {"t": 0.0},
        {"t": 0.4},
        {"t": 2.0, "readings": [weak_fix]},
        {"t": 9.5},
    ]}
    assert outage_report(log)["outages"] == [
        {"last_estimate_s": None, "first_missing_s": 0.0, "last_missing_s": 0.4,
         "recovered_s": 2.0, "recovered_mode": "degraded",
         "missing_ticks": 2, "mode_transitions": [{"time_s": 0.0, "mode": "dead_reckoning"}]},
        {"last_estimate_s": 2.0, "first_missing_s": 9.5, "last_missing_s": 9.5,
         "recovered_s": None, "recovered_mode": None,
         "missing_ticks": 1, "mode_transitions": [{"time_s": 9.5, "mode": "hold"}]},
    ]
    assert outage_report({"ticks": []})["outages"] == []


def test_main_outages_rejects_nonfinite_time(tmp_path, capsys):
    log = tmp_path / "bad-time.json"
    log.write_text('{"ticks":[{"t":"nan"}]}', encoding="utf-8")
    assert main(["replay", "--outages", str(log)]) == 2
    out, err = capsys.readouterr()
    assert out == ""
    assert "finite tick times" in err


@pytest.mark.parametrize("flags", [[], ["--json"], ["--outages"]])
@pytest.mark.parametrize(("contents", "error_detail"), [
    (None, "No such file"),
    (b"\xff", "utf-8"),
    (b"{\n  broken\n}", "line 2 column 3"),
])
def test_main_reports_input_file_errors(tmp_path, capsys, flags, contents, error_detail):
    log = tmp_path / "replay.json"
    if contents is not None:
        log.write_bytes(contents)
    assert main(["replay", *flags, str(log)]) == 2
    out, err = capsys.readouterr()
    assert out == ""
    assert err.startswith(f"could not load replay log {str(log)!r}: ")
    assert error_detail in err


def test_outages_rejects_reverse_order_before_replay(monkeypatch):
    def should_not_replay(log):
        pytest.fail("Invalid timestamps must be rejected before replay")

    monkeypatch.setattr("follow_me.replay.replay", should_not_replay)
    with pytest.raises(ValueError, match="nondecreasing order"):
        outage_report({"ticks": [{"t": 2.0}, {"t": 1.0}]})


def test_main_reports_conflicting_output_formats(capsys):
    assert main(["replay", "--json", "--outages", str(EXAMPLE)]) == 2
    assert "usage:" in capsys.readouterr().err
