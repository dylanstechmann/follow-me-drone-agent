# Vision: build the drones, and the software, from the parts up

This is the owner's stated direction, recorded on 2026-10-24. It is a curiosity and a direction for choosing between options. It is not a plan of record: no fleet size, no revenue plan and no product plan has been given. Agents should read it, use it to weigh options, and not turn it into commitments.

## What the owner said

In the owner's words, paraphrased closely:

- The owner does not like asking for money.
- The owner is curious about getting tons of drones, and about the software that may power them.
- The owner wants to get each and every part themselves, somewhat, rather than using off-the-shelf components.
- The owner expects that process to bring more control, power, money, understanding and capabilities.

Earlier statements point the same way (2026-10-10): own the whole pipeline; do not depend on suppliers or pay their markup; find out how to make the chips, lithium cells, autopilot, GPS, ESC, transmitter, motors, steel core, ESP32 and LoRa chip; get closer to the supply side, the factory, the fab and the lab; and use the IEEE club for group orders. The word "somewhat" matters: this is not an all-or-nothing rule, and the repo already decides case by case what to make and what to buy ([pipeline.md](pipeline.md), [make-own-ladder.md](make-own-ladder.md)).

## How agents should read it

This is the agent's reading of the owner's words. The owner can correct it.

| Owner's word | Working reading | What the repo has so far | Caution |
|---|---|---|---|
| Control | Hold the design files (CAD, PCB, firmware, BOM). Have two sources for each bought part. Be able to repair, modify and replace without anyone's permission. | A rule to keep design files in the repo, a dependency check that flags single-supplier parts, an open-source software stack. | No hardware exists yet. No design file exists beyond plans. |
| Power | Independence from any single supplier, price change or product decision. Leverage from ordering at factory minimums. Freedom to decide what the drones do. | A supply-side model with minimum orders and cash needed, and a group order plan. | No supplier has been contacted. No order has been placed. |
| Money | Lower cost per drone, and less exposure to retail markup. The owner did not describe an income plan. | A cost model. On paper, the modelled core cost per drone falls from $558 to $965 (pass 0, retail) to $208 to $534 (pass 10, factory-assembled own designs), about 45 to 63 percent lower. | These are estimates with many placeholders. They leave out labour, tooling, failed builds, crashes, rework, duty and the cash tied up in minimum orders. They are not a business case. |
| Understanding | Learn how each part works by specifying it, building it and measuring it. | Plans for thrust testing, bring-up checklists and coupon tests. | Nothing has been measured yet. |
| Capabilities | Make variants, such as custom tags, sensors and motors, and write the software that drives them. | A tested software core and a replay tool, run on synthetic data. | Nothing has flown, and nothing has been tested on hardware. |

## Money stance

The owner does not like asking for money. Agents must follow this:

- Do not draft funding requests, sponsorship pitches, grant applications, crowdfunding pages or donation asks, unless the owner asks for one.
- Earlier docs mention that FAU or the IEEE club might fund the project. That is optional and not part of the plan. The owner may never use it.
- Group orders are cost-sharing. Each member pays for the parts they receive. They are not fundraising.
- Asking a lab for tool time, advice or access is not asking for money, and it is still the owner's call.

Routes that need no outside money:

1. Build in stages. The bench kit with a made tag fits $100 on paper (pass 5: $63.87 to $98.99). Flying hardware waits until the bench results justify it.
2. Use what is already owned or freely available: the owner's phone, the printers at FAU's engineering building and the IEEE club.
3. Salvage parts, and buy used.
4. Share the cost of factory minimums through group orders.
5. Do the work in simulation first. It costs nothing.
6. Wait for price drops, and re-check prices before buying.

How the first flying drone gets paid for is an open question. The model shows the flying hardware does not fit in $100 under any pass, and the owner has not said how it would be funded.

## The fleet question

The owner is curious about "tons" of drones. No number has been given.

What a larger number changes, according to the cost model:

- Fixed costs spread out. One order of 1,000 magnets covers about 17 drones. One order of 1,000 stator cores covers about 250. Per-design PCB and assembly fees fall per board.
- Cash to start rises. Factory stator cores raise the cash at minimum orders from $332 to $960 (pass 10) to $1,320 to $2,943 (pass 11).
- Quality control matters more. Every factory part needs an inspection step, and the inspection results feed back into the cost model.
- The cost per drone at 1, 5, 20, 100 and 500 drones is a generated table in [cost-reduction.md](cost-reduction.md). It is for exploring, not a plan.

What a larger number changes for the software. These are ideas, none are built:

- A record for each drone: serial number, registration, firmware version, calibration, build date, parts and their batches.
- Logs and replay for every flight, so a failure on one drone can be reproduced.
- Simulation regression tests that run on every software change.
- Battery and maintenance tracking, and geofence and mission management.
- Build, test and inspection traceability, from a batch of magnets to the drone it went into.

A proposed staging, which the owner has not confirmed:

1. **One drone.** Gates 1 to 6 in [build-plan.md](build-plan.md).
2. **A few drones** built from the same design, using group-order parts.
3. **More,** only after the build, test and inspect process is repeatable, failures are counted, and the legal checks below are done.

Safety and legal topics to verify before scaling. This is not legal advice:

- In the US, drones over 250 g generally need FAA registration and Remote ID, and each drone is its own case.
- Commercial use, flying over people, and operating several drones at once have their own rules.
- Campus rules may limit flying near FAU.
- A radio the owner builds, such as a transmitter, must meet the radio rules for its band and power.
- Importing parts has duty and customs rules ([supply-side.md](supply-side.md)).
- Storing, charging and shipping many lithium packs is a fire and transport risk. Magnets are a pinch and shatter risk.

## Principles

1. **Own the capability, not every process.** Hold the design, be able to make the part or get it made from two sources, and be able to swap a supplier in about a week.
2. **Evidence over aspiration.** Every price carries its date. Unknowns are labelled. Claims are checked against sources.
3. **Safety gates before flight.** No flight code without simulation tests, and no flight without review.
4. **Hobby and learning.** Public text keeps that framing, and the AI assistance stays visible.
5. **Privacy.** The repository is public. Names, contact details, addresses and payment records stay out.
6. **Make where it pays.** Buy where the supplier's premium is small or the risk is high: props, lithium cells, flight packs and complete motors.

## Where the evidence is weak

- Only 10 of 51 sourced prices are dated within 12 months of the 2026-10-10 cutoff, and 16 inputs are placeholders ([price-audit.md](price-audit.md)).
- The largest open price is the ESC power MOSFET.
- Nothing has been built, measured, ordered or flown.
- Labour time, tooling, failures and crashes are not costed.
- Factory part quality is unknown until samples arrive.
- The 2026 duty rate on factory orders is uncertain.
- The savings could shrink or vanish once failures and rework are included.

## Open questions for the owner

1. What does "tons" mean here: 5, 50 or 500?
2. What would count as success: one reliable follow-me drone, a repeatable build, a fleet, or something else?
3. Is the aim personal use and learning, or might drones or software eventually be sold? Selling raises extra legal and product requirements. Nothing here assumes it.
4. How should the first flying drone be paid for, without asking for money?
5. Which parts should be made first?
