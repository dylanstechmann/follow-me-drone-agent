# Cost reduction

Budget: $100 for the bench and pipeline work (see [budget.md](budget.md)). A flying drone's hardware is a separate budget. Every price comes from [bom/catalog.json](../bom/catalog.json) and [bom/materials.json](../bom/materials.json), and each price carries the date it was seen on its source. Most are undated or older than 12 months, which [price-audit.md](price-audit.md) lists. Check each one at the seller before buying.

Run the reports after any change:

```
PYTHONPATH=src python3 -m follow_me.bom                    # cost report for every pass, plus dependency check
PYTHONPATH=src python3 -m follow_me.bom --passes-markdown  # the pass table below
PYTHONPATH=src python3 -m follow_me.bom --audit            # price dates and placeholders
PYTHONPATH=src python3 -m follow_me.bom --markdown         # the parts catalog
```

## Labels

Status (how sure the price is):

- **snapshot**: seen on a source page or in a listing.
- **official**: a manufacturer's list price.
- **estimate**: a calculation from a stated assumption, such as grams of filament.
- **placeholder**: a guess, counted in totals so the total is not too low.
- **owned** and **purchased**: already held, at $0, or at the exact price the owner paid.
- **unpriced**: not priced, counted as $0 and reported separately.

Checked (when the price was seen): a date (`2026-10-10`), a month (`2026-08`), a year (`2026`), or empty (undated). A price is **fresh** only with month precision and a date within 12 months before 2026-10-10.

Path (how the part is obtained):

- **buy_retail**: a finished product or module at retail or marketplace prices.
- **buy_bulk**: a distributor price for a chip, module or commodity.
- **buy_used**: used or refurbished.
- **buy_service**: a fabrication service, such as a PCB fab.
- **make**: computed from raw materials in [materials.json](../bom/materials.json).
- **owned** or **salvage**: already held, or reclaimed.

## Pass results

Core costs in USD, low to high. Optional items are excluded. The last column counts sourced prices dated within 12 months.

| Pass | Based on | Core low | Core high | Change vs base (low to high) | Made in house | Budget | Placeholders | Dated in 12 months |
|---|---|---|---|---|---|---|---|---|
| pass0 Retail autopilot drone with tag and phone | none (starting point) | 560.02 | 976.29 | none | 0% | over | 8 | 0 of 11 |
| pass1 Used autopilot, Pi Zero streams video | pass0 | 498.08 | 750.10 | -61.94 to -226.19 | 0% | over | 8 | 0 of 10 |
| pass2 Printed frame and guards | pass1 | 471.04 | 697.23 | -27.04 to -52.87 | 1% | over | 9 | 0 of 10 |
| pass3 Bench-first kit (no flying drone yet) | pass2 | 67.36 | 101.23 | -403.68 to -596.00 | 1% | fits at low prices only | 2 | 0 of 6 |
| pass4 Used feature-rich phone replaces the Pi and camera (example) | pass2 | 686.04 | 907.23 | +215.00 to +210.00 | 1% | over | 10 | 0 of 8 |
| pass5 Bench kit with a made tag | pass3 | 63.87 | 98.99 | -3.49 to -2.24 | 1% | fits at both ends | 2 | 1 of 7 |
| pass6 Printed structure, DIY motor research, thrust stand | pass2 | 468.16 | 764.39 | -2.88 to +67.16 | 13% | over | 10 | 3 of 14 |
| pass7 Owned pipeline | pass6 | 460.07 | 747.85 | -8.09 to -16.54 | 13% | over | 9 | 4 of 16 |
| pass8 Own most: made autopilot board, ESC, transmitter, tag battery | pass7 | 267.32 | 594.07 | -192.75 to -153.78 | 45% | over | 9 | 7 of 23 |
| pass9 Own most, with the by-weight and salvage motor target | pass8 | 253.12 | 523.59 | -14.20 to -70.48 | 38% | over | 9 | 6 of 22 |

Pass 3 includes the optional Tello refurbished ($79 to $139). Pass 7 has the optional CNC mill ($115 to $200). Neither is in the core totals.

## What each pass does and the risk it adds

- **Pass 0, retail.** Every part a complete first build would want, at retail or marketplace prices.
- **Pass 1, used autopilot.** A used Pix32 v5 at $149 replaces the new board. At the low end it is not cheaper than the new one ($146.99), so the saving comes from dropping the Pi 5 and the ToF sensor. Risk added: control depends on the ground link, so the autopilot's link-loss failsafe must be tested in simulation.
- **Pass 2, printed structure.** Printed frame, guards and camera mount replace the commercial frame. Risk added: printed parts fail differently from moulded ones, so each load-bearing part needs a bench test. See [3d-printing.md](3d-printing.md).
- **Pass 3, bench-first kit.** Drops every flying part and keeps what a desk needs. This is the only pass that fits $100 at low prices without a made tag.
- **Pass 4, used phone onboard (example).** A used phone replaces the Pi and camera. It costs $210 to $215 more. The example is the owner's Pixel 8a, bought for $250. Risk added: about 188 g of weight, a phone battery on a drone, and a MAVLink bridge to build and test.
- **Pass 5, made tag.** Replaces the retail HT-CT62 with a bulk ESP32-C3 and an outsourced 2-layer board. Wi-Fi replaces the LoRa chip. Risk added: Wi-Fi range must be measured in the field. The saving is $2 to $3.50.
- **Pass 6, DIY motor research.** Replaces the four T-Motors with DIY outrunners and adds a thrust stand. Risk added: DIY motors may be less efficient or less reliable. Magnets bought per disc are the largest cost.
- **Pass 7, owned pipeline.** Combines the printed structure, the made tag, DIY motor research and the thrust stand. Still bought: the autopilot, GPS, ESC, transmitter, battery, charger and props.
- **Pass 8, own most.** Replaces the bought autopilot, ESC, transmitter and tag battery with designs made from chips and outsourced or printed parts. Risk added: the autopilot firmware port, the barometer and regulators, and the MOSFET prices are not costed or are placeholders.
- **Pass 9, by-weight motors.** A what-if: magnets bought by weight, wire and shaft salvaged. It is real only after a magnet quote and a salvage check.

## Findings

- **The bench kit fits $100 at both ends with a made tag** (pass 5: $63.87 to $98.99). Without the made tag, it fits only at low prices (pass 3).
- **Owning more cuts the drone's cost but not below $100.** Pass 8 is $267 to $594, and 45 percent of that cost is made in-house by cost (midpoints). The largest remaining items are the motors at retail magnet prices, the Holybro GPS, the ESC, the charger and LiPo bag (placeholders), the 4S battery and the camera.
- **Motors are the biggest make item and the largest uncertainty.** At retail magnet prices, four DIY motors cost $33.64 to $111.24, against $40 to $54 for four T-Motors. Magnets bought by weight and salvaged wire and shaft bring the target to $19.44 to $40.76 (pass 9).
- **The ESC depends on MOSFET prices we have not verified.** The bulk price is a placeholder, and the retail price is $1.75 (June 2026). The ESC total is $15.92 to $82.18 for that reason.
- **The made tag saves little.** The GNSS module and antenna dominate the cost.
- **Outsourcing a 2-layer board beats etching in-house.** $0.40 to $0.70 per board, against $1.82 to $15.48 for 100 cm2 etched at home.
- **The data is weaker than the totals suggest.** Only 9 of 39 sourced prices are dated within 12 months, and 16 inputs are placeholders. The totals are useful for comparing routes, not for quoting a build.

## Gaps that change the numbers

- Undated prices: about 30 of the 39 sourced prices. Re-check the chips, the GPS modules and the motors first, because they drive most of the total.
- MOSFET and gate-driver bulk prices, for the ESC.
- The laser-cut stator, the 4-layer board, the gimbal pots and the transmitter's 2.4 GHz module.
- The charger and LiPo bag for the drone, both still retail placeholders.
- The PETG price (a placeholder).

## Repeating the loop

1. Check a price at the seller. Update its row in [catalog.json](../bom/catalog.json) or its input in [materials.json](../bom/materials.json). Record the date you saw it in `checked`, and set the status to match the source.
2. If a design changes, change its path and its make inputs together.
3. Add a pass based on the latest one, with its adds and removes, reason and risk.
4. Run the reports. Regenerate [parts-catalog.md](parts-catalog.md), [price-audit.md](price-audit.md) and the table above.
5. Commit the data, the passes and the docs together.
