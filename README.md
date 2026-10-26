# follow-me-drone-agent

A personal hobby and learning project: a drone that follows a skater (pennyboarding) and records footage. Today it is a planning and modelling repo. There is no flight code, and nothing has flown.

## Start here

- **AI agents:** read [AGENTS.md](AGENTS.md) for the rules, then [docs/project-context.md](docs/project-context.md) for what exists, what is only a plan, and how to continue.
- **Why this exists and where it is going:** [docs/vision.md](docs/vision.md).
- **What was decided, and what was corrected:** [docs/decisions.md](docs/decisions.md).
- **What was discussed and done, in order:** [docs/history.md](docs/history.md).
- **The website:** https://dylanstechmann.github.io/follow-me-drone-agent/, a replay viewer, a cost explorer and printable parts in 3D, built from this repo's data and published by GitHub Actions ([docs/website.md](docs/website.md)).

## Direction

The owner's stated direction (2026-10-24): to be curious about building many drones, and the software that may power them, by getting each part themselves, somewhat, instead of using off-the-shelf components. The owner expects that to bring more control, power, money, understanding and capabilities. This is a direction for choosing between options, not a plan of record. See [docs/vision.md](docs/vision.md).

The owner does not like asking for money. Nothing in the plan depends on outside funding.

## Status

- **Built and tested (standard-library Python plus pytest):** the follow controller, fusion of several position sources, weather and place-based weights, a mode machine that falls back when sensors drop out, companion GNSS for a phone and a tag, a replay tool, and a data-driven cost and supply model with a dependency check and costs for any number of drones. These run on recorded or synthetic data only. A website shows the replay and the costs in the browser.
- **Planned and documented:** the routes to make each part ([docs/make-own-ladder.md](docs/make-own-ladder.md)), the factory and lab routes ([docs/supply-side.md](docs/supply-side.md)), and a public IEEE group order plan ([docs/group-order.md](docs/group-order.md)) that nobody has acted on yet.
- **Designed, not printed:** four printable parts as adjustable OpenSCAD models (test bars, a hole-size gauge, a thrust-stand jig and the tag case), shown in 3D on the website. None has been printed or tested.
- **Not built:** person detection and tracking, the simulator bridge, any flight adapter, and any PCB or firmware file.
- **Never done:** flying, building or testing hardware, contacting a supplier, or placing an order.
- Do not use this code to fly anything near people until the safety plan in [docs/safety.md](docs/safety.md) is met.

## Budget

The working budget is $100 for the bench and pipeline work, so simulation comes first. The cost passes in [docs/cost-reduction.md](docs/cost-reduction.md) show on paper that a bench kit with a made tag fits $100, and that a flying drone does not. Prices carry their own dates, and most are older than 12 months or undated ([docs/price-audit.md](docs/price-audit.md)). See [docs/budget.md](docs/budget.md) and [docs/pipeline.md](docs/pipeline.md).

## Planned scope

- Person tracking from a camera feed, so the drone keeps the rider in frame.
- Follow-distance and framing control, with the rider as the target.
- Simulation first (PX4 or ArduPilot SITL) before any real flight.
- A logging path that keeps flight and footage metadata for review.

## Development

The code is Python 3.10 or later with pytest only. Run `python3 -m pytest`. Docker Compose and uv, which the owner's other repos use, are planned and not added yet. Tables in the docs are generated from the data under `bom/`: run `PYTHONPATH=src python3 -m follow_me.docs_sync` after changing it. Build the website with `PYTHONPATH=src python3 -m follow_me.website` and preview it with `python3 -m http.server -d _site 8000`. The commands are in [docs/project-context.md](docs/project-context.md).

## How this was built

This is an AI-assisted hobby project. All the code, tests, docs, part models and the website so far were written by AI coding agents (Claude Code, with several assistant models over the sessions) at the owner's direction. The owner supplied the direction, the decisions and the real-world facts: the budget, access to 3D printers, that the IEEE club can run group orders, and the preference not to ask for money. No review of the code by the owner is recorded.

The agents ran the web research. Search snippets and fetched pages are not verified, and the prices and licence notes drawn from them are provisional. Design research draws on public PX4, ArduPilot and MAVSDK documentation. The website uses three.js and a WebAssembly build of OpenSCAD. Sources are in [docs/references.md](docs/references.md).

## License

MIT, see [LICENSE](LICENSE). It covers this repo's contents. The website's build downloads three.js (MIT) and an unmodified WebAssembly build of OpenSCAD (GPL-2.0-or-later) from the npm registry. Neither is stored in this repo, and the site serves each with its own licence file.
