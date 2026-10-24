# IEEE group order

A shared plan for buying the parts that only make sense in bulk: factory magnets and bearings, assembled boards, and later stator cores. The owner reports that the IEEE club can run group orders. That has not been confirmed with the club's officers.

Nothing here has been ordered. No supplier has been contacted, and no quote exists yet. Every price below is a listing, an estimate or a placeholder until a supplier quote replaces it.

A group order is cost-sharing: each member pays for the parts they receive. It is not fundraising, and nobody is asked for a donation.

## Privacy

This repository is public. The plan uses roles only. Never add names, email addresses, phone numbers, delivery addresses, payment records, or screenshots of orders or invoices. Keep those in the club's private channel. A test scans the plan and this page for email-like text.

## How to keep it current

1. Edit [bom/group_order.json](../bom/group_order.json): change a line's `state`, its `order_qty`, add a `quote`, answer an open decision, and set `last_updated`.
2. Run `PYTHONPATH=src python3 -m follow_me.docs_sync` to rewrite the tables below.
3. Run `python3 -m pytest`. The suite fails if a generated table is stale.
4. Commit and push.

To record a supplier quote, add this to the line, and set its state to `quoted`:

```json
"quote": {"low": 0.05, "high": 0.05, "checked": "2026-11-02", "ref": "supplier quote 1, delivered, duty paid"}
```

Prices for lines that are not yet quoted come from [materials.json](../bom/materials.json) and [catalog.json](../bom/catalog.json), so a change there moves this plan.

## Current plan

<!-- generated:group_order:start -->
**Plan status:** draft. **Last updated:** 2026-10-10. **Lines:** 14 (7 blocked, 7 needs quote). **Supplier quotes in hand:** 0 of 14.

### Totals

| Scope | Cash low (USD) | Cash high (USD) | Per member at 5 (USD) | Per member at 10 (USD) | Per member at 20 (USD) |
|---|---|---|---|---|---|
| Wave 1: Factory parts, ready now | 159.20 | 540.44 | 31.84 to 108.09 | 15.92 to 54.04 | 7.96 to 27.02 |
| Wave 2: Assembled boards, blocked by designs | 576.90 | 1,843.10 | 115.38 to 368.62 | 57.69 to 184.31 | 28.84 to 92.16 |
| Wave 3: Deferred until the lab tests pass | 991.44 | 1,992.09 | 198.29 to 398.42 | 99.14 to 199.21 | 49.57 to 99.60 |
| All lines | 1,727.54 | 4,375.63 | 345.51 to 875.13 | 172.75 to 437.56 | 86.38 to 218.78 |

### Lines

| Wave | Line | Supplier type | Order qty (minimum) | Unit price (USD) | Line total (USD) | Price basis | State | Drones covered |
|---|---|---|---|---|---|---|---|---|
| 1 | N52 disc magnets, 10 x 2 mm: sample from a distributor | distributor | 25 disc (25) | 0.78 | 19.50 | listing, undated | needs quote | 0 |
| 1 | 684ZZ miniature bearings, 4 x 9 x 4 mm: sample from a retailer | retail | 10 bearing (1) | 3.00 to 4.38 | 30.00 to 43.80 | listing, undated | needs quote | 1 |
| 1 | N52 disc magnets, 10 x 2 mm, from a factory | factory | 1000 disc (1000) | 0.020 to 0.10 | 20.00 to 100.00 | listing, undated | needs quote | 17 |
| 1 | 684ZZ miniature bearings, 4 x 9 x 4 mm, from a factory | factory | 100 bearing (100) | 0.16 to 0.88 | 16.00 to 88.00 | listing, undated | needs quote | 12 |
| 1 | Enamelled copper wire, 0.3 mm, 1 kg spools | retail | 2 kg (1) | 11.85 to 44.57 | 23.70 to 89.14 | listing, 2026-03 | needs quote | 12 |
| 1 | Hardened steel motor shafts | retail | 20 shaft (1) | 1.00 to 3.00 | 20.00 to 60.00 | placeholder, undated | needs quote | 5 |
| 1 | Shipping, duty and brokerage allowance, wave 1 | shared | 1 order (1) | 30.00 to 140.00 | 30.00 to 140.00 | placeholder, undated | needs quote | n/a |
| 2 | GNSS board with a bare u-blox M9N, factory-assembled | fab | 10 board (1) | 15.54 to 28.59 | 155.40 to 285.90 | estimate, undated | blocked | 10 |
| 2 | Tag board v2 (CH592 BLE and a clone GNSS module), factory-assembled | fab | 10 board (1) | 7.26 to 16.36 | 72.60 to 163.60 | estimate, undated | blocked | 10 |
| 2 | Autopilot board (STM32H743 and ICM-42688-P), factory-assembled | fab | 10 board (1) | 15.69 to 45.21 | 156.90 to 452.10 | estimate, undated | blocked | 10 |
| 2 | 4-in-1 ESC board (AT32F421 and FD6288Q), factory-assembled | fab | 10 board (1) | 16.20 to 80.15 | 162.00 to 801.50 | estimate, undated | blocked | 10 |
| 2 | Shipping, duty and brokerage allowance, wave 2 | shared | 1 order (1) | 30.00 to 140.00 | 30.00 to 140.00 | placeholder, undated | blocked | n/a |
| 3 | Stator cores, 2207 class, from a factory | factory | 1000 core (1000) | 0.99 to 1.99 | 990.00 to 1,990.00 | listing, undated | blocked | 250 |
| 3 | Electrical steel sheet for etched laminations | retail | 1 kg (1) | 1.44 to 2.09 | 1.44 to 2.09 | listing, 2026-06 | blocked | n/a |

### Blocked lines

- **GNSS board with a bare u-blox M9N, factory-assembled:** No board design exists yet. The KiCad file has not been made.
- **Tag board v2 (CH592 BLE and a clone GNSS module), factory-assembled:** The BLE range and clone-GNSS field tests have not been run.
- **Autopilot board (STM32H743 and ICM-42688-P), factory-assembled:** Needs simulation results and a firmware port plan. The IMU has a 45 to 53 week lead time at some distributors.
- **4-in-1 ESC board (AT32F421 and FD6288Q), factory-assembled:** Needs a bulk MOSFET price and a design review.
- **Shipping, duty and brokerage allowance, wave 2:** Same as the wave 2 boards.
- **Stator cores, 2207 class, from a factory:** The lab lamination etching test comes first. New tooling takes 10 to 12 weeks, and the order needs a drawing.
- **Electrical steel sheet for etched laminations:** Waiting for the etching coupon test. Small lots cost more than the benchmark price.

### Inspection on arrival

- **N52 disc magnets, 10 x 2 mm: sample from a distributor:** Weigh and caliper a few discs. Pull-test one. Check the coating for chips.
- **684ZZ miniature bearings, 4 x 9 x 4 mm: sample from a retailer:** Spin each bearing by hand and listen. Check radial play with a dial gauge if one is available.
- **N52 disc magnets, 10 x 2 mm, from a factory:** Pull-test ten samples from the batch. Check grade marking, coating and magnetization direction against the datasheet. Calipers for size.
- **684ZZ miniature bearings, 4 x 9 x 4 mm, from a factory:** Spin-test every bearing from a sample of twenty. Check radial play and noise. Reject any that stick.
- **Enamelled copper wire, 0.3 mm, 1 kg spools:** Check the diameter with calipers and the enamel with a continuity test.
- **Hardened steel motor shafts:** Check the diameter against the chosen bearing bore, and the straightness on a flat surface.
- **GNSS board with a bare u-blox M9N, factory-assembled:** Power-up check, then a satellite-signal test outdoors against a known-good receiver.
- **Tag board v2 (CH592 BLE and a clone GNSS module), factory-assembled:** Bring-up checklist in docs/pcb-plan.md.
- **Autopilot board (STM32H743 and ICM-42688-P), factory-assembled:** Power-up check, sensor read-back, then bench tests with props off.
- **4-in-1 ESC board (AT32F421 and FD6288Q), factory-assembled:** Low-voltage, current-limited bench test with no motor, then with a motor and no prop.
- **Stator cores, 2207 class, from a factory:** Check flatness, burrs and slot size against the drawing.

### Open decisions

- [ ] Who coordinates the order (a role, such as the club's treasurer or the project lead)?
- [ ] How many members want each line? Collect anonymous counts, then update the lines.
- [ ] Does the club pay and collect later, or do members pay suppliers directly? Ask the officers what the university allows for student-organization purchases.
- [ ] Who is the importer of record, and which delivery address is allowed? Keep the address off GitHub.
- [ ] Request quotes from at least two suppliers per factory line, using the template in docs/group-order.md.
- [ ] Ask the carrier for a delivered-duty-paid quote, and check the duty rate with US Customs before ordering.
- [ ] Who inspects arriving parts, and what are the acceptance tests? The lines list the tests.
- [ ] How are parts split among members, and what happens to leftover stock? Keep the records in the club's private channel.
- [ ] Order the small distributor samples first and build one test motor before the factory order.

### Facts and where they came from

| Fact | Source | Confirmed |
|---|---|---|
| The IEEE club can run group orders. | Owner, 2026-10-10 | no |
| FAU engineering and the IEEE club have 3D printers. | Owner, earlier in this project (date not recorded) | no |
| The US small-parcel duty exemption ended for China in 2025, and sources disagree on the 2026 rate. | Trade guides found 2026-10-10; not checked with US Customs | no |
<!-- generated:group_order:end -->

## How the order runs

1. **Collect interest.** Ask members which lines they want. Keep counts, not names, in the plan. Update `order_qty` to match.
2. **Order samples first.** The wave 1 sample lines cost about $50 to $64. Build one test motor and measure it before committing to the factory order ([motors-plan.md](motors-plan.md)).
3. **Request quotes** from at least two suppliers per factory line, using the template below. Record each quote.
4. **Agree payment and custody** with the club's officers. Ask what the university allows for student-organization purchases and for receiving parcels. Do not assume.
5. **Place the order** only when every line in the wave has a quote and the delivered cost is known.
6. **Inspect on arrival.** Run the tests listed for each line. Record counts and rejects without names.
7. **Split the parts** by agreed rule, and note leftover stock.

## Quote request template

For the magnets. Adapt it for the bearings and the other factory lines.

> Subject: Quote request: N52 disc magnets, 10 x 2 mm, 1,000 pieces
>
> Hello,
>
> We are a student engineering group buying parts for a hobby drone project. Please quote:
>
> - Item: neodymium disc magnet, grade N52, 10 mm diameter, 2 mm thick, axially magnetized
> - Coating: nickel-copper-nickel, or epoxy
> - Tolerance: plus or minus 0.05 mm on both dimensions
> - Quantity: 1,000 pieces, with the price at 500 and at 2,000
> - Samples: price and lead time for 20 pieces
> - Packaging suitable for strong magnets
> - Delivery to a US address: the delivered, duty-paid price, and the price ex-works
> - The customs code you declare, your lead time, and your payment terms
> - A grade datasheet or certificate
>
> Thank you.

Compare at least two replies. Prefer a supplier that sends a sample first, and that quotes a delivered, duty-paid price.

## Duty, shipping and safety

- **Duty.** Trade guides found for this project say the US small-parcel duty exemption ended for China in 2025. They disagree on the 2026 rate, so do not rely on them. Ask the carrier for a duty-inclusive quote, and check the declared customs code against the US tariff schedule before ordering.
- **One entry.** A single consolidated order keeps the fees down. That is the main reason to order as a group.
- **Lead time.** Factory orders can take weeks. The ICM-42688-P IMU has a 45 to 53 week lead time at some distributors, so order early and keep a second source.
- **Magnets.** Strong magnets pinch fingers and can shatter if they snap together. Use spacers. Keep them away from pacemakers, phones, cards and drives. Ask the carrier about rules for magnetized material in air freight.
- **Cells.** Lithium cells are not in this plan. Shipping rules make factory cells impractical for individuals, so buy domestic. See [supply-side.md](supply-side.md).

## After the order

Record in the plan, as aggregate numbers only: what arrived, what failed the inspection tests, and the true delivered cost. Update the prices in [materials.json](../bom/materials.json) with the delivered costs and dates, so the next pass of the cost model starts from real numbers.
