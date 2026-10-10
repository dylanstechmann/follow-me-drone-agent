# Cost reduction

Budget: $100 for the bench and pipeline work (see [budget.md](budget.md)). The flight hardware for a drone is a separate budget and is not covered. Every price here comes from [bom/catalog.json](../bom/catalog.json) and [bom/materials.json](../bom/materials.json). Prices are search snapshots from 2026-10-10, so check each one at the seller before buying.

Run the reports after any change:

```
PYTHONPATH=src python3 -m follow_me.bom                    # cost report, every pass, plus dependency check
PYTHONPATH=src python3 -m follow_me.bom --passes-markdown  # the pass table below
PYTHONPATH=src python3 -m follow_me.bom --markdown         # the parts catalog
```

## Labels

Status (how sure the price is):

- **snapshot**: seen in a search result or listing. Date unknown.
- **official**: a manufacturer's list price.
- **estimate**: a calculation from a stated assumption, such as grams of filament.
- **placeholder**: a guess, counted in totals so the total is not too low.
- **owned** and **purchased**: already held, at $0, or at the exact price the owner paid.
- **unpriced**: not priced, counted as $0 and reported separately.

Path (how the part is obtained):

- **buy_retail**: a finished product or module at retail or marketplace prices.
- **buy_bulk**: a distributor's bulk price for a chip, module or commodity.
- **buy_used**: used or refurbished.
- **buy_service**: a fabrication service, such as a PCB fab.
- **make**: computed from raw materials in [materials.json](../bom/materials.json).
- **owned** or **salvage**: already held, or reclaimed.

## Pass results

Core costs in USD, low to high. Optional items are excluded.

| Pass | Based on | Core low | Core high | Change vs base (low to high) | Made in house (midpoint) | Budget | Placeholders |
|---|---|---|---|---|---|---|---|
| pass0 Retail autopilot drone with tag and phone | none (starting point) | 560.08 | 976.35 | none | 0% | over budget | 8 |
| pass1 Used autopilot, Pi Zero streams video, ground station runs detection | pass0 | 498.14 | 750.16 | -61.94 to -226.19 | 0% | over budget | 8 |
| pass2 Printed frame and guards | pass1 | 471.17 | 697.36 | -26.97 to -52.80 | 1% | over budget | 9 |
| pass3 Bench-first kit (no flying drone yet) | pass2 | 67.49 | 101.36 | -403.68 to -596.00 | 1% | fits at low prices only | 2 |
| pass4 Pixel 8a (bought used) replaces the Pi and camera | pass2 | 686.17 | 907.36 | +215.00 to +210.00 | 1% | over budget | 10 |
| pass5 Bench kit with a made tag | pass3 | 64.00 | 99.59 | -3.49 to -1.77 | 1% | fits at both ends | 2 |
| pass6 Printed structure with DIY motor research and a thrust stand | pass2 | 462.89 | 759.15 | -8.28 to +61.79 | 12% | over budget | 10 |
| pass7 Owned pipeline: printed structure, made tag, DIY motor research | pass6 | 454.80 | 743.08 | -8.09 to -16.07 | 12% | over budget | 9 |

Pass 3 includes the optional Tello refurbished ($79 to $139). Pass 7 has the optional CNC mill ($115 to $200) as well. Neither is in the core totals.

## What each pass does and the risk it adds

- **Pass 0, retail.** Every part a complete first build would want, at retail or marketplace prices. The commercial frame and retail motors are the big costs.
- **Pass 1, used autopilot.** A used Pix32 v5 at $149 replaces the new board. Its low end is not cheaper than the new board ($146.99), so the saving comes from dropping the Pi 5 and the ToF sensor. Risk added: control depends on the ground link, so the autopilot's link-loss failsafe must be tested in simulation.
- **Pass 2, printed structure.** Printed frame, guards and camera mount replace the commercial frame. Risk added: printed parts fail differently from moulded ones, so each load-bearing part needs a bench test. See [3d-printing.md](3d-printing.md).
- **Pass 3, bench-first kit.** Drops every flying part and keeps what a desk needs: a Pi Zero, a camera, the tag and printed parts. This is the only pass that fits $100 at low prices.
- **Pass 4, Pixel onboard.** The owner's Pixel 8a replaces the Pi and camera. It costs $210 to $215 more than pass 2. Risk added: about 188 g of extra weight, a phone battery on a drone, and a MAVLink bridge to build and test.
- **Pass 5, made tag.** Replaces the retail HT-CT62 with a bulk ESP32-C3 and an outsourced 2-layer board. The ESP32's Wi-Fi replaces the LoRa chip. Risk added: Wi-Fi range and dropouts must be measured in the field. The saving is only $1.77 to $3.49.
- **Pass 6, DIY motor research.** Replaces the four T-Motors with DIY outrunners and adds a thrust stand and load cell. Risk added: DIY motors may be less efficient or less reliable. The steel core is unpriced, so the total is incomplete.
- **Pass 7, owned pipeline.** Combines the printed structure, made tag, DIY motor research and thrust stand. Still bought: the autopilot, GPS, ESC, battery, charger, transmitter and props. Adds an unverified patch antenna on a bought board.

## Findings

- **Printing and bulk chips save the most per part, but the flight hardware is most of the cost.** Pass 7 is 12 percent made in-house by cost. The remaining 88 percent is the autopilot, GPS, ESC, transmitter, battery, charger and props.
- **The bench kit fits $100 at both ends with a made tag** (pass 5: $64.00 to $99.59). Without the made tag, it only fits at low prices (pass 3: $67.49 to $101.36).
- **The made tag saves little.** The GNSS module and the antenna and battery placeholders dominate. The bulk ESP32 is a small saving on its own.
- **Outsourcing a 2-layer board beats etching in-house.** $0.40 to $0.70 per board against $1.82 to $15.48 for a 100 cm2 single-sided board. Keep in-house etching for iteration.
- **DIY motors are not yet a saving.** $7.01 to $26.42 each, excluding the steel core, against $10 to $13.50 for a retail motor. The steel core could change this either way.
- **The Pixel is a purchase, not a free device.** It adds $210 to $215 over the Pi and camera it replaces. Whether it is worth that depends on the bench and replay results.
- **The flying drone does not fit in $100 with any pass.** The autopilot alone is $147 to $263 new. The bench kit fits; the flying drone needs a separate funding source.

## Gaps that change the numbers

- The PETG price is a placeholder ($15 to $30 per kg) until searched.
- The steel stator core for the DIY motor is unpriced.
- The tag battery, the ESC power stage, the transmitter, the propellers and the charger are placeholders or unpriced.
- The GNSS patch antenna is an unverified design, and its connector is not priced.

## Repeating the loop

1. Check a price at the seller. Update its row in [catalog.json](../bom/catalog.json), or its raw input in [materials.json](../bom/materials.json). Change its status to match the source.
2. If a part's design changes, change its path and its make inputs together.
3. Add a pass based on the latest one, with its adds and removes, reason and risk.
4. Run the reports, regenerate [parts-catalog.md](parts-catalog.md), and update the table above.
5. Commit the data, the passes, and the docs together.
