# Build plan (low budget, one part at a time)

Budget: $100 total (see [budget.md](budget.md)). Build in gates. A later gate starts only when the earlier one passes.

## Gates

1. **Software core (no hardware).** Fusion, context, places, mode machine, all tested. Current stage.
2. **Replay.** Feed recorded or synthetic sensor logs through the core. Measure how it behaves when sources fail or disagree.
3. **SITL.** Run the follow logic against a PX4 or ArduPilot simulated drone. No real hardware.
4. **Bench.** Test sensors and the companion on a desk. Motors off, props removed.
5. **Tethered or caged.** Only after the bench passes and with a human safety pilot. Not planned for v0.
6. **Free flight.** Out of scope until gates 1 to 5 pass and the rules in [privacy-and-rules.md](privacy-and-rules.md) are checked.

## Hardware path (to be decided, not purchased)

- Start with the companion (phone app), since it costs nothing.
- Then a cheap sensor test rig on the bench, to collect real logs for gate 2.
- Frame and drone parts only after gate 2 has data to justify them. Prototype frames can be 3D printed in cheap material first.
