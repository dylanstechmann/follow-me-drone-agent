# Safety plan (draft)

Nothing in this project may fly until every item below is checked off.

1. Simulation: the follow logic runs in PX4 or ArduPilot SITL with no real hardware attached.
2. Geofence: a hard boundary and altitude cap, enforced by the autopilot, not by this code alone.
3. Kill path: a manual override that always wins, tested in SITL and on the bench.
4. Bystanders: no flights over people, roads, or the skate area. Respect local drone rules and no-fly zones. No flights on FAU property without FAU's approval, and check controlled airspace first (see [privacy-and-rules.md](privacy-and-rules.md)).
5. Consent: the rider agrees to being tracked and filmed. Footage stays on the owner's device unless the rider agrees otherwise.
6. Review: a human reviews every hardware-facing change before flight.
