# Companion tiers

## Decision

The owner's choice: a dedicated tag and the phone app together. Other devices are added only when they earn their place.

Why both:

- **Two receivers, independent errors.** The phone and the tag each report a rider position. If they agree, the council gets more confidence. If one drifts, the gate can reject it.
- **Different strengths.** The phone already has a camera, an IMU, Wi-Fi and a battery you charge anyway. The tag is cheap, has its own battery and a long-range link, and keeps working when the phone is in a pocket, out of signal, or dead.
- **Failure cover.** If the phone app crashes, the tag still reports. If the tag's battery dies, the phone still reports.

## Tier costs

From [parts-catalog.md](parts-catalog.md), tag cost from pass 0. The tag is about $27 to $52 of parts. The phone is $0 because you already own it.

| Tier | What it adds | Cost (USD, low to high) |
|---|---|---|
| 0 | Phone only | $0 |
| 1 | Phone and one tag | $27.39 to $52.04 |
| 2 | Phone and two tags | $54.78 to $104.08 |
| 3 | Plus wearable IMUs | Not priced. The IMU boards are unpriced in the catalog. |

At the high end, tier 2 alone exceeds the whole $100 budget. Tier 3 is outside the budget until it is priced.

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

- **Frequency variant.** LoRa modules differ by region. The Heltec HT-CT62 needs the variant for your country (915 MHz in the US). Check before buying.
- **Range.** Measure the link range in the field, not on the bench. Do not assume the range on a datasheet.
- **Battery life.** Measure it with the real GNSS and radio load. Plan charging around it.
- **Consent.** The rider is the owner. Anyone else who wears a tag or is tracked must agree first. See [privacy-and-rules.md](privacy-and-rules.md).
