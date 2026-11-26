# Interactive 3D scenario sandbox

The scenario page is an engaging way to inspect a **simplified synthetic kinematic simulation**. It covers follow-me pennyboard footage, outdoor soccer pickup, waterproof shallow-water retrieval, indoor soda pickup across a living room, pennyboard pickup, and generic objects on land or water. The implementation is split between `src/follow_me/scenario.py` (the deterministic model) and `site/scenario.html` plus `site/assets/scenario*.js` and `scene3d.js` (the viewer).

Nothing has flown. No drone, tentacle, waterproofing system, gripper, or other hardware exists or has been tested. This is not PX4 or ArduPilot SITL and does not satisfy the simulator gate. The old 2D follow controller and `sim.py` behavior are separate and unchanged.

## Presets

| Stable ID | Target and world | What the trace demonstrates |
|---|---|---|
| `follow_ride` | Synthetic consenting rider and pennyboard, outdoor land | A 24 s scripted follow with ideal onboard framing. No pickup or real footage. |
| `soccer_land` | Illustrative size-5 soccer ball, outdoor land | Approach, grasp, lift, carry, and release on the dry drop pad. |
| `soccer_water` | Soccer ball at shallow fixed depth, outdoor water | A waterproof tentacle tip submerges while the drone body remains above water. |
| `indoor_soda` | Soda can, simple living-room floor and walls | A small-target retrieval with a visible marker and label in the viewport. |
| `pennyboard_land` | Illustrative pennyboard, outdoor land | Pickup and relocation of the board without a rider. |
| `object_sandbox` | Generic object; indoor/outdoor, land/water, waterproof on/off | Independent sandbox settings and explicit capability failures. |

All positions are local synthetic offsets in metres, with **z up**. There are no maps, coordinates, or real routes. Preset traces are generated from the Python core at site build time and need no Python download in the browser.

## Using the page

1. Choose a preset. Its prebuilt trace loads paused at frame zero, and the sandbox controls show that preset's settings.
2. Use **Play**, **Previous**, **Next**, the native timeline slider, or an event's time button. Playback stops at `complete` or `stopped`; playing again from the end restarts at zero. Nothing autoplays on page load. Reduced-motion preferences select 1× speed and disable decorative motion; manually requested playback remains available.
3. Switch between **External orbit** and **Onboard · simulated footage**. Drag or scroll the external 3D view, or use the adjacent native orbit/raise/lower/zoom buttons. **Reset camera** restores the suggested external view. In onboard mode the view is computed from the frame's camera pose; it is not actual recording.
4. To customize, change target, indoor/outdoor, land/water, waterproof, or the illustrative generic mass, then choose **Run scenario**. Changing a setting pauses playback, marks the previous trace as stale, and disables transport until the new run or a preset reset. Custom runs use the same Python in a same-origin Pyodide worker. Changing settings while a run is in flight makes its response stale, so it is discarded rather than overwriting newer choices.
5. **Reset to preset** discards custom settings and restores the selected prebuilt trace.

Space toggles playback and Left/Right Arrow step one frame only when focus is not in a native control, link, or editable element. Phase changes and terminal outcomes are announced politely; frame descriptions are not sent to an aria-live region on every animation frame. Hiding the page pauses playback.

A water run with **Waterproof tentacle unchecked** returns a stopped mission before submerging. The checkbox stays unchecked and the reason is shown in the status, current description, and event table. The page never silently substitutes `waterproof=true`. An overweight generic object similarly stops before pickup.

## Sandbox inputs and illustrative objects

| Target | Illustrative mass | Full x/y/z dimensions | Notes |
|---|---:|---|---|
| Soccer ball | 0.43 kg | 0.22 × 0.22 × 0.22 m | Size-5-like geometry, not a measured ball. |
| Soda can | 0.39 kg | 0.066 × 0.066 × 0.122 m | Full 330 ml-like can, not a measured object. |
| Pennyboard | 2.4 kg | 0.57 × 0.15 × 0.10 m | Small plastic-board-like geometry, not a hardware specification. |
| Generic object | Default 0.25 kg; page input 0.05–20 kg | 0.12 × 0.08 × 0.06 m | Mass is configurable in the core; dimensions remain fixed in the page. |

These are illustrative values. Generic mass affects the model's 3 kg payload check; it does not change flight dynamics because there are no flight dynamics. The core also checks grip width, reach, world bounds, shallow depth, and the dry drop zone. A supported configuration can still be completely unrelated to a feasible real mission.

## Mission state machine

Retrieval runs through:

```
approach → align → descend → extend → grasp → lift → carry → release → complete
```

- **Approach:** move above the target at cruise altitude.
- **Align:** hold over the target briefly.
- **Descend:** reach the pickup hover position, retaining drone-body water clearance.
- **Extend:** extend the idealized prismatic tentacle to the fixed gripper offset.
- **Grasp:** attach the target scriptingly; there is no contact solver.
- **Lift / carry:** move the attached target to the safe synthetic dry pad.
- **Release / complete:** detach at the pad and record success.

Invalid or unsupported settings return `stopped` with a reason instead of a false success. A frame-limit exhaustion also becomes `stopped`. Follow mode has its own `follow → complete` path and can stop for missing scripted consent or leaving the bounded world.

## Trace and camera contract

`trace_scenario(config)` returns JSON-compatible `config`, `frames`, `events`, and `summary`. Each frame includes:

- `t_s`, `phase`, and `status`;
- `drone_flight.position`, `velocity`, `yaw_deg`, `in_water`, and `submersion_depth_m`;
- the target's position, dimensions, mass, attachment, and water state;
- `tentacle.tip_position`, extension, waterproof flag, water state, and grasp state;
- `onboard_camera_pose` and `camera_framing`;
- optional synthetic `follow` metadata and a suggested `viewer_orbit_camera`.

The drone pose, ideal stabilized onboard camera pose, and external viewer camera are deliberately separate. Moving the external orbit camera does not change framing statistics or the follow logic. The summary records success/reason, pickup/release, water contact, drop error, and follow framing shares/errors. Follow metadata explicitly says the rider is synthetic and consenting, with no bystanders or real footage.

## Rendering and failure behavior

The viewport procedurally draws a schematic drone, arms and rotors, a tentacle and gripper at the core's exact tip position, the selected object, a safe drop pad, and the appropriate outdoor ground, translucent water, or living-room shell. Follow mode adds a geometric synthetic rider and board. Small objects receive a ring and label. These are readability aids, not scale-certified engineering models.

The already pinned three.js and OrbitControls are imported through the site's import map. Rendering is requested only for playback, scrubbing, orbiting, resizing, and theme changes. If the import or WebGL context fails, or the build has no vendor files, a top-down SVG fallback keeps the scene, controls, descriptions, and event table useful. The fallback does not pretend to reproduce onboard perspective.

The page makes no backend, analytics, upload, or external runtime requests. Default traces, Python modules, Pyodide, and three.js are all served from the same static site. No new vendor dependency was introduced.

## Model limitations

- Fixed-step kinematics only: no aerodynamics, motors, wind, battery, collisions, obstacle avoidance, autopilot, PX4, or ArduPilot.
- One idealized prismatic tentacle and fixed gripper offset: no flexible-body, grip, waterproofing, or contact physics.
- Fixed-depth illustrative buoyancy and zero drag: no waves, current, fluid forces, or realistic water interaction.
- Perfectly known poses and an ideal stabilized camera: no occlusion, lens distortion, detection noise, recording, or camera-hardware validation.
- Static targets until scripted attachment; no drop bounce or release dynamics.
- Illustrative dimensions, masses, speeds, reach, and limits: not measurements or safe operating limits.
- Synthetic rider with scripted consent only; no real rider, bystanders, footage, coordinates, or routes.

## Offline synthetic handoff export

`follow_me.handoff` converts existing **retrieval** traces without a network, sibling-repository import, or runtime schema dependency. The intermediate `follow-me-synthetic-handoffs/1` report contains anonymous `scenario-01`/`job-01` IDs, relative seconds, a canonical source-trace SHA-256 and `follow-me-scenario-v1` source version, plus fixed consent, privacy, and limitation labels. It exports no names, source messages, real coordinates, routes, or footage. Follow traces are rejected rather than treated as object retrieval or consent evidence.

The initial `approach` phase event supports readiness at relative second zero. Only an actual `release` event creates a synthetic handoff completion; a completed retrieval also requires its actual `complete` event. An incomplete trace can export a job with no handoff. Missing required lifecycle events and duplicate approach/release/complete events are rejected. Existing traces have no prerequisite or evidence-receipt events, so version 1 omits `depends_on` and `evidence_minute`, and sets `evidence_recorded` to `false`. `grasp`, `complete`, and scripted phase names never become evidence receipts, physical grasp success, real delivery, inspection acceptance, or flight readiness.

`convert` targets the separately consumed **`synthetic-aerial-handoffs/1`** JSON Schema (`https://example.invalid/schemas/synthetic-aerial-handoffs/1/handoffs.schema.json`, draft 2020-12). That schema forbids additional envelope fields, so provenance and labels stay in the intermediate report. Conversion requires both an explicit output path and `--due-minute`: the deadline is a caller-supplied synthetic analysis input, not a scenario fact. Seconds become integer minutes by `ceil(seconds / 60)`, so an event is never reported early; the consumer range is 0 through 10080. Unsupported report fields and evidence claims are rejected.

```sh
# After a website build has created _site/, make a disposable synthetic source trace.
PYTHONPATH=src python3 -c "from pathlib import Path; from follow_me.handoff import json_bytes; from follow_me.scenario import trace_scenario; Path('_site/soccer_land.trace.json').write_bytes(json_bytes(trace_scenario('soccer_land')))"

# Write the source report, then the consumer document. No file is written by default.
PYTHONPATH=src python3 -m follow_me.handoff report _site/soccer_land.trace.json --output _site/soccer_land.handoff-report.json
PYTHONPATH=src python3 -m follow_me.handoff convert _site/soccer_land.handoff-report.json --output _site/soccer_land.handoffs.json --due-minute 1
PYTHONPATH=src python3 -m pytest -q tests/test_handoff.py
```

The shipped `soccer_land` release at 15.3 s becomes `completed_minute: 1`; deadline minute 1 is therefore the on-time boundary under the consumer's inclusive rule. This is deterministic synthetic event scheduling only, not evidence about hardware or a real service.

## Commands

```sh
# Run the core and its focused tests.
PYTHONPATH=src .venv/bin/python -m pytest -q tests/test_scenario.py

# Inspect a preset or a deliberately rejected water attempt.
PYTHONPATH=src .venv/bin/python -c "from follow_me.scenario import run_preset; print(run_preset('soccer_water').summary)"
PYTHONPATH=src .venv/bin/python -c "from follow_me.scenario import run_preset; print(run_preset('soccer_water', waterproof=False).summary)"

# Build all six prebuilt traces and the scenario page (with the SVG fallback).
PYTHONPATH=src .venv/bin/python -m follow_me.website _site

# Include pinned local three.js and Pyodide, enabling 3D and custom browser runs.
PYTHONPATH=src .venv/bin/python -m follow_me.website _site --vendor --render-parts

# Test the browser's pure helpers along with the existing JavaScript helpers.
node --test "tests/js/*.test.mjs"
```

The website tests verify every generated preset against the core, browser Python module copies, local links, navigation, and privacy/honesty rules. The pure JavaScript tests cover configuration conversion, trace validation, timeline edges, descriptions, event navigation, and formatting. See [website.md](website.md) for the full build and [privacy-and-rules.md](privacy-and-rules.md) for footage and bystander rules.
