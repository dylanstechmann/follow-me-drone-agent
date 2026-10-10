# Cost reduction

Budget: $100 for the bench and pipeline work (see [budget.md](budget.md)). A flying drone's hardware is a separate budget. Every price comes from [bom/catalog.json](../bom/catalog.json) and [bom/materials.json](../bom/materials.json). Each price carries the date it was seen on its source. Only 10 of 51 sourced prices are dated within 12 months, as [price-audit.md](price-audit.md) shows, so check each one at the seller before buying.

Run the reports after any change:

```
PYTHONPATH=src python3 -m follow_me.bom                    # cost report for every pass, plus dependency check
PYTHONPATH=src python3 -m follow_me.docs_sync              # rewrite the generated tables in the docs
PYTHONPATH=src python3 -m follow_me.docs_sync --check      # fail if any generated table is stale
```

The pass table below, the [parts catalog](parts-catalog.md), the [price audit](price-audit.md) and the [group order](group-order.md) are generated blocks. The test suite fails when one is stale.

## Labels

Status (how sure the price is):

- **snapshot**: seen on a source page or in a listing.
- **official**: a manufacturer's list price.
- **estimate**: a calculation from a stated assumption.
- **placeholder**: a guess, counted in totals so the total is not too low.
- **owned** and **purchased**: already held, at $0, or at the exact price the owner paid.
- **unpriced**: not priced, counted as $0 and reported separately.

Checked (when the price was seen): a date, a month, a year, or empty (undated). A price is **fresh** only with month precision and a date within 12 months before 2026-10-10.

Path (how the part is obtained):

- **buy_retail**, **buy_bulk**, **buy_used**: bought finished, from a retailer, distributor or the used market.
- **buy_service** and **buy_factory**: made by a fab or factory. When the item lists its parts, it is the owner's design.
- **make**: made in-house from materials.
- **owned** or **salvage**: already held, or reclaimed.

Two cash numbers:

- **Core cost** is per drone, at the price for the quantity needed.
- **Cash at minimum orders** is what it takes to place every order at its minimum quantity: 1,000 magnets, five boards per design, one assembly setup per design, and so on.

## Pass results

The table is generated from the data files and kept in sync by `PYTHONPATH=src python3 -m follow_me.docs_sync`. Do not edit it by hand.

<!-- generated:passes:start -->
| Pass | Based on | Core low | Core high | Change vs base (low to high) | Cash at minimum orders | Made in house | Owner-designed | Budget | Placeholders | Sourced prices dated in last 12 months |
|---|---|---|---|---|---|---|---|---|---|---|
| pass0_retail_autopilot Retail autopilot drone with tag and phone | none | 557.91 | 964.58 | none (starting point) | 566.25 to 982.04 | 0% | 0% | over budget | 7 | 0 of 12 |
| pass1_shop_smart Used autopilot, Pi Zero streams video, ground station runs detection | pass0_retail_autopilot | 495.97 | 738.39 | -61.94 to -226.19 | 504.31 to 755.85 | 0% | 0% | over budget | 7 | 0 of 11 |
| pass2_print_structure Printed frame and guards | pass1_shop_smart | 468.93 | 685.52 | -27.04 to -52.87 | 489.31 to 725.85 | 1% | 1% | over budget | 8 | 0 of 11 |
| pass3_bench_first Bench-first kit (no flying drone yet) | pass2_print_structure | 67.36 | 101.23 | -401.57 to -584.29 | 75.44 to 118.04 | 1% | 1% | fits budget at low prices only | 2 | 0 of 6 |
| pass4_pixel_onboard Used feature-rich phone replaces the Pi and camera on the drone (example) | pass2_print_structure | 683.93 | 895.52 | +215.00 to +210.00 | 704.31 to 935.85 | 1% | 1% | over budget | 9 | 0 of 9 |
| pass5_made_tag Bench kit with a made tag: bulk ESP32-C3 and outsourced board | pass3_bench_first | 63.87 | 98.99 | -3.49 to -2.24 | 71.95 to 115.80 | 1% | 1% | fits budget at low and high prices | 2 | 1 of 7 |
| pass6_diy_motor_rnd Printed structure with DIY motor research and a thrust stand | pass2_print_structure | 480.05 | 782.12 | +11.12 to +96.60 | 509.96 to 825.42 | 16% | 16% | over budget | 9 | 2 of 15 |
| pass7_owned_pipeline Owned pipeline: printed structure, made tag, DIY motor research | pass6_diy_motor_rnd | 471.96 | 765.58 | -8.09 to -16.54 | 501.87 to 808.88 | 16% | 16% | over budget | 8 | 3 of 17 |
| pass8_own_most Own most: made autopilot board, ESC, transmitter and tag battery | pass7_owned_pipeline | 275.09 | 623.11 | -196.87 to -142.47 | 316.85 to 752.24 | 48% | 48% | over budget | 7 | 6 of 26 |
| pass9_own_most_target_motors Own most, with the by-weight and salvage motor target | pass8_own_most | 238.17 | 516.23 | -36.92 to -106.88 | 373.44 to 834.95 | 38% | 38% | over budget | 7 | 5 of 25 |
| pass10_factory_and_lab Closer to the factory: factory-assembled boards, factory magnets and bearings, lab-etched stators | pass8_own_most | 207.86 | 534.21 | -67.23 to -88.90 | 332.20 to 934.98 | 20% | 51% | over budget | 10 | 7 of 28 |
| pass11_factory_stators Factory stator cores at a 1,000-piece minimum | pass10_factory_and_lab | 210.86 | 539.05 | +3.00 to +4.84 | 1,319.96 to 2,918.89 | 21% | 51% | over budget | 10 | 6 of 28 |
<!-- generated:passes:end -->

Pass 3 includes the optional Tello refurbished ($79 to $139). Pass 7 and later include the optional CNC mill ($115 to $200). Neither is in the core totals.

## What each pass does and the risk it adds

- **Pass 0, retail.** Every part a complete first build would want, at retail or marketplace prices.
- **Pass 1, used autopilot.** A used Pix32 v5 at $149 replaces the new board. Its low end is not cheaper than new ($146.99), so the saving comes from dropping the Pi 5 and the ToF sensor. Risk added: control depends on the ground link.
- **Pass 2, printed structure.** Printed frame, guards and camera mount. Risk added: printed parts need bench load tests ([3d-printing.md](3d-printing.md)).
- **Pass 3, bench-first kit.** Only what a desk needs.
- **Pass 4, used phone onboard (example).** Costs $210 to $215 more than the Pi and camera it replaces. Risk added: weight, a phone battery on a drone, and a MAVLink bridge.
- **Pass 5, made tag.** Bulk ESP32-C3 and an outsourced board. Wi-Fi replaces LoRa.
- **Pass 6, DIY motors with retail parts.** Now more expensive than retail motors, because miniature bearings at retail are $3 to $4.38 each.
- **Pass 7, owned pipeline.** Printed structure, made tag, DIY motor research, thrust stand.
- **Pass 8, own most.** Hand-assembled autopilot board, ESC and transmitter, and an own tag battery. Risk added: the autopilot firmware port and MOSFET prices are not costed.
- **Pass 9, by-weight motors.** A what-if: magnets by weight, wire and shaft salvaged.
- **Pass 10, closer to the factory.** The board factory assembles the owner's designs from its own parts stock. The GPS becomes an own board with a bare M9N. Magnets and bearings come from factories. Stators are etched in the lab (unverified). The tag moves to a BLE chip and a clone GNSS module (both untested). Includes an import-duty allowance. Risk added: minimum orders, uncertain duty, and new parts that need testing.
- **Pass 11, factory stators.** A what-if that shows the cash trap of a 1,000-piece minimum order.

## Findings

- **The bench kit fits $100 at both ends with a made tag** (pass 5: $63.87 to $98.99).
- **Going upstream is the biggest cut so far.** Pass 10 is $207.86 to $534.21 per drone, against $275.09 to $623.11 for pass 8. The largest single saving is the GPS: an own factory-assembled board at $15.54 to $28.59 replaces a $54.99 to $74.90 retail board.
- **Motors only beat retail with factory parts.** With retail magnets and bearings, a DIY motor is $11.91 to $35.17. With factory magnets and bearings and a lab-etched stator, it is $2.57 to $12.40. A T-Motor is $10 to $13.50.
- **Cheaper per drone needs more cash up front.** Pass 10 needs $332.20 to $934.98 at minimum orders. Factory stator cores (pass 11) push that to $1,319.96 to $2,918.89. Group orders through the IEEE club are how this becomes affordable.
- **Still over $100 for a flying drone.** The 4S battery, charger, LiPo bag, camera, Pi and ESC MOSFETs remain.
- **The data is weak.** Only 10 of 51 sourced prices are dated within 12 months, and 16 inputs are placeholders. The totals compare routes. They are not a quote.

## Gaps that change the numbers

- **ESC MOSFET bulk price.** The largest placeholder in pass 10.
- **Import duty rate.** A placeholder allowance until checked with CBP.
- **Lab lamination etching.** An unverified process with a placeholder cost.
- **Ceramic GNSS antenna, gimbal pots, steel shaft, charger, LiPo bag and PETG.** All placeholders.
- **About 41 undated or stale prices.**

## Repeating the loop

1. Check a price at the seller. Update its row in [catalog.json](../bom/catalog.json) or its input in [materials.json](../bom/materials.json). Record the date you saw it, its minimum order (`moq`), and whether each design pays its own minimum (`moq_per_item`).
2. If a design changes, change its path and its inputs together.
3. Add a pass based on the latest one, with adds, removes, reason and risk.
4. Run the reports. Regenerate [parts-catalog.md](parts-catalog.md), [price-audit.md](price-audit.md) and the table above.
5. Commit the data, the passes and the docs together.
