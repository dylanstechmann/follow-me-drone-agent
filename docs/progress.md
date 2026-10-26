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

## Iteration 14: KiCad board and OpenSCAD enclosure (enclosure done in iteration 19; the board still needs KiCad)

- The tag board plan is written in [pcb-plan.md](pcb-plan.md). The KiCad project needs a tool that is not installed here. The enclosure was done in iteration 19 with OpenSCAD's WebAssembly build.

## Iteration 15: range-only sources, such as BLE RSSI (planned)

- A BLE or RSSI reading gives range but no bearing, so it cannot be a fused position vote. Plan: `range_only.py` with a log-distance path-loss model, used as a consistency check on the fused estimate, with tests.

## Iterations 16 to 19 plan (2026-10-26)

- Owner input (2026-10-26): the owner asked what could be added: visualizations and easy dashboards, 3D, databases, AI models, and a website on GitHub Pages where the 3D runs in the visitor's browser, with heavy work on the owner's laptop or a cloud sandbox if needed. The owner said "ok" to the first batch proposed: the site with a status page, a replay viewer and a cost explorer; printable parts shown in 3D and ready for FAU's printers; and recording the new facts. New facts from the owner: the printers are in FAU's engineering building, and the owner can work with a drone club.
- Iteration 16, facts and the replay example:
  - Record the rules found by an agent web search, to verify with FAU and the FAA: FAU's environmental health and safety drone page (undated) says recreational drone use on university property is strictly prohibited, and other flights need approval through FAU Risk Management. The Boca Raton campus borders Boca Raton Airport, which has Class D airspace with LAANC available to recreational flyers. Recreational flyers also need the free TRUST test, FAA registration for drones over 250 g, and Remote ID.
  - Record the drone club as owner-reported. The same search found no university-level FAU drone club, only the K-12 club at FAU's lab schools.
  - Fix: this log says the replay example exercises hold, return-home and the full fallback ladder. At default settings the replay tool shows only tracking and dead reckoning: the example has 4 empty ticks against a 10-tick dead-reckoning window. Only the tests, with shortened thresholds, reach hold and return-home, and degraded never appears. Extend the example so it reaches every mode at default settings, test that it does, and record the correction.
- Iteration 17, the cost model:
  - Fix: cash at minimum orders leaves out the waste allowance on the high end, while the per-drone cost includes it. Passes 6 to 11 understate the high end by $24 to $57.
  - Add cash and cost per drone for any number of drones, honouring minimum orders. Fees paid once per order (the PCB assembly setup fee, the extended-part loading fee, and the import-duty allowance per consolidated entry) get a `per_order` flag and do not grow with the count. This is for exploring only: the owner has not set a number of drones.
- Iteration 18, the website:
  - A static site on GitHub Pages, built from the repo's data by `python -m follow_me.site` (standard library only) and deployed by a GitHub Actions workflow on each push to main. No backend, analytics or cookies, and nothing a visitor opens is uploaded.
  - Pages: an overview with the gates, what is built and what is not, the AI disclosure and credits; a replay viewer for the example log and for trace files a visitor opens locally; and a cost explorer with the passes, the drone-count view, price freshness and single-supplier parts.
  - Code: a JSON trace from the replay tool, and a fusion report (the gate centre and which readings were kept, rejected or switched off), exposed through the council without changing its results.
  - Tests: the site builds, its data matches the model and the replay, every local link resolves, there is no email-like or phone-like text, and the honesty statements are present.
- Iteration 19, printable parts:
  - The enclosure half of iteration 14, now possible with OpenSCAD's WebAssembly build: parametric test coupons, a thrust-stand jig and the tag enclosure, each with a print card.
  - A parts page: each part in 3D in the browser (three.js), sliders that re-render it with OpenSCAD in the browser, and STL downloads for the printers.
  - Every part stays unprinted and untested until it is printed and measured. Measured grams and times replace the catalog estimates when the owner reports them.
- Stop point: ask the owner before pushing and before turning on GitHub Pages, because both publish.

## Iteration 16: owner facts and the replay example (done: 191 tests pass)

- Recorded, as rules to confirm with FAU and the FAA: FAU's safety page prohibits recreational drone use on university property, and the Boca Raton campus borders Boca Raton Airport's Class D airspace. Added TRUST, LAANC and the FAU rule to [privacy-and-rules.md](privacy-and-rules.md), [lab-access.md](lab-access.md) and the safety plan. Public text names "FAU's engineering building", not a more exact place, following the location rule.
- Recorded the drone club as owner-reported, with the questions worth asking it, none of them money.
- Fixed C13: the example log now walks tracking (5 ticks), degraded (2), dead reckoning (10), hold (90), return-home requested (4) and tracking again (2) at default settings. A test checks the whole sequence, and a second test keeps the shortened-threshold case.
- Found while doing it: the mode thresholds count ticks, not seconds. At this log's 2 ticks per second, return-home is requested after 50 s without an estimate; at 30 ticks per second it would be under 4 s. Listed under the next candidates.

## Iteration 17: the cost model (done: 198 tests pass)

- Fixed C14: the cash at minimum orders now includes the waste allowance at the high end. Pass 10 is $332.20 to $960.45 (was $934.98 at the high end), pass 11 is $1,319.96 to $2,943.16 (was $2,918.89), and passes 6 to 9 rise by $29 to $57 at the high end. Per-drone costs did not change.
- Added the cost per drone for any number of drones: `cash_outlay(..., drones=N)` and `per_drone_cost()`, with a generated table in [cost-reduction.md](cost-reduction.md) (`python -m follow_me.bom --drones-markdown`). The PCB assembly setup and extended-part loading fees are marked `per_order` and paid once per order.
- Changed from the plan: the import-duty allowance is not marked `per_order`. Duty grows with an order's value, so keeping it per drone is the cautious choice; only an entry fee would be paid once.
- Results, at the 2026-10-10 prices, per drone, low to high: pass 10 goes from $332 to $960 for one drone to $197 to $519 at 100 drones, below its core cost because the setup fees spread out. Pass 11's 1,000 stator cores make one drone cost $1,320 to $2,943, and wash out to $200 to $523 at 500. The bench kit (pass 5) costs $72 to $116 for one, because minimum orders round up, against its $63.87 to $98.99 core cost.
- Not claimed: no number of drones, no volume discounts, and no labour, tooling, failures, storage or shipping.

## Iteration 18: the website (done: 212 tests pass)

- Built a static site in `site/`: an overview, a replay viewer and a cost explorer, in plain HTML, CSS and JavaScript with no libraries. `follow_me.website` writes the data from the cost model and the replay tool and copies the README's status into the overview, using only the standard library. See [website.md](website.md).
- Named the builder `follow_me.website`, not the planned `follow_me.site`, so it cannot be confused with Python's own `site` module.
- Fusion now returns a report (the gate centre, and each reading kept, rejected or off) through the council without changing any result; the existing tests pass unchanged. `python -m follow_me.replay --json` writes a trace.
- A GitHub Actions workflow runs the tests on every push and pull request, and on main builds and publishes the site. GitHub Pages is not turned on yet. It is a repo setting that publishes the site, so it waits for the owner.
- Checked in a headless browser (Chromium through Playwright, in the agent's scratch space) at 1280, 1024, 900 and 390 px wide, in light and dark themes: no script errors and no sideways scrolling. Fixed what the screenshots showed: a cramped plot, colliding labels, a mode strip where dead reckoning and hold looked like one bar, and a drop-down wider than a phone.
- Tests: the site builds; its data matches the cost model and the replay; every local link and import resolves; every page carries the hobby framing, the AI disclosure and the no-review statement; there is no email-like or phone-like text and no place data.
- Not done: a playground that runs raw logs in the browser (Pyodide), a group-order page, and a 3D view of the replay.

## Iteration 19: printable parts (done: 229 tests pass)

- Wrote four parts as adjustable OpenSCAD models in `cad/`, each with a print card in `cad/parts.json`: test bars for a break test, a hole-size gauge for M2 to M4 screws, a thrust-stand jig for a bar load cell and one motor, and the tag case. All are unprinted and untested, and each card names the test to do before relying on the part.
- Unblocked the enclosure half of iteration 14 without installing anything: OpenSCAD's WebAssembly build (openscad-wasm-prebuilt 1.2.0, OpenSCAD 2025.01.19) runs under Node.js here and in browsers. Its Manifold engine renders each part in about 0.15 s, against 10 to 17 s with the older engine, which makes live sliders practical.
- Added a parts page: each part in 3D (three.js), sliders that re-render it in a web worker in the visitor's browser, its print card, the solid-volume mass, and STL and OpenSCAD downloads. The build fetches three.js and OpenSCAD from the npm registry, pinned and hash-checked, so no library code is kept in git; `tools/render_parts.mjs` renders the default STLs. Checked in a headless browser: the prebuilt STLs load, a slider change re-renders in 0.2 to 0.3 s, and the size follows the values (a 60 mm board gives a 65.6 mm case).
- `follow_me.parts` reads each file's Customizer values and checks that every default sits on its slider's steps. A printed part must record its measured grams, minutes, material and date.
- Finding to check: the catalog costs the tag case at 25 g of PLA and the thrust stand at 80 g. These designs come to at most about 14 g and 55 g of PLA even printed solid, so the estimates look high. The catalog keeps them until a slicer or a scale gives real numbers.
- Not done: the KiCad tag board (iteration 14's other half, still needs KiCad), a camera mount for the bench kit, and any print. The workflow's build step runs Node.js on GitHub's runner, which has not run yet.

## Iteration 20 plan: publish the site (2026-10-26)

- Owner input (2026-10-26): the owner asked what to do next and said "ok" to the agent's recommendation: publish now with an MIT licence; the owner prints the hole-size gauge and the test bars at FAU's engineering building; then a batch that runs the owner's own phone recording through the council; then a camera batch. The GPU question is deferred, because nothing planned needs training.
- Update the workflow's GitHub actions from v4, written from memory in iteration 18, to the current versions: checkout v7, setup-node v7, upload-pages-artifact v5 and deploy-pages v5. The v4 versions run on Node 20, which GitHub is retiring; the new ones run on Node 24. Build with Node 24, the version the parts renderer was tested with.
- Add the MIT licence, with the same copyright line as the owner's other repos, and record it as a decision.
- Turn on GitHub Pages with source "GitHub Actions", push iterations 16 to 20, and watch the first workflow run. Fix whatever it fails on, check the live site in a headless browser, and put the site link in the repo's About box.

## Iteration 20: publishing the site (done: 229 tests pass)

- Turned on GitHub Pages with source "GitHub Actions" and pushed iterations 16 to 20 (`f95e757`). The first workflow run passed in about a minute: 229 tests on GitHub's Ubuntu 24.04 runner, the four parts rendered with Node 24 in 157 to 190 ms each, and the deploy published https://dylanstechmann.github.io/follow-me-drone-agent/.
- Checked the live site in a headless browser (Chromium through Playwright, in the agent's scratch space). All four pages, at 1280 px in the light theme and 390 px in the dark theme, load with no script errors, no failed requests and no sideways scrolling. The parts page draws the prebuilt STL in 3D, and a slider change re-rendered the thrust stand in the browser in 0.3 s. Every built file returns 200 except `.nojekyll`, which the upload action skips as a hidden file; Pages does not run Jekyll on Actions deploys, so it is not needed.
- Added the MIT licence (D19), which GitHub now detects, and set the repo's homepage link to the site.
- The deploy step prints a Node.js deprecation warning (`punycode`) from inside GitHub's deploy action, not from this repo's code.
- Not done: nothing has been printed or measured. The phone-data batch does not depend on the prints, so it can start before them.

## Iterations 21 to 24 plan: the owner's own recording through the council (2026-10-26)

- Owner input (2026-10-26): the owner asked whether anything else could be done before going to the printers. The agent listed what to bring and record, and started this batch, which does not depend on the prints.
- Iteration 21, a kinematic follow simulation (`sim.py`):
  - A point drone in a flat local frame that turns and moves along its nose as the council commands, within placeholder limits (10 m/s, 90 degrees per second), following a rider who moves.
  - It closes the loop, so the follow logic can be tested against a moving rider and a recorded track can be replayed. It is not a flight simulator: there is no physics, wind, autopilot or camera, and it does not stand in for the SITL gate.
  - Phone fixes become readings through the same body-frame math as `companion.py`.
  - Tests: a standing rider is approached and held in the follow band; a rider to one side is turned toward; a rider moving at a steady speed is trailed at the distance the controller's gain predicts; the same input gives the same output.
- Iteration 22, mode thresholds in seconds:
  - The mode machine counts seconds since the last estimate, so its timing no longer depends on the loop rate: dead reckoning up to 5 s, then hold, then a return-home request after 50 s, the same as today's 10 and 100 ticks at 2 ticks per second.
  - The example log keeps its runs.
  - The change is checked in the simulation at two loop rates, as the safety rule asks for any change to this logic.
- Iteration 23, importing a recording (`recording.py`):
  - Read a GPX track from a GPS-logging app. Turn each fix into an offset in metres from the first fix and a time in seconds from the first fix, and drop the coordinates and clock times at once.
  - A CLI runs the track through the simulation and prints a summary or a trace for the replay viewer. It writes no files.
  - `*.gpx` is ignored by git, so a recording dropped into the repo cannot be committed by accident. Tests use made-up tracks generated in the tests.
- Iteration 24, in the browser:
  - The replay page opens a GPX file and runs the same Python in the visitor's browser with Pyodide, in a web worker. Nothing is uploaded.
  - A made-up example ride, computed at build time, shows a follow-distance chart with the follow band, and a top-down view of both paths relative to the start, with no map.
- Stop point: ask the owner before pushing.

## Iteration 21: a kinematic follow simulation (done: 249 tests pass)

- Added `sim.py`: a point drone that turns and moves as the council commands, after a rider given as timed fixes, with placeholder limits of 10 m/s and 90 degrees per second. Fixes become `phone_gnss` readings through `companion.offset_estimate`, split out of `companion_estimate` so both use one rotation. The council now passes on the mode machine's dead-reckoning hold, and the simulation honours it. `trace_track` writes a trace in the replay viewer's format, with the drone's world added. See [simulation.md](simulation.md) and decision D20.
- Findings, from the model with placeholder limits:
  - The drone trails a moving rider, because the controller has no feed-forward of the rider's speed: 7.6 m behind at 2 m/s, 10.1 m at 3 m/s, 15.2 m at 4 m/s, about 30 m at 5 m/s.
  - The forward command tops out at 0.6, so the drone never passes 6 m/s.
  - A phone alone, at 4 m accuracy, is degraded on every tick (16 m² against the 9 m² threshold). That halves the gain, so the drone tops out at 3 m/s.
  - Past about 54 m, the heading term makes even a 1 m fix degraded.
- Not changed: the controller and the threshold. Each is a change to the follow logic, so it is listed in [simulation.md](simulation.md) as a candidate needing its own simulation tests.

## Iteration 22: mode thresholds in seconds (done: 257 tests pass)

- The mode machine now times a loss in seconds since the last estimate, from each tick's timestamp: dead reckoning up to 5 s, hold up to 50 s, then a return-home request. `ModeMachine(dead_reckon_s, return_home_s)` replaces the tick counts, and `Council.tick` and `ModeMachine.step` take the tick's time. Times that go backwards are refused.
- At the example log's 2 ticks per second the windows match the old 10 and 100 ticks, so the example walks the same runs, and its test passes unchanged. The mode tests check the windows at 0.1, 0.5 and 2.5 s per tick, and a simulation test checks that a 10 Hz and a 2 Hz loop reach hold and return-home at the same time, within one tick. This is the simulation test the safety rule asks for, for a change to this logic.
- One difference from counting ticks: a loss with no estimate before it is timed from its first tick, so a log that starts with no readings gets one extra dead-reckoning tick.
- The replay page now says that modes are timed in seconds, and the trace settings carry `dead_reckon_s` and `return_home_s`.

## Iteration 23: importing a recording (done: 278 tests pass)

- Added `recording.py`. It reads the track points of a GPX file (1.0 or 1.1), sorts them by time, skips points with no usable time or position, and keeps only seconds and meters from the first fix and each fix's accuracy. The coordinates, dates and names are dropped as each point is read. It refuses files with a document type (no entity tricks), files over 50 MB, tracks spanning over 200 km, and, for simulation, recordings over 2 hours.
- Found while checking the apps' code: GPX has no standard accuracy field, and `hdop` means different things. GPSLogger writes the unitless dilution of precision from NMEA, sometimes missing; OsmAnd writes the phone's accuracy in meters. The importer reads an accuracy extension first, then `hdop` as meters for OsmAnd files or HDOP times 4 m for others (a guess), then a 5 m default (a guess), and reports how many fixes used each. Recorded as a lesson in [decisions.md](decisions.md), with the sources in [references.md](references.md).
- `python -m follow_me.recording FILE.gpx` prints a summary of the simulated follow, and `--json` prints a trace for the replay viewer. It writes no files. `.gitignore` now excludes `*.gpx` and `*.trace.json`, and [privacy-and-rules.md](privacy-and-rules.md) says recordings and their traces stay off the repo.
- Tried on a made-up 4 m/s ride with turns, a stop and a 15 s gap, at HDOP 1.2 (about 5 m): degraded for 176 s, dead reckoning for 5 s and hold for 8.5 s, with the drone a median 54 m behind. That matches the iteration 21 findings.
- Tests use made-up tracks near 0 degrees north, 0 degrees east, written inside the tests. No recording is committed.

## Iteration 24: recordings in the browser (done: 281 tests pass)

- The replay page opens a GPX recording, by button or by dropping the file. A module worker (`site/assets/replay-worker.js`) loads Pyodide 314.0.7 (Python 3.14) from the site itself, writes the twelve modules the simulation needs into it, and calls `follow_me.recording.run_gpx`, the same code the command line runs. The page draws the trace. Nothing is uploaded, and no logic is rewritten in JavaScript (decision D21).
- `follow_me.website`:
  - adds Pyodide to the pinned, hash-checked downloads;
  - copies the modules under `py/follow_me/`, with a manifest;
  - writes `data/sim-example.json`, a made-up 145 s ride run through the simulation. It passes through tracking, degraded, dead reckoning and hold;
  - adds `python` to `data/build.json`, so a build without Pyodide points to the command line instead.

  The tests check:
  - that the example is the simulation's output;
  - that the browser's modules are byte-identical to `src/`;
  - that those modules import nothing outside the set.
- For a simulated trace, the page adds:
  - four tiles: the median distance, the share of time in the follow band, the share below full tracking, and whether return-home was requested;
  - a distance-over-time chart with the band shaded, a moving marker, hover and click to jump;
  - a top-down view of both paths from the start, with no map;
  - a distance column in the table view.
- Checked in a headless browser (Chromium through Playwright, in the agent's scratch space) against a local build with the libraries:
  - Both examples load at 1280 px in the light theme and 390 px in the dark theme, with no script errors, failed requests or sideways scrolling.
  - A made-up GPX opened in 2.7 s, including loading Python, and matched the command line's result.
  - A second file reused the loaded Python. A bad file showed "not a GPX file".
  - Under Node.js, Pyodide gave the same trace as CPython, in 480 ms for 379 ticks.
- Fixed what the screenshots showed:
  - The "time below full tracking" tile compared the summed mode times (one tick longer) with the track's duration, giving "189.5 s of 189.0 s". It now shows a share.
  - The band label collided with the line.
  - The scale bar sat on the start label.
  - In a deep frame, the existing "camera view" label of the drone plot was clipped at the left edge.
- To check after publishing: that GitHub Pages serves Pyodide's `.mjs` files with a JavaScript type, which module workers need.

## Iteration 25: published, checked live, and iPhone apps (done: 281 tests pass)

- Owner input (2026-10-26): the owner said yes to pushing iterations 21 to 24, and that they have both an Android phone and an iPhone.
- Pushed `e404662`, and the workflow run passed and deployed.
- Checked on the live site:
  - GitHub Pages serves `.mjs` as `text/javascript` and `.wasm` as `application/wasm`, both compressed.
  - In a headless browser, the made-up recording opened in 4.2 s, including downloading Pyodide from the site, and gave the same result as the local build. A bad file was refused with a readable message.
  - Both examples render at 1280 px in the light theme and 390 px in the dark theme, with no errors or sideways scrolling.
- Corrected the page: Pyodide is about 6.4 MB to download, compressed, not the 13 MB it said, which is its unpacked size.
- Read the iPhone apps' GPX writers:
  - OsmAnd for iPhone stores the phone's accuracy in meters in `hdop`, like the Android app, and writes "OsmAnd Maps" as the file's creator, so the importer's OsmAnd rule holds on both.
  - Open GPX Tracker stores no accuracy, so its files get the 5 m guess.
  - [simulation.md](simulation.md) now has a table of the three apps.
- Next candidate, from having two phones: record the same walk on both at once, and run one as `phone_gnss` and the other as a stand-in for `tag_gnss`. Two receivers with independent errors would test the gate on real disagreement, which `companion.py` was designed for. Not started.

## Iterations 26 to 28 plan: make the simulated drone keep up (2026-10-26)

- Owner input (2026-10-26): the owner asked what else could be done before work away from the computer. The agent recommended fixing the follow logic the simulation exposed in iteration 21, then the camera batch, then two-phone support, and started the first. Everything stays local until the owner says to push.
- Iteration 26, the rider's motion (`motion.py`):
  - A constant-velocity Kalman filter estimates the rider's position and velocity in a local frame. It uses the drone's own pose, which a real autopilot reports and the simulation knows.
  - `Council.tick` takes the pose as an optional input. Without it, as in every existing log, nothing changes.
  - The trace carries the rider's estimated speed.
- Iteration 27, feed-forward:
  - The controller adds the rider's estimated speed along the drone's nose, as a share of the full-scale speed, to the forward command. The share shrinks toward zero when the speed estimate is uncertain.
  - The mode's gain still scales the whole command, so degraded still means half authority.
  - Simulation tests, as the safety rule asks for a change to control code:
    - a rider at 2 to 5 m/s is followed near the follow band instead of 7.6 to 30 m behind;
    - a rider who stops suddenly is never approached closer than a set distance;
    - a turning rider is followed without large overshoot;
    - noisy fixes from a standing rider do not make the drone wander;
    - with no pose, the commands are unchanged.
- Iteration 28, the website and docs:
  - The simulated follow example uses the new logic, with the old logic kept beside it for comparison.
  - [simulation.md](simulation.md) gets before and after numbers.
- Not in scope: the degraded threshold. A phone alone is still degraded at half authority, and that needs real data.
- Stop point: ask the owner before pushing.

## Iteration 26: the rider's motion (done: 293 tests pass)

- Added `motion.py`. It places each fused estimate in a local frame using the drone's pose, and filters east and north with a constant-velocity Kalman filter. The filter uses a 1.5 m/s² acceleration sigma, a guess. It reports the rider's velocity over the ground in the drone's frame, with its uncertainty, or nothing before the first estimate and after 5 s without one.
- `Council.tick` takes an optional `pose`. The simulation passes its drone's pose. Logs have no pose, so the replay tool, its example and its tests are unchanged. Traces carry `motion` only when there is one.
- Found while testing: the simulation ticks every 0.5 s and a phone fixes once a second, so every other tick repeats the last fix. A filter that took each tick's estimate as new would see the rider stop every other tick. Readings now carry `age_s`, the measurement's age; fusion reports the kept readings' weighted age; and the filter uses each measurement once, at the time it was taken. Logs may give `age_s`; it defaults to 0.
- Tests:
  - frame rotations;
  - convergence to the rider's speed;
  - the drone's own motion taken out, both when it flies alongside the rider and when it spins on the spot;
  - a repeated measurement adding nothing, and a steady speed from a 1 Hz fix on a 2 Hz loop;
  - restarting after a gap;
  - fusion's weighted age.
- The controller does not use the motion yet. Iteration 27 does.

## Iteration 27: feed-forward (done: 309 tests pass)

- The controller adds the rider's estimated speed along the drone's nose to its forward command, as a share of a 10 m/s full-scale speed. The council computes the share from the motion estimate, shrunk by its uncertainty, and the mode's gain still scales the whole command (decision D22). `Council(feed_forward=False)` gives the old controller, for comparison.
- Results from the simulation, with 1 Hz fixes:
  - A rider at 2 to 7 m/s is followed 6.2 to 10.0 m behind, against 8.0 to 31.6 m and losing a 7 m/s rider before.
  - A 90 degree turn stays within 5.1 to 7.6 m.
  - The example ride's median distance falls from 20.4 m to 7.0 m.
  - The full table is in [simulation.md](simulation.md).
- Found and fixed while testing: a rider who stops suddenly from 4 m/s was approached to about 2 m, because the speed estimate takes a moment to fall. The approaching part of the feed-forward now fades out across the follow band, and the closest approach is 3.4 m. Backing away from a rider who comes toward the drone is never faded.
- Found, not fixed, and present before this change too: with made-up 3 m errors on a standing rider's fixes, the drone came within 0.3 to 1.8 m of the true rider in five runs. A 4 to 5 m follow band needs better than metre-level positions. Candidates are listed in [simulation.md](simulation.md). Each needs simulation tests first.
- The simulation can add seeded noise to fixes while keeping the track as the truth, and its summary reports the closest approach.
- Tests:
  - feed-forward keeps 2 to 5 m/s riders within 8.5 m, and closer than the old controller ever got;
  - a 7 m/s rider is kept within 12 m;
  - a sudden stop is never closer than 3 m and settles in the band;
  - a turn stays within 3.5 to 9 m;
  - noisy fixes make the drone move at most 25% more than before;
  - degraded still halves the whole command;
  - with no pose, the commands are unchanged.

  The iteration 21 findings stay as tests of the old controller.

## Next candidates (not started)

- In the order the owner agreed on 2026-10-26:
  1. The owner prints the hole-size gauge and the test bars and reports which hole fits each screw, the measured grams, and the printer and settings. These set the hole sizes for the tag case and the thrust stand before those are printed.
  2. (Started as iterations 21 to 24.) Run the owner's own phone recording through the council: express the mode machine's thresholds in seconds rather than ticks, so their timing does not depend on the loop rate (found in iteration 16; a phone logging once a second would double every timeout); add a simple simulated drone that follows the controller's commands; and import a recording from a GPS-logging app in the browser with Pyodide, turning positions into offsets and never uploading or committing them.
  3. A camera batch: a person detector under an open licence (not AGPL), tested on recordings; an estimate of whether the bench kit's Pi Zero 2 W runs it fast enough; and a browser demo that locks onto only the person holding a printed marker and blurs everyone else.
- Start the bench kit from pass 3: a Pi Zero 2 W with its camera cable, one tag, and a measurement of real tag range and battery life. Then log real data for the replay tool.

## Open questions for the owner

- What is the Pixel 8a for? The model assumes the drone's onboard computer and camera (pass 4). Confirm, because the rider's companion is your existing phone.
- Does the $100 budget include the Pixel? The model keeps it outside the budget. The $250 is already more than the budget.
- Do you already own an ELRS-compatible transmitter? It is the largest placeholder in the drone passes ($60 to $120).
- What tools can FAU engineering and IEEE lend or book: a PCB mill or etching setup, soldering and hot-air stations, a bench power supply, a load cell, a laser cutter? See [lab-access.md](lab-access.md). (Money is not on this list: the owner does not like asking for it.)
- How many is "tons" of drones, what would count as success, and how should the first flying drone be paid for without asking for money? See [vision.md](vision.md).
