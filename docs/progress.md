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

## Iteration 28: the website and docs (done: 309 tests pass)

- The replay page has a third example: the same made-up ride with the controller as it was before feed-forward (`data/sim-example-before.json`). The median distance is 20.4 m before and 7.0 m after, and the time in the band is 7% and 17%. A test checks that the new controller is closer.
- The tick panel shows the rider's estimated speed over the ground, its uncertainty, and the share fed forward. The first tile adds the closest approach.
- Checked in a headless browser at 1280 px in the light theme and 390 px in the dark theme: all three examples load with no errors or sideways scrolling, and the made-up GPX opens. Feed-forward brought the GPX ride's median distance from 53.5 m to 21.3 m; it is still degraded throughout at a phone's accuracy.
- Fixed what the screenshots and code review showed:
  - The distance chart's axis labels used quarter steps such as 37.5 m, which were clipped. They now use round steps.
  - The tick panel would have printed "null" for ticks without motion, because the DOM's `append` turns a null into text.
- [simulation.md](simulation.md) has the before and after table, and the history has a new phase.

## Iterations 29 and 30 plan: hold back when the position is uncertain (2026-10-26)

- Owner input (2026-10-26): the owner replied "yeah" to the agent's question about pushing iterations 26 to 28 and its proposed next step: fixing the close approach with noisy fixes.
- Iteration 29, a safety margin:
  - The council shows the controller the rider closer than estimated, by 2.5 times the estimate's one-sigma uncertainty, so the drone holds back further when it is less sure where the rider is.
  - If the reported accuracy is honest, 2.5 one-sided sigmas keep the real rider outside the band's near edge about 99% of the time.
  - `margin_sigmas=0` gives the iteration 27 controller.
  - Tried in a prototype first:
    - With honest 3 m fixes on a standing rider, the closest approach after the start rises from 0.2 to 1.5 m to 8 to 10 m.
    - With 3 m errors reported as 2 m, it is 3 to 5 m. The margin is only as good as the reported accuracy.
    - Clean following moves about 2.7 m further back.
  - Tests in the simulation, as the safety rule asks.
- Iteration 30, the website and docs:
  - The distance chart shows the band the controller aims for, pushed out by the margin.
  - A tile shows the time spent closer than the band's near edge.
  - The panel shows each tick's margin.
  - The "before" example becomes the controller without feed-forward or the margin.
- Stop point: ask the owner before pushing.

## Iteration 29: a safety margin (done: 317 tests pass)

- The council shows the controller the rider closer than estimated, by 2.5 times the estimate's one-sigma uncertainty, but never closer than 0.25 m (decision D23). The drone holds back further when it is less sure. `Council(margin_sigmas=0)` gives the iteration 27 controller. Each tick's margin goes into the trace, the settings record `margin_sigmas`, and the simulation summary reports the share of time closer than the band's near edge.
- Results, with the full tables in [simulation.md](simulation.md):
  - **Honest 3 m errors:** a standing rider is no longer approached closer than 8.2 m after the start, against 0.3 to 1.8 m before.
  - **The same errors reported as 2 m:** 2.9 to 4.9 m. The margin is only as good as the reported accuracy. Feed-forward alone had made this case worse, at 0.0 to 0.7 m.
  - **A sudden stop:** stays 6.1 m clear.
  - **The cost:** clean following sits at 9 to 12.5 m instead of 6 to 10 m, and the example ride's median distance is 12.2 m, against 7.0 m with feed-forward alone and 20.4 m originally.
- Tests:
  - the earlier controllers are pinned with `P_ONLY` and `FEED_ONLY`, so their findings stay checked;
  - new tests cover noisy fixes with honest and under-reported accuracy, following and stopping with the margin, the margin's size, and the geometry of moving the estimate closer.
- Also changed: the replay tool's commands for the example log now include the margin, as every caller of the council does.

## Iteration 30: the website and docs for the margin (done: 317 tests pass)

- The distance chart shades the band the controller aims for, pushed out by each tick's margin, and draws the band's near edge (3.79 m) as a dashed too-close line, with a legend.
- The second tile is now the time spent closer than the band. It is 0% for both examples and the made-up recording.
- The panel shows the tick's margin, and "How to read it" explains it.
- The comparison example is the original controller, with neither feed-forward nor the margin.
- Checked in a headless browser at 1280 px in the light theme and 390 px in the dark theme: all pages, links and the parts slider work, with no errors or sideways scrolling. The made-up GPX ride, at a phone's accuracy, is now followed at a median of 36.9 m, the price of holding back when the position is uncertain.

## Iterations 31 to 34 plan: the camera (2026-10-26)

- Owner input (2026-10-26): the owner replied "ok" to the agent's question about pushing iterations 29 and 30 and its proposed next step, the camera batch agreed earlier.
- Iteration 31, a simulated camera:
  - The kinematic simulation gets a camera source with a 90 degree field of view and a range limit. It uses the error model already in `sources.camera_estimate` (0.05 rad of bearing, 15% of range), with seeded noise, and gives a reading only when the rider is in view.
  - Fused with the phone, it should show how a camera shrinks the uncertainty and so the safety margin. The error model is a placeholder, not a measurement.
- Iteration 32, a person detector:
  - YOLOX-Nano (Apache-2.0, the authors' own ONNX export, 3.7 MB), run with onnxruntime-web 1.30.0 (MIT) in Node.js for tests and timing.
  - Box decoding and overlap removal go in a small JavaScript module, tested with Node's own test runner, in CI too.
  - Measure the time per frame here, and estimate the Pi Zero 2 W, labelled as an estimate, with a script the owner can run on a Pi.
  - No AGPL or GPL models.
- Iteration 33, a camera page on the website:
  - The visitor's webcam, or a photo they choose, goes through the detector in their browser.
  - The person holding a printed ArUco marker (js-aruco2, MIT) is the rider. Everyone else is blurred before anything is drawn, and is never tracked.
  - The rider's box goes through the repo's own Python (Pyodide) for the camera estimate and the follow command.
  - Nothing is recorded or uploaded, and the page has a marker to print.
  - Consent and bystander privacy: only a person showing the marker is followed, and the page says to point it only at people who agree.
- Iteration 34: docs and checks.
- Stop point: ask the owner before pushing.

## Iteration 31: a simulated camera (done: 323 tests pass)

- `sim.Camera` stands in for a person detector:
  - It sees the rider only inside the council's 90 degree view and within 30 m, and misses at random 10% of the time.
  - It makes the box a detector would, with the error model already in `sources.camera_estimate`, and passes the box through that function.
  - It is idealised: no other people, no wrong detections, nothing in the way. Its numbers are placeholders.
  - The summary reports the share of ticks the camera saw the rider.
- Results, with the table in [simulation.md](simulation.md):
  - With a phone at 4 m accuracy, adding the camera takes the follow from degraded the whole time, 21 to 38 m behind, to tracking about 87% of the time, about 11 m behind.
  - On the example ride, it bridges the 15 s gap in the fixes, so there is no hold, and the median distance falls from 12.2 m to 9.7 m.
  - In no case did the drone come closer than the band's near edge.
- Tests:
  - the camera sees only in view and in range, and its readings carry `camera_estimate`'s error model;
  - a degraded phone follow becomes tracking, and the gap is bridged;
  - noisy fixes still never bring the drone too close;
  - the miss rate holds, and the seed repeats.
- The website has a third simulated example, the same ride with the camera (`data/sim-example-camera.json`).

## Iteration 32: a person detector (done: 324 Python and 7 JavaScript tests pass)

- Chose YOLOX-Nano: Apache-2.0, the authors' own ONNX export (3.7 MB), 25.8 mAP on COCO. The common alternatives' licences were checked on GitHub: Ultralytics' YOLOv5, v8 and 11 are AGPL-3.0, YOLOv7 and v9 are GPL-3.0, and Yolo-FastestV2 has no licence.
- The model runs with onnxruntime-web 1.30.0 (MIT). That release is from 2026-09-14; the 1.31.1 released that day was passed over as too new.
- The build pins both pieces: the runtime by npm's hash, and the model by a sha512 hash taken on first download, because GitHub publishes none. `fetch_vendor` can now copy a single file as well as files from a tarball.
- `site/assets/detector.js` prepares the frame, decodes the 3,549 candidate boxes, keeps people and removes overlaps. It runs unchanged in the browser and in Node.js. Seven tests run with Node's own test runner, and CI now runs them.
- Timing on this machine (Intel i9-11980HK): about 70 ms per frame on one thread in Node.js. On the Raspberry Pi Zero 2 W, the estimate is about 250 ms, or 4 frames a second, with ncnn. That scales ncnn's published Pi Zero 2 W result for NanoDet-m (166 ms for 0.72 GFLOPs) to YOLOX-Nano's 1.08 GFLOPs. `node tools/detect_bench.mjs` measures it on a real Pi, as an upper bound.
- Checked on three COCO validation photos in a headless browser: 1, 11 and 4 people found, with the boxes in place, at 71 to 119 ms per frame. This confirms the input format: raw BGR values, padded at the top left. The photos stayed on the agent's machine.
- Found while testing: this onnxruntime-web build cannot use threads in Node.js, so the timing tool uses one.
- See [camera.md](camera.md).

## Iteration 33: the camera page (done: 329 Python and 12 JavaScript tests pass)

- Added `camera.html`, linked from every page and from the overview:
  - The visitor's camera, or a photo they choose, goes through the detector in a worker, and js-aruco2 (MIT, pinned) finds the printed marker.
  - The person whose box holds the marker is the rider (`rider.js`). If the marker is hidden, the same person is kept for one second by overlap.
  - The whole picture is blurred and only the rider's box is drawn sharp, so missed people stay blurred too (decision D24).
  - The rider's box goes to `follow_me.camera_view` in Pyodide, which keeps a council between frames: the estimate, the safety margin, the mode and the command.
  - The camera stops when the page is hidden, and nothing is recorded or uploaded.
- The two workers that run Python now share `python.js`, and the build reports `camera` in `data/build.json`.
- Tests:
  - `test_camera_view.py`: the estimate is `camera_estimate`'s, the commands follow from it, and a lost rider walks down the modes in seconds;
  - `rider.test.mjs`: the holder is the smallest box around the marker, only the right marker counts, and the hold works and then lets go.
- Checked in a headless browser with a COCO photo of 11 people and the marker pasted onto one, kept on the agent's machine only:
  - **Photo mode:** found all 11, followed only the marked person, and blurred a bystander's region from 12.5 to 1.9 on a sharpness measure, while the rider's stayed at 14.5 of 15.1.
  - **Live camera mode:** with Chromium's fake camera playing the same picture, it ran at 73 ms a frame and stopped cleanly.
  - **Layout:** no errors or sideways scrolling at desktop width in the light theme and phone width in the dark theme.

## Iteration 34: checks and docs (done: 329 Python and 12 JavaScript tests pass)

- Checked a full build in a headless browser:
  - all five pages at 1280 px in the light theme and 390 px in the dark theme, with no errors, failed requests or sideways scrolling;
  - every same-site link loads;
  - the parts page still re-renders in 0.3 s;
  - the replay page's four examples load, and a GPX still opens through the refactored worker.
- Docs: [camera.md](camera.md) covers the detector, its speed and the camera page; [privacy-and-rules.md](privacy-and-rules.md) covers the page's rules; decision D24 records the blur-everything design. The history has a new phase.
- Not done: a camera on a drone, detection measured on real rides, and the Pi Zero 2 W timing measured on a real board (`tools/detect_bench.mjs` is ready for it).
- Published `ed81598` on 2026-10-27 after the owner's "ok". The workflow run passed, including the 12 JavaScript tests in CI.
- The live check:
  - GitHub Pages serves the runtime's `.mjs` as JavaScript and its `.wasm` as `application/wasm`.
  - A first start downloads about 13.6 MB compressed; the page says about 15 MB.
  - In a headless browser, the live camera page followed only the marked person in a test photo, at desktop and phone widths, and blurred the bystander, at 102 to 107 ms a frame.
  - Chromium's fake camera ran and stopped cleanly.
  - There were no errors.

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

## Iteration 35: how far the detector can see (planned and done 2026-10-27)

- Owner input (2026-10-27): the owner asked what else could be done before work away from the computer. The agent recommended measuring the detector's range and putting it into the simulated camera, then two-phone support, then refreshing stale prices. It started the first. The plan was given in the conversation and is written here with the result.
- `tools/detector_recall.py` and `tools/detector_recall.html` measure recall on a seeded sample of COCO validation photos. The detector runs in a browser on photos placed inside a site build, and the script matches its detections to the drawn boxes.
  - The first run was a prototype in the agent's scratch space. Re-run through the committed tool, it gave identical detections, 500 photos in 43 s.
  - The photos stay on the machine that runs the tool and are never committed.
- Result, at the camera page's 0.35 score, for all 1,950 people:
  - 89% found when 128 px or taller in the input (under 4 m with a 70 degree camera);
  - 66 to 69% at 48 to 96 px (5 to 11 m);
  - 47% at 32 to 48 px (11 to 16 m);
  - 31% at 24 to 32 px;
  - 12% at 16 to 24 px;
  - under 5% below 16 px.

  It made 0.33 wrong detections per photo. Clearly visible people (10 or more of 17 body points marked) were found about 10 points more often. The table is in [camera.md](camera.md).
- The simulated camera now sees the rider only as often as this measured curve gives (`MEASURED_RECALL`, by height on screen). That replaces the placeholder of 90% out to 30 m, which was far too optimistic.
- Found:
  - At phone accuracy, the safety margin keeps the drone 15 to 40 m back, where the rider is seldom found. With the measured camera, a 4 m/s follow stays at 36.8 m with 4% tracking, a trap.
  - A 2x crop around where the council expects the rider breaks it: 15.8 m with 64% tracking.
  - A narrower lens did worse, but that is confounded, because the box-height controller moves the follow distance out with a narrower lens.
  - Cropping is listed as the next camera candidate.
- Tests:
  - the recall curve and its sampling;
  - mechanism tests use a camera that always sees;
  - the measured camera helps a degraded follow only a little, and the crop breaks the trap.
- The camera page now states the detector's range.

## Iteration 36: two phones on the same walk (planned and done 2026-10-27)

- The plan, from the owner's earlier "both" (they have an Android phone and an iPhone) and the agent's recommendation on 2026-10-27: run two recordings of the same walk as phone and tag, and check the phones' reported accuracy, which the safety margin relies on.
- `recording.read_gpx_pair` reads two GPX files onto one origin: the first recording's first fix, and the earlier start time. They must overlap in time. The parsing was split from the offsetting so both files share it, and the coordinates and times still go no further than the importer.
- `recording.apart` compares the phones:
  - the median and 95% separation over their shared time;
  - the median their reported accuracies predict if honest, read as 68% radii as Android reports them;
  - a verdict: optimistic above a 1.5 ratio, cautious below 0.67.

  Errors both phones share cancel, so the separation is a lower bound on each phone's error.
- `sim.simulate(..., second=...)` adds the second phone as `tag_gnss` readings, and takes the rider to be midway between the phones. Traces carry the second track. The CLI accepts two files, and the replay page opens one or two and draws the second phone's track.
- Made-up check, two walks with 2 m of error per axis:
  - **Honestly reported:** "about right", ratio 1.05; median distance 11.7 m and never too close.
  - **Understated as 1 m:** "optimistic", ratio 3.18; median 7.7 m, 2% of the time closer than the band, and 11.5 s of dead reckoning where the gate threw out readings that disagreed more than their claimed accuracy allowed.
- Tests:
  - a shared origin and clock, and recordings that do not overlap refused;
  - honest pairs called about right and understated ones optimistic;
  - the phone and tag sources;
  - the gate rejecting a phone 15 m off;
  - the CLI with two files.
- Checked in a headless browser: two files opened together, the note gave the verdict, and the second track was drawn, with no errors.

## Iterations 37 to 39 plan: crop around the rider (2026-10-27)

- Owner input (2026-10-27): the owner replied "ok" to the agent's question about pushing iterations 35 and 36, and to its proposed next step, cropping.
- Iteration 37, measure a crop on COCO:
  - For each drawn person, crop a square around them, three times their height and inside the photo. Scale it to the detector's input, and check whether the detector finds them.
  - This measures the gain for a camera with no spare pixels, such as a 640 x 480 webcam, where the crop is only enlarged. A camera with spare pixels would gain more.
  - Crops centred on the drawn box are kinder than crops centred on an estimate, so the result is an upper bound for that camera.
- Iteration 38, the crop in the simulation:
  - The camera crops around where the council last placed the rider, when it has an estimate.
  - It falls back to the whole frame when there is no estimate, when the rider would not fit in the crop, or when the rider is outside it.
  - Two settings: a camera with spare pixels (the rider's height times the zoom), and one without (the curve measured in iteration 37).
- Iteration 39, the camera page:
  - The marker starts the follow. A 15 cm marker is only about 7 pixels wide at 10 m on a 640-pixel webcam, too small to read. So after that, the same person is followed by box overlap from frame to frame.
  - The follow stops if the person is lost for a second, or if two people overlap the rider's last box. It does not guess between people.
  - The detector runs on a crop around the rider's last box.
  - Tests and a headless check.
- Stop point: ask the owner before pushing.

## Iteration 37: a crop, measured on COCO (done)

- `tools/detector_recall.html` has a crop mode, `?mode=crop`. It runs the detector once per drawn person, on a square crop three times their height (at least 160 pixels, inside the photo), enlarged to the input. `tools/detector_recall.py crop` compares that with the whole photo for people of the same height.
- On the same 500 photos, 1,950 crops, at a score of 0.35, cropping found people of 16 to 48 px far more often: 57 to 70%, against 12 to 46% in the whole photo. People 96 px and taller gained nothing. No camera detail was added, so this is what a webcam can get. Crops centred on the drawn box make it an upper bound. Full table in [camera.md](camera.md).
- The tool now draws the whole-photo mode through the same function as the crops, so its numbers moved by up to 2 points. The simulation's `MEASURED_RECALL` was updated to match.

## Iteration 38: the crop in the simulation (done: 339 tests pass)

- `sim.Camera(crop=True)` crops around where the council last placed the rider: three times the expected height, at least a third of the frame. When that crop holds the rider (`sim.crop_holds`: centred near them, and they fit), the measured crop recall applies. Otherwise the whole frame's applies.
- Results: at phone accuracy, cropping takes a 4 m/s follow from 36.8 m behind with 4% tracking to 15.7 m with 65%, and a 2 m/s follow from 17.6 m and 29% to 14.2 m and 66%. The example ride tracks 89% of the time at 10.7 m. A camera zooming 2x into spare pixels does about as well.
- Tests: the trap broken by the measured crop and by a 2x zoom; when a crop holds the rider.

## Iteration 39: cropping on the camera page (done: 339 Python and 15 JavaScript tests pass)

- `rider.js`:
  - The marker starts a follow, and box overlap from frame to frame continues it, even when the marker is too small to read. Before, overlap kept a rider for one second.
  - The follow stops after a second lost, or at once when two people overlap the rider's last box. It never guesses between people (decision D25).
  - While a lost rider is waited for, the page neither draws their old box sharp nor sends it on.
  - `cropAround` gives the crop: three times the rider's height, at least 160 pixels, inside the frame.
- `camera.js`:
  - While there is a rider, followed or waited for, the detector looks at the crop around their last box, enlarged, and the page draws the crop dashed. Otherwise it looks at the whole frame.
  - Found while testing: switching back to the whole frame after a single missed detection lost a small rider within a second, because the whole frame finds them far less often. Waiting now keeps the crop.
- Checked in a headless browser:
  - The photo mode is unchanged.
  - With a fake camera playing a made-up video, a lone rider shrinking from 332 to 93 pixels tall was followed throughout: by the marker, then by overlap once the marker could not be read, through the crop. That held for over 10 seconds at a size where the whole frame no longer found them.
- Also found while testing:
  - My first test image had a marker covering most of the torso, which hid the person from the detector at a distance. The page now advises a 15 to 20 cm marker.
  - A dense group shrunk this far stops the follow as intended.
  - After JPEG compression this rider was found down to 93 pixels tall, not at 66.
- JavaScript tests: following by overlap for as long as it lasts, waiting unseen and letting go, stopping when two people overlap, and the crop's geometry.

## Iteration 40 plan: re-check the out-of-date prices (2026-10-27)

- Owner input (2026-10-27): the owner replied "ok" to the agent's question about pushing iterations 37 to 39, and to its proposed next step, refreshing the cost model's out-of-date prices.
- Only 10 of the 51 sourced prices (snapshot or official) were dated within 12 months of the 2026-10-10 cutoff. The other 41 were undated or year-only.
- Re-check each of the 41 on its listed sources, through the agent's web access:
  - Record what a source shows today, with `checked` set to 2026-10-27. Low and high become the lowest and highest prices seen today across the row's sources.
  - Replace a source that is gone with one selling the same thing, and say so in the note.
  - Leave a row undated when none of its sources could be read, and say which were tried.
- Move `AS_OF` to 2026-10-27, so today's dates count, and update the docs that quote the cutoff.
- Placeholders stay guesses: this iteration re-checks sourced prices only.
- Stop point: ask the owner before pushing.

## Iteration 40: the prices re-checked (done: 339 Python and 15 JavaScript tests pass)

- Read on 2026-10-27 through the agent's web access: stores' own product data, LCSC's product pages, and fetched pages. 37 of the 41 rows now carry that date. With the 10 already fresh, 47 of 51 sourced prices are dated within 12 months of the new cutoff, `AS_OF` = 2026-10-27.
- Not re-checked, still undated:
  - the used Pix32 v5 (eBay blocked automated reading);
  - single-sided FR4 (Newark and Mouser timed out);
  - N52 magnets by weight (the vendor page would not load);
  - factory stator cores (the listing blocked automated reading).
- How rows were set: low and high are the lowest and highest prices seen that day across a row's sources. Sources that are gone were removed. Sources that could not be read were kept, and the note names them.
- Notable changes:
  - **Raspberry Pi 5 4 GB:** $110, not $70. Raspberry Pi raised it by $15 on 2026-02-02 and by $25 on 2026-04-01 (correction C15).
  - **ESC gate driver:** the cheaper JSMSEMI FD6288Q is no longer listed at LCSC (its page says "Part not found"), and JLCPCB's page shows no stock or price. The Fortior original is $1.15 to $2.37 and out of stock at LCSC. A search engine's cached page still showed the JSMSEMI part in stock, which LCSC's own page and API contradict. Iteration 41 looked for alternatives.
  - **Bare NEO-M9N:** $16.15 to $16.55 at LCSC, against $10.99 to $16.04 before. Symmetry's cheaper price could not be re-read: its page now redirects to Braemac.
  - **2207 motor:** the T-Motor V2207 V2 was sold out at Pyrodrone ($16.99), and T-Motor's store blocked reading. The row is now a known-brand 2207, priced from the EMAX E3 at $14.99 to $17.99, against $10 to $13.50 before.
  - **Pix32 v6:** $189.00 to $252.97, so a used v5 at $149 now saves $40 to $104.
  - **Others:**
    - STM32H743: $7.86 to $10.78.
    - JLCPCB's loading fee per extended part: $3.07.
    - Cells from a US distributor: $4.99 to $6.99, against $1.00 to $3.20 wholesale before.
    - The load cell set: $7.45 to $13.90.
    - PLA: $10.29 to $17.99 per kg.
    - ELRS nano receivers: $9.99 to $18.99.
  - **Factory magnets:** the listing's $0.01 tier (5,000 or more) was left out, because a 1.2 g N52 disc holds about $0.05 of rare earth at September 2026 metal prices. The minimum is now 10 pieces, as the listing says. The Alibaba listing is gone.
  - **Single prices:** where only one seller could be read, a range became one price: the Tello ($79), the 3018 mill ($169), and the 2-layer board ($0.40 before shipping).
- Results:
  - Pass 0: $668.18 to $977.10, against $557.91 to $964.58 before.
  - Pass 5, the bench kit with a made tag: $69.13 to $99.20, still inside $100.
  - Pass 10: $239.66 to $544.96, against $207.86 to $534.21, with $361.63 to $841.62 of cash at minimum orders.
  - The motors' factory parts now save more than the own GPS board.
- Docs:
  - The generated tables were re-synced.
  - The prices quoted in the text of these docs were updated: cost reduction, supply side, make-or-own, motors, pipeline, PCB plan, companion tiers, vision, build plan and project context.
  - The group-order plan's two sample prices are dated, and its magnet line gives the price tiers.
  - The website's cost page says prices were seen up to the cutoff, instead of "many are older".
  - Older entries in this log and in the history keep the old figures as records of their time.
- A test pinned the shipped PLA price. It now expects $10.29.
- Pushed 2026-10-27 (c611e7e) after the owner's "ok". The workflow passed. The live site reports commit c611e7e, the 2026-10-27 cutoff and 47 of 51 sourced prices dated, and its cost page carries the new banner.

## Iteration 41: the ESC gate driver (planned and done 2026-10-27)

- Owner input: the owner replied "ok" to the question about pushing iteration 40. The one open computer-only item was a source for the gate driver, so the agent looked for one.
- Read live at LCSC through its product API, which returns nothing for a part that is no longer listed:

  | Part | Package | In stock | Price, one piece to the largest break |
  |---|---|---|---|
  | Fortior FD6288Q (the part the model prices) | QFN-24 | 0 | $2.37 to $1.15 at 1,000 |
  | Fortior FD6288T (same family) | TSSOP-20 | 0 | $0.88 to $0.49 at 1,000 |
  | JSMSEMI FD6288Q and FD6288T | | not listed | |
  | EG Micro EG2133 (C190343) | TSSOP-20 | 3,996 | $0.46 to $0.27 at 2,000 |
  | TI DRV8300DIPWR | TSSOP-20 | 203 | $1.23 to $0.71 at 1,000 |

- The EG2133's datasheet reportedly has active-low low-side inputs (found in a search summary of a Chinese datasheet, version 1.0, 2017; not read in full), so it may not be a drop-in. The DRV8300 is a different family: 100 V, 750 mA and 1.5 A drive. Neither is checked against an ESC design, because none is drawn yet.
- The model still prices the FD6288Q. Swapping to either alternative would lower an ESC by about $2 to $8, so the totals stand. The material's note lists the alternatives.
- Search snippets disagreed with the live pages on stock: one cached page showed 61,569 FD6288T in stock, and another showed the JSMSEMI part in stock. Stock here is what the LCSC API said on 2026-10-27. LCSC's stock is not JLCPCB's assembly library: stock for factory assembly needs a check on JLCPCB's parts page.
