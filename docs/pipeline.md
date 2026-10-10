# Owning the pipeline

The goal is to make the drone without depending on any one supplier, and to stop paying a markup on parts that can be made or bought more cheaply in bulk. This doc says what that can realistically mean, where the markup actually sits, and what the cost model shows so far.

Numbers come from [bom/catalog.json](../bom/catalog.json) and [bom/materials.json](../bom/materials.json). They are search snapshots from 2026-10-10, so check them at the seller before buying.

## What "owning" means here

A part counts as owned when all three hold:

1. **Design.** The design files (CAD, PCB layout, firmware, BOM) are in this repo.
2. **Making.** The part can be made in-house, or ordered from at least two independent sources.
3. **Replaceable.** If one supplier disappears or raises prices, the build survives a change that can be made in about a week.

Some things cannot be owned at this scale: microcontroller and sensor chips, radio chips, GNSS chips, lithium cells, and the magnet supply chain. Own the layer above them: the boards, structure, wiring, motors' build, test rigs, firmware, and documentation.

## Where the markup actually is

The evidence from the search, in one table:

| Part | Retail or finished price | Bulk or raw price | Verdict |
|---|---|---|---|
| ESP32-C3 module | $6.90 to $9.00 (Heltec HT-CT62, which also has a LoRa chip) | $2.01 to $3.53 (LCSC, DigiKey) | The markup is large. Buy the chip in bulk and make the board. |
| GNSS module (NEO-M9N) | $54.99 (Holybro finished board) | $10.99 to $16.04 (bare module) | The finished board carries the markup. Buy the bare module. |
| 2-layer PCB, 10 x 10 cm | none needed | $0.40 to $0.70 per board (low-markup fab) | The fab's markup is small. Outsource production. |
| 100 cm2 single-sided board, etched in-house | none | $1.82 to $15.48 per board (material and etchant) | In-house etching is more expensive per board. Use it for fast iteration only. |
| PLA filament | $13 to $26 per kg (1 kg spools) | $10.99 to $20 per kg (5 kg spools) | Buy 5 kg spools for printing. |
| Commercial frame | $30 to $60 (placeholder) | about $2 to $5 printed in PETG (estimate) | Print it. |
| 2207 motor (T-Motor) | $10 to $13.50 each | $7.01 to $26.42 each DIY, excluding the unpriced steel core | Not a clear saving yet. Research only. |

The owner's instinct is right for modules and finished boards. It is not right for PCB fabrication: an outsourced 2-layer board is cheaper per board than etching one at home.

## Make or buy, part by part

| Part | Decision | Why | Model cost (USD) | Stage |
|---|---|---|---|---|
| Printed structure: frame, guards, camera mount, tag case | Make | Largest markup gap, low risk once tested | $0.33 to $5.40 per part | 1, now |
| Tag board | Design it yourself, outsource production | The fab's premium is small; keep the Gerbers so any fab can run it | $0.40 to $0.70 per board | 1 |
| Tag MCU (ESP32-C3-MINI-1) | Buy bulk from two distributors | Silicon cannot be made here | $2.01 to $3.53 | 1 |
| Tag GNSS (NEO-M9N-00B) | Buy bulk | The largest chip cost in the tag; no in-house alternative | $10.99 to $16.04 | 1 |
| Tag GNSS antenna | Design on a bought board | Cheap, but unverified | $0.40 to $0.70 plus a connector (not priced) | 1, prototype |
| Thrust stand | Make | Motors cannot be judged without one | about $3.68 to $10.11 (printed base plus load cell) | 2 |
| DIY outrunner motors | Research | Not a clear saving; the steel core is unpriced | $7.01 to $26.42 each, excluding the core | 2, research |
| Magnet wire and N52 magnets | Buy bulk; salvage where safe | Commodity inputs to motors | $26 to $45 per kg of wire; $0.26 to $0.78 per magnet | 2 |
| Propellers | Buy | Fast rotating, safety-critical; homemade props need testing to failure | $5 to $15 (placeholder) | later |
| ESC | Design later on an AM32-supported microcontroller | The MOSFET power stage is not priced | unpriced | 3 |
| Flight controller | Buy used for now; design later | Needs an IMU ($3.07 to $4.86 bulk), an MCU ($8.11 to $11.49 at 100 pieces), and a firmware port | used Pix32 v5 at $149 (one listing) | 4 |
| LiPo cells and packs | Buy from known brands; DIY packs not recommended now | Fire risk; needs an experienced reviewer | $24 to $38 per pack (bought) | 5, not recommended now |
| Phone as companion or drone computer | Owned, or bought used | See the Pixel note below | $0 owned; Pixel 8a bought for $250 | decision pending |

## What the model says now

From the pass report in [cost-reduction.md](cost-reduction.md):

- **The made tag fits $100 at both ends:** pass 5 comes to $64.00 to $99.59 for the bench kit with a made tag. It saves only $1.77 to $3.49 over the retail tag, because the GNSS module and antenna dominate the cost.
- **The owned pipeline is still mostly bought hardware:** pass 7 comes to $454.80 to $743.08 of core cost, and only 12 percent of that is made in-house by cost (midpoints). The autopilot, GPS, ESC, transmitter, battery, charger and props are the remaining 88 percent.
- **The Pixel costs more than the Pi and camera it replaces:** pass 4 adds $210 to $215 over pass 2. It buys a better camera, GNSS, IMU and compute. It is a purchase, not a free owned device.
- **Motors are not yet a saving:** pass 6 saves $8.28 at the low end and costs $61.79 more at the high end, because the DIY motor's steel core is not priced.

## Dependency check

The report flags every bought part with fewer than two listed suppliers.

- **One supplier listed:** the used Pix32 v5 (one eBay listing); the 2-layer board (JLCPCB only); the GNSS patch board (the same fab). Action: add a second fab (PCBWay or another, not priced yet) and a second listing for the autopilot.
- **No supplier listed:** the ESC, propellers, charger, LiPo bag, transmitter, tag battery and passives kit. These are research gaps, not decisions.

## Roadmap with gates

Each stage starts only when the previous gate passes. The test results go into the pass note in [passes.json](../bom/passes.json).

1. **Structure and tag (now).** Gate: printed parts pass bench load and drop tests; the tag runs one hour on the bench; Wi-Fi range is measured in the field.
2. **Motor research.** Gate: thrust per watt is measured against a retail 2207 with the same prop; the steel core is priced; the motor runs 10 minutes at a safe current with no overheating; bearing play is checked after an hour.
3. **Own ESC, bench only.** Gate: AM32 runs on the board at low voltage with a current limit; a full-throttle test passes with props off; no LiPo until a reviewer has checked the build.
4. **Own flight controller.** Gate: it runs in simulation and on the bench; the firmware port is reviewed; no flight until the review and simulation tests pass, as [AGENTS.md](../AGENTS.md) requires.
5. **Battery packs.** Not recommended now. Needs a trained reviewer first.

## Rules that keep the pipeline replaceable

1. Keep design files in this repo: schematics, layouts, Gerbers, OpenSCAD or STL files, firmware, and the BOM.
2. Every bought part has two listed sources, or a note on why it has only one.
3. Every made part names its process and its material inputs in the catalog, so its cost moves when a material price moves.
4. Do not name hardware after a brand you do not own. The Pixhawk name is reported as a trademark. Check with the PX4 project before using it.
5. Check licenses before reusing a design. PX4's Pixhawk hardware designs are reported as CC BY-SA 3.0. Verify this in the official repository before reusing anything.

## The Pixel 8a

The owner bought a used Pixel 8a for $250. It is about 188 g by most spec sheets. Two options:

- **As the drone's onboard computer and camera (pass 4).** It replaces the Pi Zero and camera at a higher cost, and brings a better camera, GNSS, IMU and compute. Costs: weight, a phone battery on a drone (fire and crash risk), and a MAVLink bridge to the autopilot that must be built and tested.
- **As the rider's companion.** The owner's existing phone already fills this role for $0, so the Pixel adds nothing here.

The model assumes the Pixel is for the drone. Confirm this, because it decides which pass applies.

## Lab and club resources

FAU's engineering building and the IEEE club have 3D printers. That is the first pipeline stage. What else they can provide is listed in [lab-access.md](lab-access.md).

## Assumptions and gaps

- The prices are search snapshots. Confirm them before buying.
- Not priced: the DIY motor's steel core, the tag battery, the PETG price (a placeholder), the ESC power stage, and the connectors.
- No CAD, PCB or firmware file has been opened or checked, because this environment has no KiCad or OpenSCAD. Any design file is unverified until it is opened and rendered at the lab.
