# follow-me-drone-agent

A personal hobby and learning project: a drone that follows a skater (pennyboarding) and records footage. Right now it is a planning skeleton. There is no flight code yet.

## Status

- The follow controller exists: a pure-Python module that turns a person's box in the frame into yaw, forward and climb commands. It has unit tests (`python3 -m pytest`) and no hardware dependency.
- Also built: fusion of several sources, weather and place-based weights, a mode machine that falls back when sensors drop out, companion GNSS for a phone and a tag, a replay tool, and a priced parts catalog with cost passes. These run on recorded or synthetic data only. Run `python3 -m pytest` (119 tests).
- Not built yet: person detection and tracking, the simulator bridge, and any flight adapter.
- Nothing here has flown, and nothing here has been tested against hardware.
- Do not use this code to fly anything near people until the safety plan in [docs/safety.md](docs/safety.md) is met.

## Budget and funding

The working budget is $100, so most of the software is written from scratch and simulation comes first. See [docs/budget.md](docs/budget.md). The cost passes in [docs/cost-reduction.md](docs/cost-reduction.md) show that a bench kit fits $100 at low prices, but a flying drone does not. Prices are in [docs/parts-catalog.md](docs/parts-catalog.md). FAU / FAU IEEE is a possible funding source; this is not confirmed.

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
