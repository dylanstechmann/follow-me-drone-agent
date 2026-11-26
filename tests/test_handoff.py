"""Offline synthetic handoff report and consumer-conversion contract tests."""

from copy import deepcopy
import hashlib
import json

import pytest

from follow_me.handoff import (
    AERIAL_SCHEMA,
    AERIAL_SCHEMA_ID,
    CONSENT_NOTE,
    LIMITATIONS_NOTE,
    PRIVACY_NOTE,
    REPORT_FORMAT,
    build_report,
    convert_report,
    json_bytes,
    main,
)
from follow_me.scenario import SCENARIO_FORMAT, trace_scenario


BASE_TRACE = trace_scenario("soccer_land")


def retrieval_trace():
    return deepcopy(BASE_TRACE)


def only_event(trace, kind):
    return next(event for event in trace["events"] if event["kind"] == kind)


def test_report_is_synthetic_private_anonymous_and_source_versioned():
    trace = retrieval_trace()
    report = build_report(trace)
    assert report["format"] == REPORT_FORMAT
    assert report["synthetic"] is True
    assert report["consent"] == CONSENT_NOTE
    assert report["privacy"] == PRIVACY_NOTE
    assert report["limitations"] == LIMITATIONS_NOTE
    assert "no person is followed or recorded" in report["consent"]
    assert "Anonymous job IDs" in report["privacy"]
    assert "no names, real coordinates, routes" in report["privacy"]

    scenario = report["scenarios"][0]
    assert scenario["id"] == "scenario-01"
    assert scenario["jobs"] == [{"id": "job-01", "ready_s": 0.0}]
    assert scenario["handoffs"][0]["job_id"] == "job-01"
    assert scenario["source"]["format"] == SCENARIO_FORMAT
    canonical = json.dumps(
        trace, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False,
    ).encode("utf-8")
    assert scenario["source"]["sha256"] == hashlib.sha256(canonical).hexdigest()
    encoded = json_bytes(report).decode("utf-8")
    assert "soccer_land" not in encoded
    assert "target_position" not in encoded
    assert "rider_id" not in encoded


def test_consumer_document_has_every_required_field_and_no_extra_envelope():
    document = convert_report(build_report(retrieval_trace()), due_minute=1)
    assert set(document) == {"schema", "scenarios"}
    assert document["schema"] == AERIAL_SCHEMA == "synthetic-aerial-handoffs/1"
    assert AERIAL_SCHEMA_ID.endswith("/synthetic-aerial-handoffs/1/handoffs.schema.json")
    scenario = document["scenarios"][0]
    assert set(scenario) == {"id", "jobs", "handoffs"}
    job = scenario["jobs"][0]
    handoff = scenario["handoffs"][0]
    assert set(job) == {"id", "ready_minute", "due_minute"}
    assert set(handoff) == {"job_id", "completed_minute", "evidence_recorded"}
    assert job == {"id": "job-01", "ready_minute": 0, "due_minute": 1}
    assert handoff == {
        "job_id": "job-01", "completed_minute": 1, "evidence_recorded": False,
    }
    assert "source" not in scenario and "synthetic" not in document


@pytest.mark.parametrize(
    "release_s, expected_minute",
    [(0.0, 0), (0.001, 1), (59.999, 1), (60.0, 1), (60.001, 2), (604800.0, 10080)],
)
def test_seconds_convert_to_ceiling_relative_minutes(release_s, expected_minute):
    trace = retrieval_trace()
    only_event(trace, "release")["t_s"] = release_s
    only_event(trace, "complete")["t_s"] = release_s + 0.001
    report = build_report(trace)
    document = convert_report(report, due_minute=expected_minute)
    handoff = document["scenarios"][0]["handoffs"][0]
    assert handoff["completed_minute"] == expected_minute
    assert document["scenarios"][0]["jobs"][0]["ready_minute"] == 0


def test_deadline_is_explicit_and_completion_at_deadline_is_not_delayed():
    report = build_report(retrieval_trace())
    on_time = convert_report(report, due_minute=1)
    late = convert_report(report, due_minute=0)
    assert on_time["scenarios"][0]["jobs"][0]["due_minute"] == 1
    assert on_time["scenarios"][0]["handoffs"][0]["completed_minute"] == 1
    assert late["scenarios"][0]["jobs"][0]["due_minute"] == 0
    assert late["scenarios"][0]["handoffs"][0]["completed_minute"] == 1
    for invalid in (True, 1.0, "1", -1, 10081):
        with pytest.raises(ValueError, match="due_minute"):
            convert_report(report, due_minute=invalid)


def test_complete_and_grasp_never_become_evidence_or_prerequisites():
    trace = retrieval_trace()
    assert only_event(trace, "complete")["t_s"] > only_event(trace, "release")["t_s"]
    assert only_event(trace, "grasp")["kind"] == "grasp"
    report = build_report(trace)
    handoff = report["scenarios"][0]["handoffs"][0]
    assert handoff["evidence_recorded"] is False
    assert set(handoff) == {"job_id", "completed_s", "evidence_recorded"}
    converted = convert_report(report, due_minute=1)
    output_handoff = converted["scenarios"][0]["handoffs"][0]
    assert "evidence_minute" not in output_handoff
    assert "depends_on" not in converted["scenarios"][0]["jobs"][0]
    assert output_handoff["completed_minute"] == 1


def test_incomplete_retrieval_exports_a_job_without_inventing_a_handoff():
    trace = trace_scenario("soccer_land", max_frames=2)
    assert trace["summary"]["success"] is False
    report = build_report(trace)
    assert report["scenarios"][0]["handoffs"] == []
    converted = convert_report(report, due_minute=1)
    assert converted["scenarios"][0]["jobs"] == [
        {"id": "job-01", "ready_minute": 0, "due_minute": 1}
    ]
    assert converted["scenarios"][0]["handoffs"] == []


def test_missing_approach_or_complete_events_are_rejected():
    missing_approach = retrieval_trace()
    missing_approach["events"] = [
        event for event in missing_approach["events"]
        if not (event["kind"] == "phase" and event["phase"] == "approach")
    ]
    with pytest.raises(ValueError, match="approach"):
        build_report(missing_approach)

    missing_complete = retrieval_trace()
    missing_complete["events"] = [
        event for event in missing_complete["events"] if event["kind"] != "complete"
    ]
    with pytest.raises(ValueError, match="complete"):
        build_report(missing_complete)

    missing_release = retrieval_trace()
    missing_release["events"] = [
        event for event in missing_release["events"] if event["kind"] != "release"
    ]
    with pytest.raises(ValueError, match="without a release"):
        build_report(missing_release)


@pytest.mark.parametrize("kind", ["release", "complete"])
def test_duplicate_terminal_events_are_rejected(kind):
    trace = retrieval_trace()
    trace["events"] = list(trace["events"])
    trace["events"].append(deepcopy(only_event(trace, kind)))
    with pytest.raises(ValueError, match="duplicate release or complete"):
        build_report(trace)


def test_duplicate_approach_event_is_rejected():
    trace = retrieval_trace()
    trace["events"] = list(trace["events"])
    approach = next(
        event for event in trace["events"]
        if event["kind"] == "phase" and event["phase"] == "approach"
    )
    trace["events"].append(deepcopy(approach))
    with pytest.raises(ValueError, match="exactly one approach"):
        build_report(trace)


@pytest.mark.parametrize("bad_time", [True, "15.3", None, -0.1, float("nan"), float("inf")])
def test_malformed_event_times_are_rejected(bad_time):
    trace = retrieval_trace()
    only_event(trace, "release")["t_s"] = bad_time
    with pytest.raises(ValueError, match="seconds"):
        build_report(trace)


def test_scripted_phase_names_alone_do_not_create_a_handoff_or_validation():
    trace = retrieval_trace()
    for event in trace["events"]:
        if event["kind"] in {"release", "complete"}:
            event["kind"] = "phase"
    trace["summary"]["success"] = False
    trace["summary"]["released"] = False
    trace["summary"]["final_phase"] = "stopped"
    report = build_report(trace)
    assert report["scenarios"][0]["handoffs"] == []
    assert "not real delivery, inspection acceptance, flight readiness" in report["limitations"]
    assert "physical grasp success" in report["limitations"]
    converted_text = json_bytes(convert_report(report, due_minute=1)).decode("utf-8")
    for forbidden in ("grasp", "inspection", "flight_ready", "delivery", "validated"):
        assert forbidden not in converted_text


def test_follow_trace_is_not_an_object_handoff_and_consent_is_not_assumed():
    with pytest.raises(ValueError, match="object-only synthetic retrieval"):
        build_report(trace_scenario("follow_ride"))


def test_unsupported_report_fields_and_evidence_claims_are_rejected():
    with_dependency = build_report(retrieval_trace())
    with_dependency["scenarios"][0]["jobs"][0]["depends_on"] = []
    with pytest.raises(ValueError, match="unsupported fields"):
        convert_report(with_dependency, due_minute=1)

    with_evidence_time = build_report(retrieval_trace())
    with_evidence_time["scenarios"][0]["handoffs"][0]["evidence_s"] = 15.4
    with pytest.raises(ValueError, match="unsupported fields"):
        convert_report(with_evidence_time, due_minute=1)

    with_evidence = build_report(retrieval_trace())
    with_evidence["scenarios"][0]["handoffs"][0]["evidence_recorded"] = True
    with pytest.raises(ValueError, match="no evidence-receipt event"):
        convert_report(with_evidence, due_minute=1)


def test_changed_or_removed_consent_privacy_and_limitations_labels_are_rejected():
    for field in ("consent", "privacy", "limitations"):
        report = build_report(retrieval_trace())
        report[field] = ""
        with pytest.raises(ValueError, match=field):
            convert_report(report, due_minute=1)


def test_report_and_consumer_bytes_are_deterministic():
    first = build_report(retrieval_trace())
    second = build_report(retrieval_trace())
    assert json_bytes(first) == json_bytes(second)
    assert json_bytes(first).endswith(b"\n")
    first_converted = convert_report(first, due_minute=1)
    second_converted = convert_report(second, due_minute=1)
    assert json_bytes(first_converted) == json_bytes(second_converted)


def test_cli_round_trip_requires_and_uses_explicit_output_paths(tmp_path, capsys):
    trace_path = tmp_path / "source.trace.json"
    report_path = tmp_path / "report.json"
    output_path = tmp_path / "handoffs.json"
    trace_path.write_bytes(json_bytes(retrieval_trace()))
    assert main(["report", str(trace_path)]) == 2
    assert not report_path.exists()
    assert main(["report", str(trace_path), "--output", str(report_path)]) == 0
    assert report_path.read_bytes() == json_bytes(build_report(retrieval_trace()))

    assert main(["convert", str(report_path), "--output", str(output_path)]) == 2
    assert not output_path.exists()
    assert main([
        "convert", str(report_path), "--output", str(output_path), "--due-minute", "1",
    ]) == 0
    expected = convert_report(build_report(retrieval_trace()), due_minute=1)
    assert output_path.read_bytes() == json_bytes(expected)
    assert json.loads(output_path.read_text(encoding="utf-8"))["schema"] == AERIAL_SCHEMA
    capsys.readouterr()


def test_cli_errors_do_not_write_consumer_output(tmp_path, capsys):
    report_path = tmp_path / "bad-report.json"
    output_path = tmp_path / "handoffs.json"
    report_path.write_text('{"format": "wrong"}', encoding="utf-8")
    assert main([
        "convert", str(report_path), "--output", str(output_path), "--due-minute", "1",
    ]) == 2
    assert not output_path.exists()
    assert "handoff export:" in capsys.readouterr().err
