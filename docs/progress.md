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

## Iteration 10: price audit and the make-own ladder (done: 146 tests pass)

- Results:
  - Only 9 of 39 sourced prices are dated within 12 months. Sixteen inputs are placeholders. The earlier "searched 2026-10-10" label on the catalog was wrong, and is removed.
  - Re-checked and dated: ESP32-C3-MINI-1 (LCSC page fetched 2026-10-10, $2.01 to $3.06), the ICM-42688-P (reseller guide dated 2026-08-23, $6.50; DigiKey and Mouser lead times of 45 to 53 weeks), the TP4056 module (August 2026 listings), electrical steel (Q2 2026 benchmark, $1.44 to $2.09 per kg), skate bearings (February 2026), magnet wire (March 2026 listing), and the RTL-SDR V4.
  - Pass 8 (own most) is $267 to $594 core, 45 percent made in-house, still over budget. Its largest items are the DIY motors at retail magnet prices, the Holybro GPS, the ESC, and placeholders for the charger and LiPo bag.
  - Pass 9 (by-weight magnets and salvage) is $253 to $524.
- Code: each price has a `checked` date. Freshness needs month precision and a date within 12 months. `--audit` lists every input and its freshness. Made items now take a `checked` date from their materials. Pass 8 replaces the bought autopilot, ESC, transmitter and tag battery with four made designs. Pass 9 is the motor what-if.
- Docs: [make-own-ladder.md](make-own-ladder.md) (each part on the list: buy, own, salvage, verdict), [price-audit.md](price-audit.md), and the updated cost, budget, pipeline and README docs.
- Not done: no KiCad or OpenSCAD files (tools not installed). The MOSFET and gate-driver bulk prices, the magnet quote by weight, the laser cutter, and the clone GNSS field test are the next research items.
- Licence claims for PX4, ArduPilot, ELRS, EdgeTX, AM32 and GNSS-SDR come from forum and index summaries. Read each LICENSE file before reuse.

- Correction: the catalog said "searched 2026-10-10", which made old listings look current. Many sources were years old (a DigiKey page flagged about 2,349 days old, a Sunlu page about 5 years, a review about 9.5 years). Each price will now carry its own checked date, or "undated". The report flags any price not seen in the last 12 months before 2026-10-10.
- Re-search, with 2026 cues, the prices that decide the plan: MCU and radio chips (ESP32, SX1262 or similar), IMU and barometer, MOSFETs and gate drivers, 18650 and 21700 cells, electrical steel for laminations, N52 magnets, magnet wire, PLA and PETG, SDR hardware for GNSS and LoRa, PCB fabrication, and the cheapest GNSS chip. Record each source's date where the page shows one.
- Make-own ladder for each named item: chips, lithium cells, autopilot, GNSS, ESC, transmitter, motors, steel core, ESP32 and LoRa. For each: buy in bulk, salvage, or make. Record the cost, effort, safety and what cannot be made at home.
- Model: items for the owned routes (DIY ESC, DIY ELRS-style transmitter, own autopilot board, cells from bulk or salvage, GNSS software receiver, laminated steel cores). New pass for "own most" with the made share.
- Docs: `docs/make-own-ladder.md`, `docs/price-audit.md` (generated), and updates to pipeline and cost docs.
- Note: the Pixel 8a was an example of a cheap used phone. It is a parts source too (GNSS, IMU, camera, Wi-Fi and cells), not a decided drone computer.

## Iteration 11: closer to the supply side (done: 151 tests pass)

- Results, from the model:
  - Pass 10 (factory-assembled own boards, factory magnets and bearings, lab-etched stators, BLE tag): $207.86 to $534.21 per drone, $67 to $89 below pass 8. Cash at minimum orders is $332.20 to $934.98. 20 percent made in-house, 51 percent the owner's design.
  - Pass 11 (factory stator cores): about the same per drone, but $1,319.96 to $2,918.89 of cash at the 1,000-piece minimum.
  - Largest single saving: the own GNSS board, factory-assembled with a bare M9N, at $15.54 to $28.59 against $54.99 to $74.90 retail.
  - Motors beat retail only with factory parts: $2.57 to $12.40 each, against $11.91 to $35.17 with retail parts and $10 to $13.50 for a T-Motor.
  - No gain upstream for complete motors, props, cells (shipping rules) or filament from pellets (extruder payback of 55 to 150 kg).
- Corrections: the motor model used 608 skateboard bearings, which are too large for a 2207 motor. It now uses 4 x 9 x 4 mm miniature bearings. "Laser-cut stator" now notes that most makerspace CO2 lasers cannot cut steel.
- Code: a `moq` (minimum order) on items and materials, `moq_per_item` for boards and assembly fees, the `buy_factory` path, composed service and factory items, the cash-at-minimum-orders figure, and an owner-designed share.
- Docs: [supply-side.md](supply-side.md), plus updates to the make-own ladder, cost, motor and lab docs.
- Data quality: 10 of 51 sourced prices are dated within 12 months, and 16 inputs are placeholders. The ESC MOSFET bulk price is the largest open placeholder.
- The licence and import-duty claims come from summaries and trade guides. Verify them with the LICENSE files and with CBP.

## Iteration 11 plan (kept for the record)

- Owner input: make it cheaper, own more, and get closer to the factory, fab and lab.
- Goal: move each part one step up its supply chain, from retail to distributor to factory or fab to in-house lab, and show what each step costs in cash and minimum orders.
- Research (with 2026 cues and dates): factory and OEM prices with minimum orders for motors, stators, magnets, props, cells and packs. Bare chips instead of modules (an ESP32-C3 with in-package flash, a low-cost BLE SoC, GNSS chips). The ESC power parts commonly used in factory ESCs (MOSFETs, three-phase gate drivers). PCB assembly fees at a factory that stocks the parts. Raw plastic pellets and filament extrusion. Import duties and the end of US de minimis for small parcels. Lithium shipping rules. FAU lab facilities.
- Model: a minimum order quantity (`moq`) on items and materials, and a `buy_factory` path. The report shows both the per-unit cost and the cash outlay at the minimum order, so cheaper per unit is never confused with cheaper to start.
- New pass: factory-direct parts and factory-assembled boards.
- Docs: `docs/supply-side.md`: who makes each part, how close the project can get, minimum orders, duties and shipping, group buys through the IEEE club, and the lab steps.

## Iteration 12: IEEE group order plan, kept in sync (done: 184 tests pass)

- Results:
  - The plan has 14 lines in three waves. Wave 1, the factory parts that are ready now, totals $159.20 to $540.44. At 10 members that is $15.92 to $54.04 each. Wave 2 (assembled boards, blocked by designs) totals $576.90 to $1,843.10. Wave 3 (deferred) totals $991.44 to $1,992.09.
  - Nothing has been ordered, no supplier has been contacted, and there are no quotes (0 of 14 lines). The club's ability to run group orders is owner-reported and unconfirmed.
  - Nine open decisions are listed, led by the coordinator role, payment and custody, the importer and address, quote requests, and the duty quote.
- How it stays current: the plan is data (`bom/group_order.json`). The doc is generated from it. `follow_me.docs_sync` rewrites every generated table in the docs, and the test suite fails if one is stale. AGENTS.md tells every future session to update the line states, quotes and `last_updated` as the order moves, and to run the sync.
- Privacy: the plan uses roles only. A test scans the plan files for emails and phone numbers.
- Moved to the same mechanism: the parts catalog, the price audit and the pass table in the cost doc, which had been hand-copied.
- Code: `follow_me.group_order` (loading, validation, totals, per-member shares, drones covered) and `follow_me.docs_sync`.

## Iteration 12 plan (kept for the record)

- Owner input: the IEEE club can do group orders. Put the details on GitHub and keep them updated.
- Data: `bom/group_order.json` holds the plan: waves of order lines, quantities, minimum orders, states (blocked, needs quote, quoted, ordered, received, inspected), supplier quotes when they arrive, open decisions, and facts with their provenance. Prices come from the cost model until a quote replaces them, so a change to a material price moves the plan.
- Code: `follow_me.group_order` loads and validates the plan and computes totals, per-member shares for 5, 10 and 20 members, and how many drones each line covers. `follow_me.docs_sync` rewrites generated blocks in the docs from the data, and `--check` fails when a block is stale.
- Docs: `docs/group-order.md` (a human part plus a generated block), with the generated tables in the parts catalog, price audit and cost docs moved to the same mechanism.
- Keep-updated rules: the test suite fails if a generated block is stale. AGENTS.md tells every future session to run the sync after changing the data and to update line states, quotes and `last_updated` as the order moves.
- Privacy: this repo is public. The plan uses roles only. No names, contact details, addresses, payment records or order screenshots. A test scans for email-like text.
- Not claimed: the club's ability to run group orders is owner-reported, not confirmed with the club's officers. No supplier has been contacted and no quote exists.

## Iteration 13: agent-readable project record and the owner's vision (done: 190 tests pass)

- Results:
  - Wrote [project-context.md](project-context.md) (the briefing for any agent), [vision.md](vision.md) (the owner's stance and ambition), [decisions.md](decisions.md) (16 decisions, 12 corrections, lessons) and [history.md](history.md) (what happened, in order, with who did what).
  - Rewrote the README with a start-here list, the direction and the money stance. AGENTS.md now has a reading order and the owner's preferences as hard rules.
  - Funding mentions in the budget and lab-access docs are now optional and marked as not part of the plan. Group orders are described as cost-sharing, not fundraising.
  - Found and fixed C12: three docs said the code was "reviewed by the owner", and no review is recorded.
  - Added tests that the briefing lists every doc, that the entry points exist, that the money stance is where agents will read it, and that no doc claims owner review.
- Not claimed: no fleet size, revenue plan or product plan. The owner said "tons" of drones and "money" as an expected benefit; both are recorded as the owner's words, with open questions in [vision.md](vision.md).

## Iteration 13 plan (kept for the record)

- Owner input (2026-10-24): save everything discussed in documents in the repo, so other AI agents can understand the project. Also record the owner's stance and ambition: the owner does not like asking for money, and is curious about building many drones, and the software that may power them, by getting each part oneself rather than from off-the-shelf components. The owner expects that process to bring more control, power, money, understanding and capabilities.
- Docs to write: `docs/project-context.md` (a briefing for any agent: what this is, what exists, how it fits together, rules, caveats, how to continue, glossary, doc map), `docs/vision.md` (the owner's stance and ambition, what each claimed benefit means in practice, what the evidence supports, the fleet question, risks and legal checks), `docs/decisions.md` (decision log and corrections log), `docs/history.md` (what was discussed and done, in order).
- Updates for consistency: AGENTS.md gets a "start here" list and the owner's preferences. Funding mentions in the README, budget and lab-access docs become optional and are marked as not part of the plan. Group orders are described as cost-sharing, not fundraising.
- Tests: a check that the doc map lists every file in docs/, so the briefing cannot silently fall behind.
- Honesty rules for the new docs: report the owner's statements as the owner's. Mark what the model supports and what it does not. Do not turn an aspiration into a plan, and do not add a business case or a number of drones the owner has not given.

## Iteration 14: KiCad board and OpenSCAD enclosure (planned, needs tools)

- The tag board plan is written in [pcb-plan.md](pcb-plan.md). The KiCad project and the OpenSCAD enclosure both need tools that are not installed here.

## Iteration 15: range-only sources, such as BLE RSSI (planned)

- A BLE or RSSI reading gives range but no bearing, so it cannot be a fused position vote. Plan: `range_only.py` with a log-distance path-loss model, used as a consistency check on the fused estimate, with tests.

## Next candidates (not started)

- Start the bench kit from pass 3: a Pi Zero 2 W with its camera cable, one tag, and a measurement of real tag range and battery life. Then log real data for the replay tool.

## Open questions for the owner

- What is the Pixel 8a for? The model assumes the drone's onboard computer and camera (pass 4). Confirm, because the rider's companion is your existing phone.
- Does the $100 budget include the Pixel? The model keeps it outside the budget. The $250 is already more than the budget.
- Do you already own an ELRS-compatible transmitter? It is the largest placeholder in the drone passes ($60 to $120).
- What tools can FAU engineering and IEEE lend or book: a PCB mill or etching setup, soldering and hot-air stations, a bench power supply, a load cell, a laser cutter? See [lab-access.md](lab-access.md). (Money is not on this list: the owner does not like asking for it.)
- How many is "tons" of drones, what would count as success, and how should the first flying drone be paid for without asking for money? See [vision.md](vision.md).
- Repo license (still unset; see the README).
