# Project context for AI agents

Read [AGENTS.md](../AGENTS.md) first for the rules, then this page. It is written for any coding agent (Claude Code, Codex, Grok, Cline or another) that picks up this repo with no memory of earlier sessions. It tells you what the project is, what exists, what is only a plan, what the owner wants, and what to avoid.

Facts here are a snapshot dated 2026-10-26. Where a number comes from a generated table, the table is the source of truth, not this page.

## 1. What this is

A personal hobby and learning project: a drone that follows the owner while pennyboarding and records footage. It is developed with AI coding assistants. The public repo is `dylanstechmann/follow-me-drone-agent`.

The repo holds four things today:

1. **Tested Python logic** ("the council") that combines several imperfect position sources into one estimate of where the rider is, and turns it into follow commands. It runs on recorded or synthetic data only.
2. **A data-driven cost and supply model** that prices building the drone in different ways, from retail parts to parts the owner designs and has made closer to the maker.
3. **A public group-order plan** for the owner's IEEE club.
4. **Documents**: plans, findings, decisions and this record.

Nothing has flown. No hardware has been built or tested. No supplier has been contacted. Nothing has been ordered. No CAD, PCB or firmware file exists.

The wider direction, set by the owner on 2026-10-24, is in [vision.md](vision.md): curiosity about building many drones and the software that may power them, with the owner getting each part themselves, somewhat, instead of using off-the-shelf components.

## 2. What the owner wants

- **Hobby and learning framing.** Keep AI assistance visible in public text. No employment, resume or solo-authorship framing.
- **No asking for money.** The owner does not like asking for money. Do not draft funding, sponsorship, grant or donation requests unless asked. Mentions of possible funding in older docs are optional. Group orders are cost-sharing.
- **Own the pipeline.** Own the capability, not every process: hold the design files, be able to make a part or get it from two sources, and be able to swap a supplier quickly. Get closer to the factory, fab and lab where it pays.
- **Honesty.** Report outcomes faithfully. Say what is a guess. Date every price. Correct mistakes in the open ([decisions.md](decisions.md)).
- **Plan, do, record.** Write each plan in [progress.md](progress.md) before the work, commit and push each iteration, and keep going until the owner says stop.
- **Documents for other agents.** What was discussed lives in this repo.

## 3. Who knows what

| Fact | Source | Verified? |
|---|---|---|
| The working budget is $100 for the bench and pipeline work. | Owner | Owner's figure |
| FAU's engineering building and the IEEE club have 3D printers. | Owner | Not checked |
| The IEEE club can run group orders. | Owner | Not confirmed with the club's officers |
| The owner bought a used Pixel 8a for $250, as an example of a cheap used phone. | Owner | Owner's figure |
| The owner does not like asking for money. | Owner | Stated preference |
| FAU's architecture FabLab has laser cutters, 3D printers and a CNC. | A web search | Not visited |
| The owner can work with a drone club. | Owner (2026-10-26) | Not confirmed. A web search found no university-level FAU drone club, only the K-12 club at FAU's lab schools. |
| FAU prohibits recreational drone use on university property. Other flights need approval through FAU Risk Management. | FAU's environmental health and safety drone page, found by web search | The page is undated. Not confirmed with FAU. |
| FAU's Boca Raton campus borders Boca Raton Airport, which has Class D airspace with LAANC available. | Web search and the airport's site | Check the FAA's B4UFLY app before any flight. |
| Web prices, lead times, licence summaries and duty claims | Web search snippets and fetched pages | Mostly not verified. Only 10 of 51 sourced prices are dated within 12 months of the 2026-10-10 cutoff. |

## 4. How the code fits together

```
sources -> readings -> attention -> fusion -> mode -> controller -> (adapter, not built)
```

1. **Sense.** Each source gives a position estimate for the rider in the drone's body frame (meters, +x forward, +y left) with a variance: the camera, the phone's GNSS, the tag's GNSS.
2. **Attention.** Weather, link quality, GNSS fix quality and known places change each source's weight.
3. **Fuse.** Outliers are rejected against a reliability-weighted median, and the rest are combined by inverse variance.
4. **Mode.** A state machine falls back from tracking to degraded, dead reckoning, hold, and a return-home request, and scales the commands.
5. **Control.** The follow controller turns the estimate into normalized yaw, forward and climb commands.
6. **Adapter.** Commands would go to an autopilot. This does not exist. It needs simulation first.

| Module in `src/follow_me/` | Role | Tests |
|---|---|---|
| `controller.py` | Follow controller: a person's box to yaw, forward and climb commands. | `test_controller.py` |
| `fusion.py` | The estimate and reading types, the weighted-median gate, inverse-variance fusion. | `test_fusion.py` |
| `sources.py` | Camera box to body-frame estimate, and the inverse. | `test_fusion.py` |
| `companion.py` | Rider GNSS fix from the phone or tag to a body-frame estimate. Stale fixes are rejected. | `test_companion.py` |
| `context.py` | Attention weights. Weather provider (Open-Meteo, with injected fetch) and a TTL cache. | `test_context.py` |
| `geo.py`, `places.py` | Geodesy helpers. Place profiles and approach detection. | `test_places.py` |
| `mode.py` | The mode machine. | `test_mode.py` |
| `council.py`, `replay.py` | One tick end to end. A replay tool for JSON logs. | `test_pipeline.py`, `test_replay.py` |
| `bom.py` | The cost and supply model: materials, catalog, passes, price dates, minimum orders, and the cost per drone for a number of drones. | `test_bom.py` |
| `group_order.py` | The group-order plan: lines, quotes, totals, per-member shares. | `test_group_order.py` |
| `docs_sync.py` | Rewrites generated tables in the docs from the data. | `test_docs_sync.py` |

Everything is standard-library Python 3.10 or later, plus pytest. There is no package install step. Every module has tests, and the suite also checks that the generated docs are current and that this page lists every doc.

## 5. The cost and supply model

Data lives in `bom/`:

- `materials.json`: raw inputs and components with a low and high price, a status, a checked date, a source, and a minimum order.
- `catalog.json`: every item, with a path (how it is obtained), and for made or factory-assembled items, the materials it uses.
- `passes.json`: build passes, each a change from an earlier pass, with the reason and the risk it adds.
- `group_order.json`: the group-order plan.

Concepts:

- **Status** says how sure a price is: snapshot, official, estimate, placeholder, owned, purchased, unpriced.
- **Path** says how a part is obtained: buy_retail, buy_bulk, buy_used, buy_service, buy_factory, make, owned, salvage.
- **Checked** is the date the price was seen on its source. A price is fresh only with month precision and a date within 12 months of the cutoff `AS_OF` in `bom.py` (2026-10-10). Move `AS_OF` when prices are re-checked.
- **Composed items** have no price of their own. Their cost is the sum of their materials, with a waste allowance on the high end.
- **Cash at minimum orders** is separate from per-drone cost, because a cheap unit price can sit behind a large minimum order.
- **Cost per drone for a number of drones** divides the cash for that many drones by the count. Fees marked `per_order` (the PCB assembly setup and loading fees) are paid once per order. It is for exploring: the owner has not set a number of drones.

Headline results at the 2026-10-10 prices, core cost per drone in USD, low to high. The generated table in [cost-reduction.md](cost-reduction.md) is current:

| Pass | What it is | Core cost |
|---|---|---|
| 0 | Retail autopilot drone | 557.91 to 964.58 |
| 3 | Bench kit, no flying drone | 67.36 to 101.23 |
| 5 | Bench kit with a made tag | 63.87 to 98.99 (fits $100) |
| 8 | Own autopilot board, ESC, transmitter and tag battery | 275.09 to 623.11 |
| 10 | Factory-assembled own boards, factory magnets and bearings, lab-etched stators | 207.86 to 534.21, with 332.20 to 960.45 of cash at minimum orders |

Main findings:

1. The bench kit fits $100. A flying drone does not fit under any pass so far.
2. Owning more lowers the modelled cost. The largest single saving is an own GNSS board with a bare u-blox chip, factory-assembled, at $15.54 to $28.59 against a $54.99 to $74.90 retail board.
3. Going upstream pays for magnets, bearings and assembled boards. It does not pay for complete motors, props, cells or filament pellets.
4. An outsourced two-layer board is cheaper than etching one. Etching is for fast iteration.
5. Chips, radios and lithium cells cannot be made at home. The design, firmware, boards, structure and motors' build can be owned. Some distributors quote 45 to 53 weeks for an IMU.
6. A used autopilot is no cheaper than a new one at the low end.

Read [make-own-ladder.md](make-own-ladder.md) and [supply-side.md](supply-side.md) for the part-by-part reasoning.

## 6. The group order

[group-order.md](group-order.md) is a public plan for the IEEE club. It has 14 lines in three waves, and the first wave (factory parts, ready now) totals about $159 to $540. There are no quotes yet and no orders. It uses roles only. Keep it current: update the line states, quotes, decisions and `last_updated` in `bom/group_order.json`, then run the sync.

## 7. Hard rules

- **Safety.** No flight-control, geofence or obstacle-avoidance code without a passing simulation test. No claim that the drone is safe, autonomous or ready to fly. Hardware-facing changes need human review before flight.
- **Consent.** Do not track or record a person who has not agreed.
- **Privacy.** The repo is public. No real coordinates, routes, names, emails, phone numbers, addresses, payment records or order screenshots. Real place profiles live outside the repo.
- **No unmade claims.** Do not say an order is placed, a supplier is contacted, a quote exists, a club has decided, or a design works, unless the data says so.
- **No money asks** on the owner's behalf.
- **Generated blocks.** Never edit text between `<!-- generated:... -->` markers. Change the data and run the sync.
- **CAD, PCB and firmware** are unverified until opened, rendered or run. The sandbox used so far has no KiCad or OpenSCAD.

## 8. Traps

- A search snippet is not a current price. See [decisions.md](decisions.md), C07.
- Check part sizes and units before modelling (C08).
- Licence claims here come from forum and index summaries. Read the LICENSE file of PX4, ArduPilot, ELRS, EdgeTX, AM32 and GNSS-SDR before reuse.
- The 2026 duty rate on factory orders is uncertain. The model carries an allowance, not a fact.
- The model leaves out labour, tooling, failures, crashes and rework.
- The Pixel 8a is an example, not a chosen drone computer.
- The pass numbers shift when prices change. Quote the generated tables, with their date.
- Do not claim the owner reviewed the code. No review is recorded.

## 9. How to continue

**For the owner** (the agent cannot do these):

1. Answer the open questions in [vision.md](vision.md) (how many is "tons", what counts as success, how the first flying drone is paid for without asking for money).
2. Ask the IEEE officers: who coordinates, what the university allows for student-organization purchases and parcels, and how many members want each line.
3. Request quotes with the template in [group-order.md](group-order.md), and report the results.
4. Ask the FabLab or the lab: is any laser a fiber laser, is there an etching setup, what tools are available.
5. Ask the drone club the questions in [lab-access.md](lab-access.md), and plan any flight off FAU property unless FAU approves one.

**For an agent:**

1. Re-check the 41 undated or stale prices, starting with chips, GNSS modules and motors. Record the date seen.
2. Price 30 V power MOSFETs on LCSC. This is the largest open placeholder.
3. Read the LICENSE files named above.
4. Update the group-order plan when the owner reports news.
5. When a KiCad or OpenSCAD install exists, build the tag board and enclosure (iteration 14 in the progress log).
6. Then the range-only source (iteration 15), and later person detection and a simulator bridge.

**In the lab or the field**, when equipment exists:

1. Etch a lamination coupon.
2. Build a thrust stand and measure a motor.
3. Measure BLE and Wi-Fi range for the tag.
4. Test a clone GNSS chip against a u-blox reference.

## 10. How to work here

```
python3 -m pytest -q                                   # run the tests
PYTHONPATH=src python3 -m follow_me.bom                # cost report and dependency check
PYTHONPATH=src python3 -m follow_me.docs_sync          # rewrite generated doc tables
PYTHONPATH=src python3 -m follow_me.docs_sync --check  # fail if any table is stale
PYTHONPATH=src python3 -m follow_me.replay examples/replay.example.json
PYTHONPATH=src python3 -m follow_me.group_order        # print the group-order tables
```

- One agent at a time on the working copy. Commit or save before switching tools.
- Commit trailers name the assistant model that did the work.
- After changing anything under `bom/`, run the sync and commit the result. The test suite fails otherwise.
- The workspace this repo sits in has its own rules, in a workspace-level AGENTS.md outside this repo. It describes isolated per-project containers and reservations. Read it if you are working inside that workspace. This repo does not depend on it.

## 11. Glossary

- **Council:** the set of position sources and the rules for weighing them.
- **Attention:** the multiplier on each source's weight, from conditions and places.
- **Place profile:** a stored location with sensor overrides, applied when the rider is approaching it.
- **Mode:** tracking, degraded, dead reckoning, hold, or return-home requested.
- **Gate:** a stage that must pass before the next one (software, replay, simulator, bench, tethered, free flight), and also the outlier test in fusion.
- **Pass:** one version of the build in the cost model, defined as a change from an earlier pass.
- **Composed item:** an item costed from its materials. It is made in-house or assembled by a fab or factory from the owner's design.
- **MOQ:** minimum order quantity.
- **Wave:** a group of order lines in the group-order plan.
- **Fresh:** a price seen with month precision within 12 months of the cutoff.
- **Owner-designed:** a composed item, whoever builds it.
- **Tag:** the small device the rider carries, with a GNSS receiver and a radio.

## 12. Documentation map

Start here, then follow the question you have.

**What and why**

- [vision.md](vision.md): the owner's stance and ambition, the fleet question, the money stance.
- [decisions.md](decisions.md): decisions, corrections and lessons.
- [history.md](history.md): what was discussed and done, in order.
- [progress.md](progress.md): the iteration log, the plans, and open questions.

**Design and safety**

- [architecture.md](architecture.md): the council design.
- [build-plan.md](build-plan.md): the gates from software to free flight.
- [safety.md](safety.md): the safety plan that must be met before flight.
- [privacy-and-rules.md](privacy-and-rules.md): privacy, consent and the rules to verify.
- [sensors-and-companion.md](sensors-and-companion.md): sensors and the companion device.
- [companion-tiers.md](companion-tiers.md): the phone and tag decision and the rule for extra devices.
- [pcb-plan.md](pcb-plan.md): the tag board plan.
- [motors-plan.md](motors-plan.md): the motor research plan.
- [3d-printing.md](3d-printing.md): materials, parts and tests for printed parts.

**Cost and supply**

- [budget.md](budget.md): the $100 working budget.
- [cost-reduction.md](cost-reduction.md): the cost passes and findings (generated table).
- [pipeline.md](pipeline.md): what owning the pipeline means.
- [make-own-ladder.md](make-own-ladder.md): each part, buy or make.
- [supply-side.md](supply-side.md): factories, minimum orders, duty and the lab.
- [parts-catalog.md](parts-catalog.md): the full parts list (generated).
- [price-audit.md](price-audit.md): price dates and placeholders (generated).

**People and orders**

- [group-order.md](group-order.md): the IEEE group-order plan (generated).
- [lab-access.md](lab-access.md): what to ask FAU and the IEEE club.

**Sources**

- [references.md](references.md): sources and credits.
