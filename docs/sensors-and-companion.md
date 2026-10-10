# Sensors and companion device

## Idea

The drone does the seeing. A small companion device the rider carries (a "tag") adds positions the drone cannot see. The two sides vote, and each vote is weighted by how trustworthy it is right now. A single source is never enough on its own, which is the point of the council.

## Companion (rider) options, cheapest first

**Owner decision:** a dedicated tag and the phone app, together. Other options stay as evaluations, not purchases. Tiers and costs are in [companion-tiers.md](companion-tiers.md). Prices are in [parts-catalog.md](parts-catalog.md), from searches on 2026-10-10, and need checking at the seller.

- **Phone app.** Uses the phone's own GNSS, IMU and Wi-Fi. Zero extra hardware, since the phone is already owned. Needs a link to the drone (the drone's Wi-Fi access point is the simplest option). Good for early tests.
- **BLE beacon on an ESP32-class board.** Broadcasts so the drone can estimate range from RSSI. Very noisy, but cheap and useful as a sanity check.
- **GNSS module with a radio.** A repurposed GNSS module plus a small radio (for example a LoRa-class module) sends the rider's position. Needs an antenna and a battery plan.
- **UWB tags.** Much better ranging, usually more expensive. Later option, only if the budget allows.

## Drone sensors

- Camera with a person detector. Needs a fixed, known field of view for the geometry to work.
- Time-of-flight or ultrasonic for close range (useful below about 2 m).
- IMU and compass for heading. Needed to turn GNSS offsets into the body frame.
- Radar or lidar: later, if weight and power allow.

## Camera geometry (used in code)

With the person's height H, field of view vertical angle v, and a normalized box height h (fraction of frame height):

- range ≈ H / (2 · h · tan(v/2))
- bearing ≈ (0.5 − cx) · horizontal field of view (positive = left)

Both are small-angle approximations. They assume a level camera, no lens distortion, and a person standing upright.

## Repurposing and low-cost parts

Parts can be sourced individually or made. Ideas to evaluate:

- Salvaged phones, action cameras, GNSS modules and cellular modules.
- 3D-printed frames, mounts and enclosures (materials and print settings to be tested).
- Motors, ESCs, batteries, wiring and propellers bought as separate pieces.

Safety: lithium batteries and motors need proper handling, charging, and protection. Do not charge or store packs unattended, and check the cell type and charger before use.
