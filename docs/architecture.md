# Architecture (draft v0)

Goal: keep one rider in frame across varied conditions, on a low budget, by combining several imperfect sensors instead of relying on one. This is a hobby project and everything here is a design, not a tested system.

## Principles

- **No single sensor is trusted.** Each source gives a position estimate with an uncertainty and a reliability weight.
- **Disagreement is information.** Outlying estimates are rejected, not averaged in.
- **Context changes trust.** Weather, link quality, GNSS quality and known places adjust each source's weight ("attention").
- **Known trouble spots are programmed.** Places with known sensor problems are stored as profiles and applied when the rider is approaching, using GPS and heading.
- **Failure degrades gracefully.** Tracking, then degraded tracking, then dead reckoning, then hold, then a return-home request. Each step is a mode, not a crash.
- **Simulation first, hardware last.** No flight adapter exists until the logic passes simulated tests.

## Frames and units

- Rider and target estimates are in meters in the **drone body frame**: +x forward, +y left.
- Commands are normalized to [-1, 1] (yaw, forward, climb). A later adapter maps them to real limits set on the autopilot.

## Per-tick pipeline

1. **Sense.** Each source produces a `Reading`: an `Estimate` (x, y, variance), a source name, and the measurement's age. A source slower than the loop, such as a phone's 1 Hz fix, repeats its last measurement with a growing age.
2. **Context.** Weather cache, companion link quality, GNSS quality and active place profiles produce per-source attention multipliers.
3. **Fuse.** Readings are scaled by attention, outliers are gated against a robust median reference, and the rest are combined by inverse-variance weighting. The result is one `Estimate`, or `None` when the sources do not agree. Fusion also reports the gate centre and which readings it kept, rejected or found switched off. The replay tool writes this into a trace (`--json`) for the website's replay viewer.
4. **Mode.** A small state machine picks TRACKING, DEGRADED, DEAD_RECKONING, HOLD or RETURN_HOME_REQUESTED, plus a gain scale. Losses are timed in seconds.
4b. **Motion.** When the caller gives the drone's pose in a local frame (from the autopilot, or the simulation), a constant-velocity Kalman filter estimates the rider's velocity over the ground. Each measurement is used once, at the time it was taken. Without a pose there is no motion estimate, and nothing else changes.
5. **Control.** The `FollowController` turns the estimate into commands, scaled by the mode. When there is a motion estimate, the rider's speed along the drone's nose is fed forward into the forward command. The added share shrinks when the speed is uncertain, and its approaching part fades out across the follow band.
6. **Act (later).** Commands go to the autopilot only after SITL tests pass.

## Sources (planned)

| Source | Gives | Good at | Weak at |
|---|---|---|---|
| Camera person detector | bearing and range from the box | cheap, rich | rain, fog, glare, wind vibration |
| Companion GNSS (rider device) | rider position | works out of camera view | meter-level error, needs a radio or cellular link |
| Companion BLE RSSI | range only | cheap, works partly occluded | noisy, multipath |
| Drone ToF or ultrasonic | near range | close-in precision | short range |
| Drone IMU and compass | own heading and motion | fills short gaps | drifts |
| Radar or lidar (later) | range and bearing | robust to light and weather | cost, power, weight |

## Context ("attention")

- **Weather.** Rain or fog lowers camera weight. High wind lowers camera weight (vibration). Weather is queried on a timer and cached, never per frame.
- **Link and GNSS quality.** A weak link lowers companion weights. Poor rider GNSS fix lowers companion GNSS weight.
- **Places.** A profile can multiply any source's weight for a given location (for example, "camera unreliable at this shed").
- Multipliers are clamped and never negative. Unknown weather uses a conservative camera multiplier.

## Place profiles

- A place is a lat/lon with a radius and optional attention overrides and a note.
- A place is **approaching** when the rider is inside it, or within a lookahead distance and roughly in the direction of travel.
- Places are stored in a local JSON file outside this repo (see [privacy-and-rules.md](privacy-and-rules.md)). The repo only ships a fake example.

## Mode machine

- Estimate present and variance under the threshold: TRACKING.
- Estimate present but variance high: DEGRADED (gain scaled down).
- No estimate for a short time: DEAD_RECKONING (gain 0, the caller may hold the last command).
- Longer loss: HOLD (gain 0).
- Longer still: RETURN_HOME_REQUESTED. The mission layer decides whether to latch it.

## Out of scope for now

- Real flight, MAVLink or MAVSDK control.
- Detection and tracking models (the camera source currently consumes already-produced boxes).
- Any cloud service. Everything runs locally.
