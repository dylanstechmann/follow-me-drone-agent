# Companion tiers

## Decision

The owner's choice: a dedicated tag and the phone app together. Other devices are added only when they earn their place.

Why both:

- **Two receivers, independent errors.** The phone and the tag each report a rider position. If they agree, the council gets more confidence. If one drifts, the gate can reject it.
- **Different strengths.** The phone already has a camera, an IMU, Wi-Fi and a battery you charge anyway. The tag is cheap, has its own battery and a long-range link, and keeps working when the phone is in a pocket, out of signal, or dead.
- **Failure cover.** If the phone app crashes, the tag still reports. If the tag's battery dies, the phone still reports.

## Tier costs

From [parts-catalog.md](parts-catalog.md). The retail tag (pass 0) is about $32 to $51 of parts. The made tag (pass 5, bulk chip and outsourced board) is about $29 to $49. The phone is $0 because you already own it.

| Tier | What it adds | Cost (USD, low to high) |
|---|---|---|
| 0 | Phone only | $0 |
| 1 | Phone and one tag | $32.31 to $51.09 retail; $28.82 to $48.55 made |
| 2 | Phone and two tags | $64.62 to $102.18 retail; $57.64 to $97.10 made |
| 3 | Plus wearable IMUs | Not priced. The IMU boards are unpriced in the catalog. |

With retail tags, tier 2 exceeds the whole $100 budget at the high end. With made tags it fits, just. Tier 3 is outside the budget until it is priced.

The Pixel 8a is not a rider companion. It is a drone computer candidate (pass 4). The owner's existing phone is the rider's companion.

## Earning a place

A device is added only when all three hold:

1. **It improves a measured result.** A replay log or bench run shows lower tracking error, fewer dropouts, or both. A guess does not count.
2. **Its cost is worth it.** The parts cost, the charging, the pairing, and the time to maintain it are counted, not just the price.
3. **It is safe on a board.** It adds no snag point, no weight that changes how the rider falls, and no battery against the body without a plan.

If a device fails any of these, it stays out. The default for every new device is no.

## The motion-capture-suit question

A full-body suit of IMUs is possible, but it has to earn its place like everything else. The likely value is predicting the rider's motion, such as a lean into a turn, a little before the drone's sensors see it.

Order of tests:

1. Check what the phone's own IMU already gives. The phone is already on the rider.
2. Add one wearable and see whether the prediction improves the replay result.
3. Only then consider more. Each extra unit adds charging, pairing, a failure point and a cost. Set the limit from bench results and the rider's comfort, not from what is possible.

Start with zero extra wearables beyond the tag and the phone.

## Safety on the board

- Nothing loose or dangling. Clip the tag flat in a pocket or on a strap that can break away.
- Keep batteries off the body unless there is a plan for a fall, and keep them away from heat.
- Keep the phone out of the path of a fall. A cracked screen or a sharp edge can cut.
- The rider's safety comes before the drone's data. A device that makes a fall worse is not worth any tracking gain.
- Skate only where it is safe. Traffic, people and uneven ground matter more than any sensor.

## Other checks before using a tag

- **Link.** Version 0 of the tag uses the ESP32's Wi-Fi to reach the drone's access point, not LoRa. Measure Wi-Fi range and dropouts in the field. If they are not good enough, LoRa comes back, and its frequency variant must match your country (915 MHz in the US).
- **Range.** Measure the link range in the field, not on the bench. Do not assume the range on a datasheet.
- **Battery life.** Measure it with the real GNSS and radio load. Plan charging around it.
- **Consent.** The rider is the owner. Anyone else who wears a tag or is tracked must agree first. See [privacy-and-rules.md](privacy-and-rules.md).
