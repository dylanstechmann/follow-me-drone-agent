# History: what was discussed and done

A plain account for agents and for the owner. It follows the order of events. The first fifteen commits were all made on 2026-10-10, in one long working session. The vision and this record were added on 2026-10-24.

## Who did what

- **The owner** gave the direction and the decisions, and supplied facts only the owner knows: the $100 budget, access to 3D printers at FAU's engineering building and the IEEE club, that the IEEE club can run group orders, the purchase of a used Pixel 8a for $250, the preference not to ask for money, and the interest in building many drones.
- **AI coding agents** (Claude Code) wrote all the code, tests and docs, ran the web research, and did the calculations. The assistant model changed over the session: the commit trailers show Claude Haiku 5.5 for the first thirteen commits, Claude Opus 5.5 for one, and Claude Sonnet 5.5 for one.
- **Not done by anyone yet:** building or testing any hardware, contacting any supplier, ordering anything, reading the licence files, visiting a lab, running a flight, printing a part, or opening a PCB file. The only CAD files are the four OpenSCAD parts an agent wrote and rendered on 2026-10-26. No review of the code by the owner is recorded.

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

## Phase 10: a website, printable parts and new facts (iterations 16 to 20, 2026-10-26)

The owner asked what else could be done for the repo: visualizations and easy dashboards, 3D, databases, AI models, and a website on GitHub Pages where the 3D runs in the visitor's browser, with heavy work on the owner's laptop or a cloud sandbox if needed. The owner added that they can use the printers in FAU's engineering building and can work with a drone club. The agent proposed a menu and a first batch, and the owner said "ok".

- **Iteration 16:** an agent web search found that FAU's safety office prohibits recreational drone use on university property, and that the Boca Raton campus borders Boca Raton Airport's Class D airspace. Both are recorded as rules to confirm. The drone club is recorded as owner-reported, because the search found no university-level FAU drone club. Found C13: the replay example did not reach the modes the progress log said it did. The example now walks every mode at default settings.
- **Iteration 17:** found C14, the cash at minimum orders leaving out the waste allowance, and fixed it. Added the cost per drone for any number of drones, with the PCB assembly fees paid once per order. It is for exploring; the owner has not set a number.
- **Iteration 18:** built the website: an overview, a replay viewer and a cost explorer, built from the repo's data by `follow_me.website` and published by a GitHub Actions workflow. Fusion now reports its gate decisions, and the replay tool writes them into a JSON trace. The agent checked every page in a headless browser at desktop and phone widths, in light and dark themes.
- **Iteration 19:** wrote four printable parts as adjustable OpenSCAD models (test bars, a hole-size gauge, a thrust-stand jig and the tag case) with print cards, and a parts page that shows them in 3D and re-renders them in the browser. OpenSCAD's WebAssembly build made this possible without installing anything, and its Manifold engine renders a part in about 0.15 s. Nothing has been printed.
- **Iteration 20:** the owner asked what to do next and said "ok" to the agent's recommendation. With that agreement, the agent added the MIT licence, updated the workflow's GitHub actions to current versions, turned on GitHub Pages and pushed iterations 16 to 20. The first workflow run passed and published the site at https://dylanstechmann.github.io/follow-me-drone-agent/, and the agent checked the live pages in a headless browser. The agreed next steps: the owner prints the hole-size gauge and the test bars, then a batch that runs the owner's own phone recording through the council, then a camera batch.

## Phase 11: the owner's own recording through the council (iterations 21 to 24, 2026-10-26)

The owner asked whether anything else could be done before going to the printers. The agent listed what to bring and record, and started the phone-data batch the owner had agreed to, which does not depend on the prints.

- **Iteration 21:** a kinematic follow simulation, a point drone flown by the council's commands. It is not a flight simulator. It found that the drone trails a moving rider (the controller has no feed-forward of the rider's speed), that its forward command tops out at 0.6, and that a phone fix alone (4 m) is degraded on every tick, which halves the speed.
- **Iteration 22:** the mode machine's fallbacks are timed in seconds, not ticks, checked at several loop rates in the simulation.
- **Iteration 23:** a GPX importer that keeps only meters and seconds from the first fix. Reading the apps' code showed that `hdop` means different things in GPSLogger and OsmAnd.
- **Iteration 24:** the replay page runs the same Python in the visitor's browser with Pyodide, so a recording can be simulated without uploading it. It also shows a made-up simulated ride, with the distance to the rider over time and a top-down view of both paths.

## Phase 12: the simulated drone keeps up (iterations 26 to 28, 2026-10-26)

The owner asked what else could be done before work away from the computer. The agent recommended fixing the follow logic the simulation had exposed, then the camera batch, then two-phone support, and started the first.

- **Iteration 26:** a Kalman filter estimates the rider's velocity over the ground from the fused estimates and the drone's pose. Readings now carry their measurement's age, so a 1 Hz phone fix on a 2 Hz loop is used once.
- **Iteration 27:** the rider's speed is fed forward into the forward command. In simulation, riders at 2 to 7 m/s are followed 6 to 10 m behind instead of 8 to 31 m. A sudden stop brought the drone within 2 m, so the approaching part now fades out across the follow band (3.4 m). The simulation also found that 3 m noisy fixes bring the drone within 0.3 to 1.8 m of a standing rider, with or without the change. That is recorded as open.
- **Iteration 28:** the website shows the made-up ride with the new controller and the old one side by side, and the replay panel shows the rider's estimated speed and how much of it was fed forward.

## Standing instructions from the owner

- Work in plan, do and record cycles, and keep going until told to stop. Each plan goes in [progress.md](progress.md) before the work.
- Report outcomes faithfully. Keep AI assistance visible. Keep the hobby and learning framing.
- Keep the repo public and free of personal data.
- Do not ask for money on the owner's behalf.
