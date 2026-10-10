# follow-me-drone-agent

A personal hobby and learning project: a drone that follows a skater (pennyboarding) and records footage. Right now it is a planning skeleton. There is no flight code yet.

## Status

- The follow controller exists: a pure-Python module that turns a person's box in the frame into yaw, forward and climb commands. It has unit tests (`python3 -m pytest`) and no hardware dependency.
- Also built: fusion of several sources, weather and place-based weights, a mode machine that falls back when sensors drop out, companion GNSS for a phone and a tag, a replay tool, and a cost model built from raw materials, with cost passes and a supplier-dependency check. These run on recorded or synthetic data only. Run `python3 -m pytest` (184 tests). The routes to make each part, with price dates, are in [docs/make-own-ladder.md](docs/make-own-ladder.md). Factory, minimum-order and lab routes are in [docs/supply-side.md](docs/supply-side.md). The IEEE group order plan, kept current from [bom/group_order.json](bom/group_order.json), is in [docs/group-order.md](docs/group-order.md).
- Not built yet: person detection and tracking, the simulator bridge, and any flight adapter.
- Nothing here has flown, and nothing here has been tested against hardware.
- Do not use this code to fly anything near people until the safety plan in [docs/safety.md](docs/safety.md) is met.

## Budget and funding

The working budget is $100 for the bench and pipeline work, so most of the software is written from scratch and simulation comes first. See [docs/budget.md](docs/budget.md). The cost passes in [docs/cost-reduction.md](docs/cost-reduction.md) show that a bench kit with a made tag fits $100 at both ends, but a flying drone does not. [docs/pipeline.md](docs/pipeline.md) explains what the owner can make and what must be bought. Prices are in [docs/parts-catalog.md](docs/parts-catalog.md). FAU's engineering building and the IEEE club have 3D printers ([docs/lab-access.md](docs/lab-access.md)). FAU / FAU IEEE funding is a possible source; this is not confirmed.

## Planned scope

- Person tracking from a camera feed, so the drone keeps the rider in frame.
- Follow-distance and framing control, with the rider as the target.
- Simulation first (PX4 or ArduPilot SITL) before any real flight.
- A logging path that keeps flight and footage metadata for review.

## Development

So far the code is pure Python 3.10+ with pytest only (`python3 -m pytest`). Docker Compose and uv, which the owner's other repos use, are planned but not added yet. Rules for coding agents are in [AGENTS.md](AGENTS.md).

## How this was built

This is an AI-assisted hobby project. Code and docs are drafted with coding agents (Claude Code) and reviewed by the owner. Agent-generated analyses are labelled as such. Design research draws on public PX4, ArduPilot, and MAVSDK documentation; links will be added to [docs/references.md](docs/references.md) as they are used.

## License

See [LICENSE](LICENSE) once added.
