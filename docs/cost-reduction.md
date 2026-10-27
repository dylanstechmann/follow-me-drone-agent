# Cost reduction

Budget: $100 for the bench and pipeline work (see [budget.md](budget.md)). A flying drone's hardware is a separate budget. Every price comes from [bom/catalog.json](../bom/catalog.json) and [bom/materials.json](../bom/materials.json). Each price carries the date it was seen on its source. 47 of 51 sourced prices were seen within 12 months, most of them on 2026-10-27, as [price-audit.md](price-audit.md) shows. Prices move, so check each one at the seller before buying.

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

Checked (when the price was seen): a date, a month, a year, or empty (undated). A price is **fresh** only with month precision and a date within 12 months before 2026-10-27.

Path (how the part is obtained):

- **buy_retail**, **buy_bulk**, **buy_used**: bought finished, from a retailer, distributor or the used market.
- **buy_service** and **buy_factory**: made by a fab or factory. When the item lists its parts, it is the owner's design.
- **make**: made in-house from materials.
- **owned** or **salvage**: already held, or reclaimed.

Three cash numbers:

- **Core cost** is per drone, at the price for the quantity needed.
- **Cash at minimum orders** is what it takes to place every order at its minimum quantity: 100 factory bearings, five boards per design, one assembly setup per design, and so on. Its high end includes the waste allowance on made items, as the core cost does.
- **Cost per drone for a number of drones** is the cash to build that many, minimum orders included, divided by the count. See the table below the pass results.

## Pass results

The table is generated from the data files and kept in sync by `PYTHONPATH=src python3 -m follow_me.docs_sync`. Do not edit it by hand.

<!-- generated:passes:start -->
| Pass | Based on | Core low | Core high | Change vs base (low to high) | Cash at minimum orders | Made in house | Owner-designed | Budget | Placeholders | Sourced prices dated in last 12 months |
|---|---|---|---|---|---|---|---|---|---|---|
| pass0_retail_autopilot Retail autopilot drone with tag and phone | none | 668.18 | 977.10 | none (starting point) | 678.21 to 994.55 | 0% | 0% | over budget | 7 | 12 of 12 |
| pass1_shop_smart Used autopilot, Pi Zero streams video, ground station runs detection | pass0_retail_autopilot | 524.23 | 760.93 | -143.95 to -216.17 | 534.26 to 778.38 | 0% | 0% | over budget | 7 | 10 of 11 |
| pass2_print_structure Printed frame and guards | pass1_shop_smart | 497.24 | 708.06 | -26.99 to -52.87 | 519.26 to 748.38 | 1% | 1% | over budget | 8 | 10 of 11 |
| pass3_bench_first Bench-first kit (no flying drone yet) | pass2_print_structure | 72.62 | 101.74 | -424.62 to -606.32 | 82.34 to 118.54 | 1% | 1% | fits budget at low prices only | 2 | 6 of 6 |
| pass4_pixel_onboard Used feature-rich phone replaces the Pi and camera on the drone (example) | pass2_print_structure | 712.24 | 918.06 | +215.00 to +210.00 | 734.26 to 958.38 | 1% | 1% | over budget | 9 | 8 of 9 |
| pass5_made_tag Bench kit with a made tag: bulk ESP32-C3 and outsourced board | pass3_bench_first | 69.13 | 99.20 | -3.49 to -2.54 | 78.85 to 116.00 | 1% | 1% | fits budget at low and high prices | 2 | 7 of 7 |
| pass6_diy_motor_rnd Printed structure with DIY motor research and a thrust stand | pass2_print_structure | 493.39 | 792.41 | -3.85 to +84.35 | 524.60 to 865.32 | 16% | 16% | over budget | 9 | 14 of 15 |
| pass7_owned_pipeline Owned pipeline: printed structure, made tag, DIY motor research | pass6_diy_motor_rnd | 485.30 | 775.57 | -8.09 to -16.84 | 516.51 to 848.48 | 16% | 16% | over budget | 8 | 16 of 17 |
| pass8_own_most Own most: made autopilot board, ESC, transmitter and tag battery | pass7_owned_pipeline | 301.76 | 638.79 | -183.54 to -136.78 | 344.64 to 823.35 | 48% | 48% | over budget | 7 | 26 of 26 |
| pass9_own_most_target_motors Own most, with the by-weight and salvage motor target | pass8_own_most | 264.84 | 527.95 | -36.92 to -110.84 | 401.23 to 840.85 | 39% | 39% | over budget | 7 | 24 of 25 |
| pass10_factory_and_lab Closer to the factory: factory-assembled boards, factory magnets and bearings, lab-etched stators | pass8_own_most | 239.66 | 544.96 | -62.10 to -93.83 | 361.63 to 841.62 | 20% | 51% | over budget | 10 | 28 of 28 |
| pass11_factory_stators Factory stator cores at a 1,000-piece minimum | pass10_factory_and_lab | 242.66 | 549.84 | +3.00 to +4.88 | 1,349.39 to 2,824.33 | 21% | 52% | over budget | 10 | 27 of 28 |
<!-- generated:passes:end -->

Pass 3 includes the optional Tello refurbished ($79). Pass 7 and later include the optional CNC mill ($169). Neither is in the core totals.

## Cost per drone as the number of drones grows

This is for exploring only. The owner has not set a number of drones. Each cell is the cash to build that many drones, with every order at least its minimum, divided by the count, in whole USD, low to high. It assumes one order per design for the whole batch and the same unit prices at every count, so real volume discounts would lower it. The PCB assembly setup fee and the extended-part loading fee are paid once per order (`per_order` in [materials.json](../bom/materials.json)), so at large counts the cost per drone falls below the core cost, which spreads those fees over five boards. The import-duty allowance stays per drone, because duty grows with an order's value. Like the rest of the model, it leaves out labour, tooling, failed builds, crashes, storage and shipping.

<!-- generated:drones:start -->
| Pass | 1 drone | 5 drones | 20 drones | 100 drones | 500 drones |
|---|---|---|---|---|---|
| pass0_retail_autopilot | 678 to 995 | 670 to 980 | 668 to 977 | 668 to 977 | 668 to 977 |
| pass1_shop_smart | 534 to 778 | 526 to 764 | 524 to 761 | 524 to 761 | 524 to 761 |
| pass2_print_structure | 519 to 748 | 499 to 710 | 497 to 708 | 497 to 708 | 497 to 708 |
| pass3_bench_first | 82 to 119 | 74 to 104 | 73 to 102 | 73 to 102 | 73 to 102 |
| pass4_pixel_onboard | 734 to 958 | 714 to 920 | 712 to 918 | 712 to 918 | 712 to 918 |
| pass5_made_tag | 79 to 116 | 71 to 102 | 69 to 99 | 69 to 99 | 69 to 99 |
| pass6_diy_motor_rnd | 525 to 865 | 494 to 793 | 493 to 792 | 493 to 792 | 493 to 792 |
| pass7_owned_pipeline | 517 to 848 | 486 to 776 | 485 to 776 | 485 to 776 | 485 to 776 |
| pass8_own_most | 345 to 823 | 303 to 639 | 302 to 639 | 302 to 639 | 302 to 639 |
| pass9_own_most_target_motors | 401 to 841 | 280 to 548 | 265 to 528 | 265 to 528 | 265 to 528 |
| pass10_factory_and_lab | 362 to 842 | 243 to 549 | 229 to 533 | 226 to 530 | 225 to 529 |
| pass11_factory_stators | 1,349 to 2,824 | 440 to 941 | 277 to 627 | 235 to 544 | 228 to 534 |
<!-- generated:drones:end -->

## What each pass does and the risk it adds

- **Pass 0, retail.** Every part a complete first build would want, at retail or marketplace prices.
- **Pass 1, used autopilot.** A used Pix32 v5 at $149 (one undated listing) replaces the new board at $189.00 to $252.97, and the Pi 5 and the ToF sensor are dropped. Risk added: control depends on the ground link.
- **Pass 2, printed structure.** Printed frame, guards and camera mount. Risk added: printed parts need bench load tests ([3d-printing.md](3d-printing.md)).
- **Pass 3, bench-first kit.** Only what a desk needs.
- **Pass 4, used phone onboard (example).** Costs $210 to $215 more than the Pi and camera it replaces. Risk added: weight, a phone battery on a drone, and a MAVLink bridge.
- **Pass 5, made tag.** Bulk ESP32-C3 and an outsourced board. Wi-Fi replaces LoRa.
- **Pass 6, DIY motors with retail parts.** $11.96 to $35.17 a motor against $14.99 to $17.99 retail, so cheaper only at the low end, because miniature bearings at retail are $3 to $4.38 each.
- **Pass 7, owned pipeline.** Printed structure, made tag, DIY motor research, thrust stand.
- **Pass 8, own most.** Hand-assembled autopilot board, ESC and transmitter, and an own tag battery. Risk added: the autopilot firmware port and MOSFET prices are not costed.
- **Pass 9, by-weight motors.** A what-if: magnets by weight, wire and shaft salvaged.
- **Pass 10, closer to the factory.** The board factory assembles the owner's designs from its own parts stock. The GPS becomes an own board with a bare M9N. Magnets and bearings come from factories. Stators are etched in the lab (unverified). The tag moves to a BLE chip and a clone GNSS module (both untested). Includes an import-duty allowance. Risk added: minimum orders, uncertain duty, and new parts that need testing.
- **Pass 11, factory stators.** A what-if that shows the cash trap of a 1,000-piece minimum order.

## Findings

- **The bench kit fits $100 at both ends with a made tag** (pass 5: $69.13 to $99.20), with 80 cents to spare at the high end.
- **Going upstream is the biggest cut so far.** Pass 10 is $239.66 to $544.96 per drone, against $301.76 to $638.79 for pass 8. The largest savings are the motors' factory parts ($35.68 to $95.04 for four) and the GPS: an own factory-assembled board at $21.33 to $28.86 replaces a $54.99 to $74.90 retail board.
- **Motors only beat retail reliably with factory parts.** With retail magnets and bearings, a DIY motor is $11.96 to $35.17. With factory magnets and bearings and a lab-etched stator, it is $3.04 to $11.41. A known-brand retail 2207 is $14.99 to $17.99.
- **Cheaper per drone needs more cash up front.** Pass 10 needs $361.63 to $841.62 at minimum orders. Factory stator cores (pass 11) push that to $1,349.39 to $2,824.33. Group orders through the IEEE club are how this becomes affordable.
- **Still over $100 for a flying drone.** The 4S battery, charger, LiPo bag, camera, Pi and ESC MOSFETs remain.
- **The data is better dated, and still not a quote.** 47 of 51 sourced prices were seen within 12 months, but 16 inputs are placeholders. The totals compare routes.

## Gaps that change the numbers

- **ESC MOSFET bulk price.** The largest placeholder in pass 10.
- **Import duty rate.** A placeholder allowance until checked with CBP.
- **Lab lamination etching.** An unverified process with a placeholder cost.
- **Ceramic GNSS antenna, gimbal pots, steel shaft, charger, LiPo bag and PETG.** All placeholders.
- **Four sourced prices that could not be re-read on 2026-10-27:** the used Pix32 v5, the FR4 board, magnets by weight and factory stator cores.
- **The ESC gate driver.** The cheaper FD6288Q was gone and the original out of stock on 2026-10-27.

## Repeating the loop

1. Check a price at the seller. Update its row in [catalog.json](../bom/catalog.json) or its input in [materials.json](../bom/materials.json). Record the date you saw it, its minimum order (`moq`), whether each design pays its own minimum (`moq_per_item`), and whether it is a fee paid once per order (`per_order`).
2. If a design changes, change its path and its inputs together.
3. Add a pass based on the latest one, with adds, removes, reason and risk.
4. Run the reports. Regenerate [parts-catalog.md](parts-catalog.md), [price-audit.md](price-audit.md) and the table above.
5. Commit the data, the passes and the docs together.
