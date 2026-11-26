"""Offline synthetic handoff reports and aerial-schema conversion.

The source is a ``follow-me-scenario-v1`` retrieval trace. The intermediate
``follow-me-synthetic-handoffs/1`` report retains provenance and safety/privacy
labels. Its ``convert_report`` function emits only ``synthetic-aerial-handoffs/1``
fields; that consumer schema forbids envelope metadata.

No delivery, inspection acceptance, flight readiness, evidence receipt, or
physical grasp is asserted. A deadline is an explicit synthetic analysis input,
not a fact inferred from the scenario.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

from follow_me.scenario import SCENARIO_FORMAT

REPORT_FORMAT = "follow-me-synthetic-handoffs/1"  # SECRETS-GUARD-IGNORE: public format ID
AERIAL_SCHEMA = "synthetic-aerial-handoffs/1"
AERIAL_SCHEMA_ID = (
    "https://example.invalid/schemas/synthetic-aerial-handoffs/1/handoffs.schema.json"
)
MAX_MINUTE = 10080
CONSENT_NOTE = (
    "Object-only synthetic retrieval; no person is followed or recorded, and no "
    "real-footage consent is represented."
)
PRIVACY_NOTE = (
    "Anonymous job IDs and relative synthetic event times only; no names, real "
    "coordinates, routes, source messages, or footage are exported."
)
LIMITATIONS_NOTE = (
    "Scripted synthetic handoff availability only; not real delivery, inspection "
    "acceptance, flight readiness, evidence receipt, or physical grasp success."
)

_IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _object(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be an object")
    return value


def _keys(
    value: dict[str, Any], name: str, required: set[str], optional: set[str] | None = None,
) -> None:
    allowed = required | (optional or set())
    missing = required - value.keys()
    unknown = value.keys() - allowed
    if missing:
        raise ValueError(f"{name} is missing fields: {sorted(missing)}")
    if unknown:
        raise ValueError(f"{name} has unsupported fields: {sorted(unknown)}")


def _seconds(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite nonnegative number of seconds")
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise ValueError(f"{name} must be a finite nonnegative number of seconds")
    return result


def _minute(seconds: Any, name: str) -> int:
    """Round up to a relative minute so an event is never reported early."""
    result = math.ceil(_seconds(seconds, name) / 60.0)
    if result > MAX_MINUTE:
        raise ValueError(f"{name} exceeds the consumer minute limit")
    return result


def _identifier(value: Any, name: str) -> str:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise ValueError(f"{name} must be an anonymous consumer identifier")
    return value


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False,
    ).encode("utf-8")


def json_bytes(value: Any) -> bytes:
    """Stable UTF-8 JSON bytes, including one final newline."""
    return (
        json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False)
        + "\n"
    ).encode("utf-8")


def _matching(events: list[dict[str, Any]], kind: str, phase: str) -> list[dict[str, Any]]:
    return [
        event for event in events
        if event.get("kind") == kind and event.get("phase") == phase
    ]


def build_report(trace: dict[str, Any]) -> dict[str, Any]:
    """Build a privacy-reduced synthetic report from one retrieval trace.

    The initial approach event supports readiness. A release event supports a
    synthetic handoff; without one, the job has no handoff. Existing traces have
    no prerequisite or evidence-receipt events, so neither is synthesized.
    """
    _object(trace, "scenario trace")
    if trace.get("format") != SCENARIO_FORMAT:
        raise ValueError(f"scenario trace format must be {SCENARIO_FORMAT}")
    config = _object(trace.get("config"), "scenario config")
    if config.get("mode") != "retrieval":
        raise ValueError("only object-only synthetic retrieval traces can be exported")
    summary = _object(trace.get("summary"), "scenario summary")
    raw_events = trace.get("events")
    if not isinstance(raw_events, (list, tuple)):
        raise ValueError("scenario events must be an array")

    events: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_events):
        event = _object(raw, f"event {index}")
        _seconds(event.get("t_s"), f"event {index} time")
        if not isinstance(event.get("kind"), str) or not isinstance(event.get("phase"), str):
            raise ValueError(f"event {index} kind and phase must be strings")
        events.append(event)

    approaches = _matching(events, "phase", "approach")
    releases = _matching(events, "release", "release")
    completions = _matching(events, "complete", "complete")
    if len(approaches) != 1 or _seconds(approaches[0]["t_s"], "approach") != 0.0:
        raise ValueError("exactly one approach phase event at relative second zero is required")
    if len(releases) > 1 or len(completions) > 1:
        raise ValueError("duplicate release or complete events are ambiguous")

    ready_s = _seconds(approaches[0]["t_s"], "approach")
    handoffs: list[dict[str, Any]] = []
    if releases:
        release_s = _seconds(releases[0]["t_s"], "release")
        if len(completions) != 1:
            raise ValueError("a released retrieval requires exactly one complete event")
        complete_s = _seconds(completions[0]["t_s"], "complete")
        if not ready_s <= release_s <= complete_s:
            raise ValueError("approach, release, and complete events must be ordered")
        if summary.get("success") is not True or summary.get("released") is not True:
            raise ValueError("release events must agree with the synthetic scenario summary")
        handoffs.append({
            "job_id": "job-01",
            "completed_s": release_s,
            "evidence_recorded": False,
        })
    else:
        if completions:
            raise ValueError("a complete event without a release is not a handoff")
        if summary.get("success") is not False or summary.get("released") is not False:
            raise ValueError("a trace without release must be an incomplete retrieval")

    source_hash = hashlib.sha256(_canonical_bytes(trace)).hexdigest()
    return {
        "format": REPORT_FORMAT,
        "synthetic": True,
        "consent": CONSENT_NOTE,
        "privacy": PRIVACY_NOTE,
        "limitations": LIMITATIONS_NOTE,
        "scenarios": [{
            "id": "scenario-01",
            "source": {"format": SCENARIO_FORMAT, "sha256": source_hash},
            "jobs": [{"id": "job-01", "ready_s": ready_s}],
            "handoffs": handoffs,
        }],
    }


def _validate_report(report: dict[str, Any]) -> None:
    _object(report, "handoff report")
    _keys(
        report, "handoff report",
        {"format", "synthetic", "consent", "privacy", "limitations", "scenarios"},
    )
    if report.get("format") != REPORT_FORMAT or report.get("synthetic") is not True:
        raise ValueError(f"report must be explicitly synthetic {REPORT_FORMAT}")
    for field, expected in (
        ("consent", CONSENT_NOTE), ("privacy", PRIVACY_NOTE), ("limitations", LIMITATIONS_NOTE),
    ):
        if report.get(field) != expected:
            raise ValueError(f"report {field} label is missing or changed")
    scenarios = report.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        raise ValueError("report scenarios must be a nonempty array")

    scenario_ids: set[str] = set()
    for scenario_index, raw_scenario in enumerate(scenarios):
        name = f"scenario {scenario_index}"
        scenario = _object(raw_scenario, name)
        _keys(scenario, name, {"id", "source", "jobs", "handoffs"})
        scenario_id = _identifier(scenario.get("id"), f"{name} id")
        if scenario_id in scenario_ids:
            raise ValueError("duplicate scenario IDs are not supported")
        scenario_ids.add(scenario_id)
        source = _object(scenario.get("source"), f"{name} source")
        _keys(source, f"{name} source", {"format", "sha256"})
        if source.get("format") != SCENARIO_FORMAT:
            raise ValueError("unsupported source scenario format")
        if not isinstance(source.get("sha256"), str) or not _SHA256.fullmatch(source["sha256"]):
            raise ValueError("source sha256 must be a lowercase SHA-256 digest")
        jobs = scenario.get("jobs")
        handoffs = scenario.get("handoffs")
        if not isinstance(jobs, list) or not jobs or not isinstance(handoffs, list):
            raise ValueError(f"{name} requires jobs and a handoff array")

        job_times: dict[str, float] = {}
        for job_index, raw_job in enumerate(jobs):
            job_name = f"{name} job {job_index}"
            job = _object(raw_job, job_name)
            _keys(job, job_name, {"id", "ready_s"})
            job_id = _identifier(job.get("id"), f"{job_name} id")
            if job_id in job_times:
                raise ValueError("duplicate job IDs are not supported")
            job_times[job_id] = _seconds(job.get("ready_s"), f"{job_name} ready_s")

        handed_off: set[str] = set()
        for handoff_index, raw_handoff in enumerate(handoffs):
            handoff_name = f"{name} handoff {handoff_index}"
            handoff = _object(raw_handoff, handoff_name)
            _keys(handoff, handoff_name, {"job_id", "completed_s", "evidence_recorded"})
            job_id = _identifier(handoff.get("job_id"), f"{handoff_name} job_id")
            if job_id not in job_times or job_id in handed_off:
                raise ValueError("handoffs must reference one known job exactly once")
            handed_off.add(job_id)
            completed_s = _seconds(handoff.get("completed_s"), f"{handoff_name} completed_s")
            if completed_s < job_times[job_id]:
                raise ValueError("handoff completion cannot precede readiness")
            if handoff.get("evidence_recorded") is not False:
                raise ValueError("version 1 has no evidence-receipt event and requires false")


def convert_report(report: dict[str, Any], *, due_minute: int) -> dict[str, Any]:
    """Convert a validated report to the version-1 aerial consumer document.

    ``due_minute`` is mandatory because scenario traces contain no deadline.
    Evidence minutes and dependencies remain absent rather than being invented.
    """
    _validate_report(report)
    if isinstance(due_minute, bool) or not isinstance(due_minute, int):
        raise ValueError("due_minute must be an explicit integer")
    if not 0 <= due_minute <= MAX_MINUTE:
        raise ValueError(f"due_minute must be between 0 and {MAX_MINUTE}")

    scenarios = []
    for source_scenario in report["scenarios"]:
        jobs = []
        ready_by_job = {}
        for source_job in source_scenario["jobs"]:
            ready_minute = _minute(source_job["ready_s"], "job ready_s")
            if due_minute < ready_minute:
                raise ValueError("due_minute cannot precede ready_minute")
            ready_by_job[source_job["id"]] = ready_minute
            jobs.append({
                "id": source_job["id"],
                "ready_minute": ready_minute,
                "due_minute": due_minute,
            })
        handoffs = []
        for source_handoff in source_scenario["handoffs"]:
            completed_minute = _minute(source_handoff["completed_s"], "handoff completed_s")
            if completed_minute < ready_by_job[source_handoff["job_id"]]:
                raise ValueError("converted handoff completion cannot precede readiness")
            handoffs.append({
                "job_id": source_handoff["job_id"],
                "completed_minute": completed_minute,
                "evidence_recorded": False,
            })
        scenarios.append({
            "id": source_scenario["id"], "jobs": jobs, "handoffs": handoffs,
        })
    return {"schema": AERIAL_SCHEMA, "scenarios": scenarios}


def _load(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)
    report_parser = subcommands.add_parser("report", help="write a synthetic source report")
    report_parser.add_argument("trace", help="follow-me-scenario-v1 JSON trace")
    report_parser.add_argument("--output", required=True, help="explicit report output path")
    convert_parser = subcommands.add_parser("convert", help="write aerial-schema JSON")
    convert_parser.add_argument("report", help="follow-me-synthetic-handoffs/1 JSON report")
    convert_parser.add_argument("--output", required=True, help="explicit consumer output path")
    convert_parser.add_argument("--due-minute", required=True, type=int, help="synthetic deadline")
    try:
        args = parser.parse_args(argv)
    except SystemExit as error:
        return int(error.code)

    try:
        if args.command == "report":
            document = build_report(_load(args.trace))
        else:
            document = convert_report(_load(args.report), due_minute=args.due_minute)
        encoded = json_bytes(document)
        Path(args.output).write_bytes(encoded)
    except (KeyError, OSError, OverflowError, TypeError, ValueError) as error:
        print(f"handoff export: {error}", file=sys.stderr)
        return 2
    print(f"wrote {args.output} ({len(encoded)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
