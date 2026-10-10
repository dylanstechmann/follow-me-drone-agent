# Build plan (low budget, one part at a time)

Budget: $100 total (see [budget.md](budget.md)). Build in gates. A later gate starts only when the earlier one passes.

## Gates

1. **Software core (no hardware).** Fusion, context, places, mode machine, companion GNSS for a phone and a tag, replay tool, and a priced parts catalog with cost passes. All tested (119 tests). Current stage.
2. **Replay.** Feed recorded or synthetic sensor logs through the core. Measure how it behaves when sources fail or disagree.
3. **SITL.** Run the follow logic against a PX4 or ArduPilot simulated drone. No real hardware.
4. **Bench.** Test sensors and the companion on a desk. Motors off, props removed.
5. **Tethered or caged.** Only after the bench passes and with a human safety pilot. Not planned for v0.
6. **Free flight.** Out of scope until gates 1 to 5 pass and the rules in [privacy-and-rules.md](privacy-and-rules.md) are checked.

## Hardware path (to be decided, not purchased)

- Start with the companions the owner chose: the phone app (already owned, $0) and one tag (about $27 to $52 of parts, see [parts-catalog.md](parts-catalog.md)).
- Then the bench kit from pass 3 in [cost-reduction.md](cost-reduction.md): a Pi Zero 2 W, a camera, the tag, and filament. It fits $100 at low prices. It collects real logs for gate 2.
- Frame and drone parts only after gate 2 has data to justify them. Prototype frames can be printed in PETG first, following [3d-printing.md](3d-printing.md).
- A flying drone does not fit in $100 with any pass so far. See the findings in [cost-reduction.md](cost-reduction.md).
