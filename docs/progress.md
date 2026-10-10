# Progress log

Working loop: plan (write it here), do it (code plus tests), commit and push, record the result, then plan the next iteration. The loop repeats until the owner says stop.

## Plan 0: documentation (done)

- architecture, sensors and companion, build plan, privacy and rules.
- Location data kept out of the repo.

## Iteration 1: council fusion core (done: 28 tests pass)

- `Estimate`, `Reading`, and `fuse()` with a robust median gate and inverse-variance weighting.
- `camera_estimate()` converts a person box to a body-frame estimate using the geometry in [sensors-and-companion.md](sensors-and-companion.md).
- Tests for agreement, outlier rejection, total disagreement, zero reliability, and camera geometry.

## Iteration 2: context and attention (done: 42 tests pass)

- `Conditions`, `attention()` multipliers for weather, link and GNSS quality, and overrides from places.
- `WeatherProvider` interface, an Open-Meteo adapter (fetch injected, so tests make no network calls), and a TTL cache.

## Iteration 3: places (done: 55 tests pass)

- `geo.py` with haversine, local east/north offsets and bearing.
- `places.py` with a `Place` model, JSON loading, and approach detection (inside the radius or ahead on heading).
- `examples/places.example.json` with fake coordinates only.

## Iteration 4: mode machine and integration (done: 67 tests pass)

- `mode.py` with TRACKING, DEGRADED, DEAD_RECKONING, HOLD and RETURN_HOME_REQUESTED.
- One integration test that chains readings → attention → fusion → mode.

## Iteration 5: replay harness, gate 2 (done: 76 tests pass)

- `council.py` runs one tick end to end: attention, fusion, mode, controller, mode gain.
- `replay.py` runs a JSON sensor log through the council and prints one line per tick (`python -m follow_me.replay LOG.json`).
- Found and fixed a flaw from iteration 1 while writing the replay scenario. With two sources, the median reference was their midpoint, so both were rejected even when one was far more reliable. The gate now uses a reliability-weighted median.
- The example log is synthetic (fake numbers) and exercises tracking, rain, link loss, dead reckoning, hold, return-home request, and recovery.
- Limitation: the controller still expects image-style boxes. Fused estimates are converted back to boxes with the inverse camera geometry, which loses vertical information.

## Iteration 6: companion GNSS, phone and tag (done: 92 tests pass)

- Owner decision: both a dedicated tag and the phone app, plus other devices only when they earn their place (see [companion-tiers.md](companion-tiers.md) once written).
- `companion.py`: a rider GNSS fix becomes a body-frame `Estimate` using the drone's heading. Stale or future fixes return `None`. Heading error adds variance.
- Source names split into `phone_gnss` and `tag_gnss`, so two independent receivers can disagree and be weighed. Link and GNSS quality are now per source.
- Tests: geometry for each heading, stale and future fixes, variance terms, and a council run with phone, tag and camera.
- Found while testing: the default degraded threshold was 4 m² (2 m one-sigma). A single 2 m GNSS fix at 10 m would be called "degraded". The default is now 9 m² (3 m one-sigma). This is a guess to tune on real logs, not a measured value.
- The replay example now has both companions, a phone-link dropout where the tag carries the estimate, and the full fallback ladder.

## Iteration 7: parts catalog and cost passes (done: 119 tests pass)

- `bom/catalog.json` lists each priced part with a status: snapshot, official, estimate, placeholder, owned, or unpriced. Prices came from web searches on 2026-10-10. Most are undated snapshots, so each one needs checking at the seller.
- `bom/passes.json` records five cost passes as deltas on a base pass, each with the reason and the risk it adds.
- `follow_me.bom` resolves the passes, totals core and optional costs, counts placeholders and unpriced items, reports the change against each pass's base, and checks the $100 budget.
- Results (core, USD, low to high):
  - pass0 retail autopilot: $571 to $1,004
  - pass1 used autopilot, Pi Zero streams video: $509 to $778
  - pass2 printed frame and guards: $482 to $725
  - pass3 bench-first kit: $78 to $130, fits $100 at low prices only (optional Tello $79 to $139)
  - pass4 owned phone as the drone computer: $447 to $685
- Finding: the autopilot flight controller and the transmitter are most of the cost. A flying drone does not fit in $100 with any pass so far. The $100 budget covers the bench kit and one tag.
- Found while checking: the report compared each pass with the line above it. Pass 4 is based on pass 2, so it now compares against its base.

## Iteration 8: documentation from the data (done: 119 tests pass)

- `docs/parts-catalog.md` is generated from the catalog (`python -m follow_me.bom --markdown`). Regenerate it after any catalog change.
- `docs/cost-reduction.md` covers the method, the five passes with their risks, the findings, and the steps for repeating the loop.
- `docs/3d-printing.md` covers printer access, materials, parts with the test each one needs before flight, starting settings, costing, and safety.
- `docs/companion-tiers.md` records the tag-plus-phone decision, the tier costs, the rule that a device must earn its place, and the safety limits on the board.
- Updated the sensors, build-plan, budget and README docs to match. Corrected the README, which claimed uv and Docker Compose were in use.
- Corrected three claims while checking the numbers: the printing saving is net of the added guards, the transmitter is a placeholder rather than unpriced, and tier 2 exceeds the budget at the high end.

## Iteration 9: the owned pipeline (done: 137 tests pass)

- Results, from the model:
  - The bench kit with a made tag fits $100 at both ends: pass 5, $64.00 to $99.59. The saving over the retail tag is only $1.77 to $3.49.
  - The owned pipeline (pass 7) is 12 percent made in-house by cost. The flight hardware is the rest.
  - The Pixel 8a costs $210 to $215 more than the Pi and camera it would replace (pass 4).
  - DIY motors cost $7.01 to $26.42 each, excluding the unpriced steel core, against $10 to $13.50 for a retail motor (pass 6).
  - An outsourced 2-layer board is $0.40 to $0.70. An in-house 100 cm2 single-sided board is $1.82 to $15.48.
- Dependency check: the used autopilot, the 2-layer board and the patch-antenna board each have only one listed supplier. The ESC, props, charger, transmitter, tag battery and passives have none.
- Code: `bom/materials.json` holds raw inputs. Catalog items have a path (retail, bulk, used, service, make, owned, salvage). Made items are costed from materials. The report shows made-in-house share, already-owned cost, and the dependency check. `--passes-markdown` and `--markdown` generate the docs tables.
- Docs: [pipeline.md](pipeline.md), [pcb-plan.md](pcb-plan.md), [motors-plan.md](motors-plan.md), [lab-access.md](lab-access.md), and updates to the printing, cost, companion, budget and README docs.
- Found and fixed while checking: the made-share metric counted the Pixel as "made or owned", which made pass 4 look 32 percent self-made. It now counts only made and salvaged parts. A test had also forgotten the waste factor; fixed.
- Not done: no KiCad or OpenSCAD file, because neither is installed here. The PCB and enclosure plans are written instead.

## Iteration 9 plan (kept for the record)

- Owner input: 3D printers are available at FAU's engineering building and the IEEE club. The owner bought a used Pixel 8a for $250. The owner wants to own design, fabrication and assembly, and to avoid supplier markups. The earlier prices were retail and marketplace prices, so they overstate the raw parts.
- Research: raw and bulk prices for printing material, PCB blanks and etchant, magnet wire and magnets, a load cell, the chips for a tag and for a DIY ESC or flight controller, whether PX4 hardware designs are open, whether an open ESC firmware exists, the Pixel 8a's weight, and a desktop CNC PCB mill. Each price keeps its source.
- Code: a `bom/materials.json` of raw inputs. Catalog items can be made (`path: make`), and their cost is computed from those inputs. The report splits totals by path (retail, bulk, used, purchased, make, owned) and shows the share that is made or owned. New passes cover a made tag, a DIY motor research track and an owned-pipeline pass. Pass 4 uses the Pixel 8a at its purchase price, not $0.
- Docs: `docs/pipeline.md` (make-or-buy table, feasibility, savings and effort, and what cannot be owned), `docs/pcb-plan.md`, `docs/motors-plan.md`, `docs/lab-access.md` (what to ask FAU and IEEE for), and updates to the printing, cost, companion and budget docs.
- Constraint: OpenSCAD and KiCad are not installed in this environment. CAD and PCB files cannot be rendered or checked here, so any design file is marked unverified until it is opened and rendered at the lab.
- Stop point: none. Iteration 9 is complete.

## Iteration 10: tag board in KiCad and the enclosure in OpenSCAD (planned)

- The tag board plan is written in [pcb-plan.md](pcb-plan.md). The KiCad project and the OpenSCAD enclosure both need tools that are not installed here. Build them at home or at the lab, then mark each file as checked once it has been rendered or run through the design-rule check.

## Iteration 11: range-only sources, such as BLE RSSI (planned)

- A BLE or RSSI reading gives range but no bearing, so it cannot be a fused position vote. Plan: `range_only.py` with a log-distance path-loss model, used as a consistency check on the fused estimate, with tests.

## Next candidates (not started)

- Start the bench kit from pass 3: a Pi Zero 2 W with its camera cable, one tag, and a measurement of real tag range and battery life. Then log real data for the replay tool.

## Open questions for the owner

- What is the Pixel 8a for? The model assumes the drone's onboard computer and camera (pass 4). Confirm, because the rider's companion is your existing phone.
- Does the $100 budget include the Pixel? The model keeps it outside the budget. The $250 is already more than the budget.
- Which funding or equipment can FAU engineering or IEEE provide? See [lab-access.md](lab-access.md).
- Do you already own an ELRS-compatible transmitter? It is the largest placeholder in the drone passes ($60 to $120).
- What can FAU engineering and IEEE provide: a PCB mill or etching setup, soldering and hot-air stations, a bench power supply, a load cell, magnet wire, or funding? See [lab-access.md](lab-access.md).
- Repo license (still unset; see the README).
