# History: what was discussed and done

A plain account for agents and for the owner. It follows the order of events. The first fifteen commits were all made on 2026-10-10, in one long working session. The vision and this record were added on 2026-10-24.

## Who did what

- **The owner** gave the direction and the decisions, and supplied facts only the owner knows: the $100 budget, access to 3D printers at FAU's engineering building and the IEEE club, that the IEEE club can run group orders, the purchase of a used Pixel 8a for $250, the preference not to ask for money, and the interest in building many drones.
- **AI coding agents** (Claude Code) wrote all the code, tests and docs, ran the web research, and did the calculations. The assistant model changed over the session: the commit trailers show Claude Haiku 5.5 for the first thirteen commits, Claude Opus 5.5 for one, and Claude Sonnet 5.5 for one.
- **Not done by anyone yet:** building or testing any hardware, contacting any supplier, ordering anything, reading the licence files, visiting a lab, running a flight, or opening a CAD or PCB file. No review of the code by the owner is recorded.

## Phase 0: origin

The owner pasted a Perplexity comparison of Claude Code, Codex and Grok Build for a repo "similar to my machine-cad-agent repo, but for a drone that would follow me around for footage of me pennyboarding". The shared link could not be opened by the agent, so the pasted text was used. Its claims about pricing, benchmarks and the other repo's structure were not verified and are not used anywhere in the repo. The comparison explains why the repo is written for several agents: the owner works with more than one.

The owner asked for the project and a public GitHub repo. The first agent created `follow-me-drone-agent` (`cbc4cb4`) with a README, safety rules and a rule set for agents.

## Phase 1: skeleton and first code (`b43888f`)

The owner added: the budget is $100, the parts could be built from scratch, and FAU or the FAU IEEE chapter is a possible funding source. The agent wrote the follow controller, which turns a person's box in the camera frame into yaw, forward and climb commands, with unit tests, and added the budget and funding notes. The funding note is now optional (see [vision.md](vision.md)).

## Phase 2: the council (iterations 1 to 5)

The owner described the design idea: like an autonomous vehicle, use many sensors (camera, lidar, radar, geofencing, satellite and cellular and local positioning), where each could do the job alone, but the variety gives fallbacks and acts like a council. Add data for places that trip some sensors (the example was a shed that fools some sensors), adjust sensor attention by local weather, and use a device worn by the rider. The owner also wanted drones built cheaply from individually bought or repurposed parts, 3D printing and low-data SIM cards. The owner asked the agent to plan, do, record, and repeat until told to stop.

Built: architecture, sensors and safety docs (`b50ecd4`), the fusion core (`2e8a8eb`), weather and attention (`4cd6a0d`), place profiles (`0d28898`), and the mode machine, council tick and replay tool (`8b14c7f`). Found and fixed C01 in [decisions.md](decisions.md).

## Phase 3: companions (iteration 6, `33e5978`)

The owner chose a dedicated tag plus the phone app, and worried that it could get "ridiculous" with a motion-capture suit and a sack of transmitters. That produced the rule that any extra device must earn its place, and that the default is none. Built: companion GNSS for the phone and tag. Found C02.

## Phase 4: parts, prices and 3D printing (iterations 7 and 8, `668ec60`, `d1fc007`)

The owner asked to document parts and 3D printing ideas, to explore prices, and to reduce them repeatedly. Built: a parts catalog, cost passes, a cost report, and docs on printing, cost reduction and companion tiers. Found C03, C04 and C10. Main finding: the bench kit fits $100, and a flying drone does not.

## Phase 5: owning the pipeline (iteration 9, `90afffb`)

The owner said the prices were inflated, that FAU engineering and the IEEE club have 3D printers, that they had bought a used Pixel 8a on Swappa for $250, and that they want to own the whole pipeline without paying supplier markups. Built: a raw-materials file, made items costed from materials, a dependency check, and plans for PCBs, motors and lab access. Found C05, C06 and C11. Main finding: an outsourced two-layer board costs less than etching one, so owning the pipeline means owning the design and the ability to swap suppliers, not making every part.

## Phase 6: price audit and the make-or-own ladder (iteration 10, `d9e34e7`)

The owner said the prices were not 2026, asked how to make the chips, lithium cells, autopilot, GPS, ESC, transmitter, motors, steel core, ESP32 and LoRa chip, and said the Pixel was only an example of a cheap used phone. Built: a date on every price, a freshness audit, new research on 2026 prices, and a part-by-part make-or-own ladder. Found C07. Main finding: chips, radios and lithium cells cannot be made at home, while the design, firmware, boards, structure and motors' build can be owned.

## Phase 7: the supply side (iteration 11, `a8bccee`)

The owner asked to make it cheaper, own more, and get closer to the supply side, the factory, the fab and the lab. Built: minimum orders, the cash needed to start, factory-assembled designs, and a supply-side doc. Found C08 and C09. Main finding: going upstream pays for magnets, bearings and assembled boards (the GPS board saves the most), and does not pay for complete motors, props, cells or filament pellets.

## Phase 8: the group order (iteration 12, `bee2c60`)

The owner said the IEEE club can run group orders, and asked for the details to go on GitHub and be kept updated. Built: a public group order plan with roles only, a sync tool that keeps generated doc tables equal to the data, and tests that fail when they drift. No supplier has been contacted and no quote exists.

## Phase 9: the record and the vision (iteration 13, 2026-10-24)

The owner asked for everything discussed to be saved for other AI agents, and stated the money stance and the interest in many drones and in making each part, somewhat. Built: [project-context.md](project-context.md), [vision.md](vision.md), [decisions.md](decisions.md) and this history, with consistency updates to older docs.

## Standing instructions from the owner

- Work in plan, do and record cycles, and keep going until told to stop. Each plan goes in [progress.md](progress.md) before the work.
- Report outcomes faithfully. Keep AI assistance visible. Keep the hobby and learning framing.
- Keep the repo public and free of personal data.
- Do not ask for money on the owner's behalf.
