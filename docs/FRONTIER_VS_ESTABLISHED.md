# Frontier versus established evidence

**Evidence date: 2026-11-27.**

This boundary records what agent-run checks actually reproduced in the offline software environment. It does not turn simulation into flight evidence, and no owner review is recorded.

## Established: reproduced offline software behavior

- The bounded pre-merge run passed **434 Python tests** with `python3 -m pytest` in the repository's existing Python 3.12.16 virtual environment.
- After fetching and safely reconciling `origin/main`, the exact staged publication snapshot passed **443 Python tests**. The increase comes from incoming main history; neither result is hardware or flight validation.
- The JavaScript suite passed **28 tests**, including deterministic import-generation regressions.
- In offline Chromium with the real vendored Pyodide runtime, Forget was triggered while a synthetic GPX worker job was active. The worker subsequently returned a nonempty trace, but the imported trace remained absent and exactly four built-in examples remained available.
- A valid synthetic two-tick JSON trace loaded and stepped. Malformed JSON was rejected without adding an entry.
- The original replay reproducer and the extended worker check passed. Their measured browser traffic was loopback-only static GET requests: 55 requests over 10 allowed paths for the original check and 66 requests over 33 unique paths for the extended check. Neither observed unexpected requests, request bodies, WebSockets, or page errors.
- The detailed synthetic fixtures, commands, input hashes, and limitations are recorded in [progress.md](progress.md); the extended check writes `_site/replay-forget-receipt.json` locally when given that output path.

These results establish only the named replay and regression behavior in the tested environment. They do not establish that every browser, runtime version, input, or future revision behaves identically.

## Frontier / not established

- Hardware behavior, physical performance, mechanical integrity, radio range, sensing performance, and outdoor operation.
- Flight safety, flight readiness, autonomy claims, and behavior around real people.
- Real routes, real location data, field recordings, and operation outside synthetic fixtures.
- PX4/ArduPilot SITL, hardware-in-the-loop, tethered, free-flight, or other physical validation.
- Privacy, consent, data handling, and bystander protection outside the declared static synthetic fixtures and loopback-only test scope.

## Update when evidence changes

Update this document whenever new evidence changes one of these boundaries. Record the date, exact command or procedure, software revision, fixture or dataset identity, environment, measured result, and limitations. Move an item into **Established** only when the cited result has actually been reproduced; otherwise keep it in **Frontier / not established** with the remaining gap. Never infer hardware, flight, outdoor, SITL, or real-world privacy evidence from these offline software checks.
