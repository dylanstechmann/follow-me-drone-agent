# Decisions and corrections

A log for agents and for the owner. Read the decisions before proposing a change that would reverse one. Read the corrections to avoid repeating a mistake. Dates are when the decision was made in conversation. All of the early work happened on 2026-10-10.

## Decisions

| ID | Date | Decision | Why | Where it lives |
|---|---|---|---|---|
| D01 | 2026-10-10 | A public GitHub repo, `follow-me-drone-agent`, framed as a personal hobby and learning project with AI assistance disclosed. | The owner asked for a project and a public repo. The workspace rules require this framing. | [README.md](../README.md), [AGENTS.md](../AGENTS.md) |
| D02 | 2026-10-10 | Simulation first. Build in gates: software core, replay, simulator, bench, tethered, free flight. | A bad edit in flight code can crash a drone near people. | [build-plan.md](build-plan.md), [safety.md](safety.md) |
| D03 | 2026-10-10 | The "council": several imperfect position sources, each weighted by reliability and adjusted by context (weather, link quality, known places), with a fallback ladder. | The owner's idea: diversity of sensors, like an autonomous vehicle's mix of camera, lidar, radar and GPS. | [architecture.md](architecture.md) |
| D04 | 2026-10-10 | Fusion gates outliers against a reliability-weighted median, then combines by inverse variance. | A plain median rejected both sources when only two disagreed. | `src/follow_me/fusion.py` |
| D05 | 2026-10-10 | Companions: a dedicated tag and the phone app together. Any further wearable must earn its place by measured gain, justified cost and safety on the board. Start with none. | Two receivers have independent errors. The owner chose both. | [companion-tiers.md](companion-tiers.md) |
| D06 | 2026-10-10 | Tag version 0 links to the drone over the ESP32-C3's Wi-Fi, not LoRa. Version 2 (a BLE chip and a clone GNSS module) is to be tested, with the ESP32 and u-blox tag as the fallback. | The drone is within follow distance, and it removes a chip. Range is unmeasured. | [pcb-plan.md](pcb-plan.md), [cost-reduction.md](cost-reduction.md) |
| D07 | 2026-10-10 | The working budget is $100 for the bench and pipeline work. Flying hardware is a separate question. | The owner gave $100. The model shows the bench kit fits and a flying drone does not. | [budget.md](budget.md) |
| D08 | 2026-10-10 | Own the pipeline: the capability, not every process. Print the structure, design the boards, outsource PCB production to low-markup fabs, buy chips in bulk, research motors, and later the ESC, transmitter and autopilot. Do not make lithium cells, props or flight packs. | The owner wants control and no dependence on suppliers. PCB fabs have a small premium, and cells and props carry safety risk. | [pipeline.md](pipeline.md), [make-own-ladder.md](make-own-ladder.md) |
| D09 | 2026-10-10 | Every price carries the date it was seen. Stale and undated prices are flagged. Placeholders are counted and labelled. | A mislabelled date made old prices look current (see C07). | [price-audit.md](price-audit.md), `src/follow_me/bom.py` |
| D10 | 2026-10-10 | Go upstream to the factory where it pays: magnets, bearings, factory-assembled boards. Do not where it does not: complete motors, props, cells, filament pellets. Report the cash needed at minimum orders next to the per-drone cost. | The owner asked for the supply side. The model shows where the gain is. | [supply-side.md](supply-side.md) |
| D11 | 2026-10-10 | Group orders through the IEEE club. The plan is public, uses roles only, and is generated from data. | The club can run group orders (owner-reported). Factory minimums need a group. | [group-order.md](group-order.md) |
| D12 | 2026-10-10 | Tables in the docs are generated from the data under `bom/`. Edit the data, run the sync, and the test suite fails if a table is stale. | Hand-copied tables drift out of date. | `src/follow_me/docs_sync.py` |
| D13 | 2026-10-10 | The owner's used Pixel 8a was an example of a cheap feature-rich phone. It is a parts source, not a decided drone computer. | The owner clarified this. | `pass4` in `bom/passes.json` |
| D14 | 2026-10-24 | The owner does not like asking for money. No funding, sponsorship or grant requests unless the owner asks. Funding mentions in older docs are optional. | The owner's stated preference. | [vision.md](vision.md), [AGENTS.md](../AGENTS.md) |
| D15 | 2026-10-24 | Direction: curiosity about many drones and the software that may power them, with the owner sourcing or making the parts, somewhat. This is not a plan of record. | The owner's stated interest. | [vision.md](vision.md) |
| D16 | 2026-10-24 | Record the project, the vision and the history in the repo, so that any AI agent can pick it up. | The owner asked. | [project-context.md](project-context.md), [history.md](history.md) |
| D17 | 2026-10-26 | A static website on GitHub Pages, built from the repo's data in GitHub Actions at every push to main. No backend, analytics or cookies. The browser draws what the tested Python computed and never re-implements the logic. | The owner asked for easy visualizations and a site for the repo. Building from the data keeps the site from falling behind. | [website.md](website.md), `src/follow_me/website.py` |
| D18 | 2026-10-26 | Printable parts are adjustable OpenSCAD sources in `cad/` with print cards. The site renders them with OpenSCAD's WebAssembly build and its Manifold engine, in CI and in the visitor's browser. Browser libraries are fetched at build time, pinned and hash-checked, rather than kept in git. | OpenSCAD could not be installed here, but its WebAssembly build runs under Node.js and in browsers. Text sources keep the designs reviewable and owned, and pinned downloads keep library code out of git. | [3d-printing.md](3d-printing.md), [website.md](website.md) |

## Corrections

Mistakes found and fixed. Each one is a trap for the next agent.

| ID | Found | What was wrong | What changed |
|---|---|---|---|
| C01 | Replay example | With two sources, a plain median rejected both whenever they disagreed, even if one was far more reliable. | A reliability-weighted median, with a tie returning the midpoint. |
| C02 | Companion test | The default "degraded" threshold of 4 m squared would call a single 2 m GNSS fix degraded. | Raised to 9 m squared (3 m one-sigma). This is a guess to tune on real logs. |
| C03 | BOM report | Each pass was compared with the line above it, not with its base. | Compared against the base pass. |
| C04 | Docs check | The printing saving ignored the added guards, the transmitter was called unpriced when it was a placeholder, and a tier was said to fit the budget when it did not. | Three claims corrected. |
| C05 | README | It said uv and Docker Compose were in use. They were not. | Corrected to what exists. |
| C06 | Pipeline report | The "made or owned" share counted the Pixel purchase as self-made. | Only made and salvaged parts count. |
| C07 | Owner feedback | The catalog said "searched 2026-10-10", which made years-old listings look current. | A date on every price, a 12-month freshness rule, and an audit. Only 9 of 39 prices qualified at the time. |
| C08 | Factory pass | The motor model used 608 skateboard bearings. They are 22 mm across, the same size as a 2207 stator, and cannot fit. | Miniature 4 x 9 x 4 mm bearings. The DIY motor became dearer at retail parts. |
| C09 | Factory pass | The stator plan assumed a laser that cuts steel. Most makerspace CO2 lasers cannot. | A fiber laser, a cutting service or chemical etching, with the etching unverified. |
| C10 | Used-autopilot pass | A used autopilot was expected to save a lot. Its price matched the new board at the low end. | The saving was traced to dropping the Pi 5 and the ToF sensor. |
| C11 | Pixel pass | The phone was first modelled as an owned $0 device. It was a $250 purchase. | The cost is shown as a purchase. |
| C12 | This pass | The README, privacy and lab docs said the code was "reviewed by the owner". No review is recorded. | Reworded to "written by AI coding agents at the owner's direction". |
| C13 | Replay example (2026-10-26) | The progress log said the example log exercises hold, return-home and the full fallback ladder. At default settings the replay tool showed only tracking and dead reckoning: the log had 4 empty ticks against a 10-tick dead-reckoning window. Only the tests, with shortened thresholds, reached hold and return-home, and degraded never appeared. | The example now has a degraded stretch and a long loss, and a test checks that it walks every mode at default settings. |
| C14 | Cash at minimum orders (2026-10-26) | The cash at minimum orders left out the waste allowance on made items, while the per-drone cost included it. The high end of passes 6 to 11 was $24 to $57 too low (pass 10: $934.98, now $960.45). | The cash high end applies each made item's waste allowance before comparing with the minimum order, and a test checks it. Figures quoted in the docs were updated. The progress log and history keep the old figures as records of that time. |

## Lessons for agents

- A search snippet is not a current price. Record the date the source shows, or mark the price undated.
- Say what is a guess. Count placeholders. Do not present estimates as quotes.
- Check units and sizes before modelling a part (C08).
- Do not claim an order, a quote, a supplier contact or a club decision that has not happened.
- Licence claims from forum posts need a read of the real LICENSE file.
- Do not claim the owner reviewed or built something unless it is recorded.
- Mark CAD, PCB and firmware as unverified until it is opened, rendered or run.
- Keep personal data out of this public repo.
- Do not draft money asks.
