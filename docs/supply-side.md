# Closer to the supply side

Each part can move up its supply chain: retail, then marketplace, then distributor, then factory, then fab or lab. Each step usually lowers the unit price and adds something else: a minimum order, a lead time, an import duty, or a quality risk. The cost model now shows both numbers for every pass: the per-drone cost, and the cash needed to place every order at its minimum.

Prices come from [bom/materials.json](../bom/materials.json) and [bom/catalog.json](../bom/catalog.json). Only 10 of 51 sourced prices are dated within the last 12 months ([price-audit.md](price-audit.md)), so treat every figure as provisional.

## Where each part sits, and the next step up

| Part | Now | Next step up (price, minimum order) | Verdict |
|---|---|---|---|
| N52 magnets, 10 x 2 mm | Distributor $0.26 to $0.78 each | Factory $0.02 to $0.10 each at 1,000 pieces (listing about 17 months old) | Go upstream. 1,000 magnets is $20 to $100 and covers about 70 motors. Pull-test a sample. |
| Miniature bearings, 4 x 9 x 4 mm | Retail $3.00 to $4.38 each | Factory $0.16 to $0.88 each at 100 pieces | Go upstream. Spin-test and check play. |
| Stator cores | Laser-cut by a service (placeholder) | Lab photo-etch, about $0.24 to $1.05 with steel (unverified). Factory $0.99 to $1.99 at 1,000 pieces, 10 to 12 weeks of tooling | Etch in the lab first. Factory cores only as a group order. |
| Electrical steel | None yet | $1.44 to $2.09 per kg (Q2 2026 benchmarks); small lots cost more | Buy a small sheet for etching tests. |
| Magnet wire | Retail spool about $44.57 per kg | Factory $7 to $10 per kg at 300 kg | Salvage, or buy a 1 kg spool. The factory minimum is far too large. |
| Complete motors | T-Motor $10 to $13.50 each | Factory 2207 about $11 each at 10 pieces | No gain. The gain is in the parts. |
| ESC | Hand-assembled own design, $12.40 to $81.79 | Factory-assembled own design, $16.20 to $80.15 | Factory assembly from the fab's own parts stock. FD6288Q drivers are $0.27 to $0.67. The MOSFET price is still a placeholder. |
| Autopilot board | Hand-assembled own design, $12.37 to $47.94 | Factory-assembled, $15.69 to $45.21 | Factory assembly suits the fine-pitch MCU and the LGA IMU. |
| GPS | Holybro M9N board $54.99 to $74.90 | Own board with a bare M9N, factory-assembled, $15.54 to $28.59 | Go upstream. The largest single saving. No compass yet. |
| Tag | ESP32-C3 module ($2.01 to $3.06) and M9N | CH592 BLE chip ($0.46 to $0.95) and a clone GNSS module ($1.82 to $3.24); the tag board is $7.26 to $16.36 | Test both new parts against the old ones before switching. |
| Bare ESP32-C3 | Module $2.01 to $3.06 | ESP32-C3FH4 chip $1.30 to $2.50 | Small saving, adds RF design work. The CH592 is the bigger saving if BLE is enough. |
| PCBs | 2-layer $0.40 to $0.70 per board | Already at the factory. 4-layer $1.40 to $15 per board. Five boards per design minimum. | Stay. |
| PCB assembly | Hand soldering | Economic factory assembly: $9.71 per order, $0.0016 per joint, $1.50 to $3 per extended part type (JLCPCB help page, about a month old) | Use basic parts where possible, since they have no loading fee. |
| Props | Retail 4-pack $2.89 to $3.29 | Factory $0.70 to $1.20 per prop | No gain. Stay retail. |
| Cells | Undated wholesale $1.00 to $3.20 | US distributor EVE 30P $3.89 to $4.99; factory listings $1.14 to $2.20 (authenticity unverified) | Buy domestic. Factory cells are dangerous goods to ship. |
| Filament | 5 to 20 kg PLA $8.55 to $10.49 per kg | Pellets $1.00 to $4.85 per kg at 25 kg, plus an extruder at EUR 699 to EUR 1,399 | Not worth it. Payback takes about 55 to 150 kg. |

## What the model says

From [cost-reduction.md](cost-reduction.md):

- **Pass 10, closer to the factory:** $207.86 to $534.21 per drone, $67 to $89 cheaper than pass 8. The cash needed at minimum orders is $332.20 to $934.98. 20 percent of the cost is made in-house and 51 percent is the owner's own design, since the factory assembles boards the owner designed. Still over $100.
- **Pass 11, factory stator cores:** about the same per drone ($210.86 to $539.05), but $1,319.96 to $2,918.89 of cash to start.
- **Cheapest per drone is not cheapest to start.** Minimum orders turn small unit prices into large up-front orders. A group order spreads them: 1,000 magnets cover about 17 drones' worth of motors.

## What going upstream costs

1. **Minimum orders.** Cash, storage and leftover stock. The model reports the cash for each pass.
2. **Import duty.** Trade guides report that the US small-parcel exemption ended for China in May 2025 and for other origins in August 2025. One guide says CBP made it permanent from 24 June 2026. They disagree on the 2026 rate, so the model carries a $10 to $60 placeholder per consolidated order. Verify with CBP before ordering, and combine orders into one entry.
3. **Lead times.** New stator tooling takes 10 to 12 weeks. Distributors quote 45 to 53 weeks for the ICM-42688-P IMU. Order early, and keep a second source.
4. **Quality.** Factory and marketplace parts vary, and some are counterfeit. Inspect what arrives: pull-test magnets, spin-test bearings, capacity-test cells, and buy chips from authorized distributors.
5. **Lithium shipping.** Shipping guides say standalone cells (UN3480) fly on cargo aircraft only, at 30 percent charge or less. From 1 January 2026 the same limit also covers batteries packed with equipment above 2.7 Wh. Sea freight has no charge limit but is slow. For an individual, domestic distributors are the practical route.

## Group orders through the IEEE club

- One order meets the minimum, and members pay per unit. This is cost-sharing, not fundraising.
- Good candidates: magnets (1,000), bearings (100), boards (five per design), assembly setup fees (one per design), and later stator cores (1,000).
- One customs entry for the whole order keeps duty fees down.
- Keep a written allocation of who paid for what, in the club's private channel, not on GitHub.

The plan, its quantities, minimum orders, costs per member and status are in [group-order.md](group-order.md). It is generated from [bom/group_order.json](../bom/group_order.json), so it stays current as the order moves.

## The lab: what FAU has

- FAU's School of Architecture runs a FabLab in Fort Lauderdale with laser cutters, 3D printers, a CNC machine, a 3D scanner and a wood shop. A safety orientation comes first.
- Ask whether any laser is a fiber laser. Most makerspace CO2 lasers cannot cut steel, so stator laminations need a fiber laser, a cutting service, or etching.
- No FAU cleanroom turned up. The University of Florida's Nanoscale Research Facility has cleanrooms for UF-affiliated users.
- The closest route to a chip fab is a shared shuttle such as Tiny Tapeout (about EUR 70 per digital tile, undated). See [make-own-ladder.md](make-own-ladder.md).

In-house steps the owner can take on:

- Board etching, for fast iteration.
- Lamination etching (test on a coupon first).
- Reflow assembly with a stencil and a hot plate (not priced).
- Motor winding and assembly.
- Thrust testing.
- Inspection of incoming parts.

## What not to pull upstream yet

- **Complete motors:** factory 2207s cost about the same as retail.
- **Props:** retail is already close to factory price.
- **Cells and flight packs:** shipping rules and safety. Buy known brands from domestic distributors.
- **Filament from pellets:** the extruder does not pay back at hobby scale.

## Corrections made in this pass

- The motor model used 608 skateboard bearings, which are 22 mm across, the same size as a 2207 stator. Small drone motors use miniature bearings around 4 x 9 x 4 mm. The DIY motor now costs $11.91 to $35.17 each with retail parts, against the earlier $8.41 to $27.81.
- "Laser-cut stator" assumed a laser that can cut steel. Most makerspace lasers cannot.

## Next steps

1. Price 30 V ESC MOSFETs in PDFN5x6 using LCSC's parametric search. This is the largest open placeholder in pass 10.
2. Ask two factories for quotes: N52 10 x 2 mm discs at 1,000, and 684ZZ bearings at 100.
3. Etch a test lamination coupon and check its edges and flatness.
4. Ask the FAU FabLab about the laser type and the orientation.
5. Ask the IEEE club about a group order and a shared customs entry.
6. Re-check the 41 sourced prices that are undated or older than 12 months.
