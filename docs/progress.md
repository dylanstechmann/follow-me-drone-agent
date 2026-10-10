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

## Next candidates (not started)

- Start the bench kit from pass 3: a Pi Zero 2 W with its camera cable, one tag, and a measurement of real tag range and battery life. Then log real data for the replay tool.
- Price the open lines: a PX4-compatible autopilot, a transmitter, the 4-in-1 ESC, propellers and a charger.
- A BLE range source model (RSSI to distance with a log-distance fit, plus its variance).

## Open questions for the owner

- Do you have access to a 3D printer (your own, a makerspace, or a print service)? This changes the printing costs.
- Do you already own an ELRS-compatible transmitter? That line is the largest unpriced item in the drone builds.
- Repo license (still unset; see the README).
