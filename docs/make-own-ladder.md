# Make or own: the ladder for each part

For each part on the list, this doc gives what it costs to buy (with the date that price was seen), what it costs to make or own (from the model), and what can realistically be made at home. Costs come from [bom/materials.json](../bom/materials.json) and [bom/catalog.json](../bom/catalog.json). For the factory and minimum-order side, see [supply-side.md](supply-side.md).

Read the dates first. Only 10 of the 51 sourced prices in the model are dated within the last 12 months ([price-audit.md](price-audit.md)). Treat every bought price as provisional until it is re-checked at the seller.

## Summary

| Part | Can it be made at home? | Cheapest bought route (date seen) | Own route (model) | Verdict |
|---|---|---|---|---|
| Silicon chips in general | Design and firmware, yes. The silicon, no. | See the chips section | Custom digital blocks through a shuttle (about EUR 70 per tile, undated) | Buy the chips, own the design, and keep two sources. |
| ESP32 (MCU and Wi-Fi radio) | No, the radio is silicon | Module $2.01 to $3.06 (LCSC, fetched 2026-10-10). Bare ESP32-C3FH4 $1.30 to $2.50 (undated) | Own board and firmware | Buy. For the tag, the CH592 BLE chip ($0.46 to $0.95) is the bigger saving if BLE range is enough. |
| LoRa chip | No, the RF is silicon | SX1262 module $4.10 to $7.99 (undated) | Software LoRa modem on an SDR, plus a radio | Skip LoRa for version 0. |
| GPS (GNSS) | No, the RF and baseband are silicon | Bare M9N $10.99 to $16.04. Clone ATGM336H $1.82 to $3.24 (both undated; the clone is untested) | Own board, factory-assembled with a bare M9N: $15.54 to $28.59. Software receiver: about $133 to $145 | Build the own board. It replaces a $54.99 to $74.90 retail board. |
| Autopilot | Board and firmware, yes. Sensors, no. | Used Pix32 v5 $149. New $147 to $263 (undated) | Own board: $12.37 to $47.94 hand-assembled, or $15.69 to $45.21 factory-assembled, plus a firmware port | Factory-assembled, after simulation and bench tests. |
| ESC | Yes: MCU, MOSFETs, drivers, board, AM32 firmware | Retail 4-in-1 not found (placeholder $25 to $55) | Own: $12.40 to $81.79 hand-assembled, or $16.20 to $80.15 factory-assembled. MOSFET price is a placeholder | Price the MOSFETs, then bench at low voltage. |
| Transmitter | Yes: MCU, 2.4 GHz module, gimbals, case, open firmware | Retail ELRS transmitter (placeholder $60 to $120) | Own: $12.88 to $49.12 | After the ESC. Test the kill path. |
| Motors | Yes, as outrunners | T-Motor V2207 $10 to $13.50 each (undated) | Retail parts: $11.91 to $35.17 each. Factory magnets and bearings with a lab-etched stator: $2.57 to $12.40 | Build only with factory parts. Measure thrust per watt first. |
| Steel stator core | Yes: etched or cut laminations | Electrical steel $1.44 to $2.09 per kg (Q2 2026 benchmark). Factory cores $0.99 to $1.99 at 1,000 pieces | Lab etching: about $0.24 to $1.05 with steel (unverified) | Etch a test coupon in the lab first. |
| Lithium cells | No, cell making is hazardous | US distributor EVE 30P $3.89 to $4.99. Drone packs $24 to $38 (both undated) | Pack assembly, protection and testing only | Buy domestic. Salvage only for the tag, after testing. |

## What you can own, and what you cannot

You can own the design, the board, the firmware, the choice of parts, the second sources and the documentation. A factory can assemble your design from its own parts stock, which is the shortest practical path from chip maker to finished board.

You cannot make these at home:

- MEMS sensors: IMU, barometer, magnetometer.
- Radio silicon: Wi-Fi, Bluetooth, LoRa, 2.4 GHz and GNSS receivers.
- MCU and MOSFET silicon.
- Lithium cells (see below).

Custom chips are possible in a shared shuttle. Tiny Tapeout's calculator lists a digital tile at EUR 70, a EUR 300 development kit and EUR 15 shipping (undated). A tile holds a small digital block, not a microcontroller or a radio.

Chip supply is a dependency. Distributors quote 45 to 53 weeks for the ICM-42688-P IMU. Keep two sources for each chip and buy spares before a build.

Salvage is a real source: crashed flight controllers (MCU, IMU, regulators), phones (GNSS, IMU, camera, Wi-Fi, cell, magnets) and old motors (wire, laminations). Test every salvaged part.

## ESP32 and the tag radio

- **Buy the module:** ESP32-C3-MINI-1-N4 at $3.06 for one and $2.01 at 1,300 (LCSC page fetched 2026-10-10).
- **Buy the bare chip:** ESP32-C3FH4 with 4 MB flash in the package, $2.50 for one to $1.30 per reel (undated). It needs a crystal, RF matching and an antenna. That saves about $0.70 per unit at volume and adds RF design work.
- **Swap to BLE:** the WCH CH592 RISC-V chip with BLE 5.4 is $0.91 for one and $0.50 at 1,000 (LCSC, 19,237 in stock, undated). The drone's Pi Zero 2 W has BLE. Measure BLE range in the field before switching.
- **Own:** the board, the firmware and the link protocol.

## LoRa chip

- **Buy:** SX1262 modules at $4.10 to $7.99 (undated). The bare chip is not verified for 2026.
- **Own:** the modem in software. gr-lora_sdr implements the LoRa physical layer in GNU Radio under GPL-3.0. The radio still needs hardware.
- **Verdict:** skip LoRa for version 0.

## GPS (GNSS)

- **Retail board:** Holybro M9N at $54.99 to $74.90 (undated).
- **Own board:** a bare u-blox NEO-M9N ($10.99 to $16.04), a ceramic antenna (placeholder), passives and a 2-layer board, assembled by the board factory. The model's total is $15.54 to $28.59. It has no compass yet.
- **Clone:** ATGM336H at $1.82 to $3.24 (undated, untested). It is used in the version 2 tag. Field-test it against the M9N on the same antenna first.
- **Software receiver:** an RTL-SDR V4 ($39.95 to $44.95, mid-2026), a filtered L1 amplifier ($93 to $99) and a patch antenna, about $133 to $145 in total. GNSS-SDR (GPL-3.0) does the signal processing. This route is for learning, not saving.

## Autopilot

- **Buy:** a used Pix32 v5 for $149. A new Pix32 v6 is $146.99 to $262.99. Both undated.
- **Own board:** STM32H743 ($5.90 to $9.38), ICM-42688-P ($3.07 to $6.50), passives and a 4-layer board ($1.40 to $15 per board).
  - Hand-assembled: $12.37 to $47.94.
  - Factory-assembled: $15.69 to $45.21. Factory assembly suits the fine-pitch MCU and the LGA IMU.
- **Not costed:** barometer, magnetometer, regulators, SD card, connectors and the firmware port.
- **Firmware:** PX4 (reported BSD 3-clause) or ArduPilot (reported GPLv3). Read the LICENSE files. Do not use the Pixhawk name for your own board.

## ESC

- **Own design:** four AT32F421 MCUs ($0.43 to $1.37 each), four FD6288Q three-phase gate drivers ($0.27 to $0.67 each, in stock at the board factory), 24 MOSFETs (placeholder $0.30 to $1.75 each), passives and a 4-layer board.
  - Hand-assembled: $12.40 to $81.79.
  - Factory-assembled: $16.20 to $80.15.
- **The range is the MOSFET price,** not the design. Use LCSC's parametric search for 30 V PDFN5x6 parts.
- **Firmware:** AM32 supports the AT32F421. Check its LICENSE.
- Test at low voltage with a current limit, with props off. No LiPo until a reviewer has checked the build.

## Transmitter

- **Own:** an ESP32-C3 ($2.01 to $3.06), a 2.4 GHz module ($3.22 to $13.98), four gimbal pots (placeholder), a protected cell, a 2-layer board and a printed case. The model's total is $12.88 to $49.12.
- **Firmware:** ELRS (reported GPL-3.0) and EdgeTX (reported GPL-2.0). Check the LICENSE files and the MCU support list before ordering.
- **Checks:** 2.4 GHz output must meet the regulations. The kill path must work at range before any flight.

## Motors

- **Buy:** T-Motor V2207 V2 at $10 to $13.50 each (undated). Factory 2207 motors are about $11 at a 10-piece minimum, so buying complete motors from a factory saves nothing.
- **Own, retail parts:** $11.91 to $35.17 per motor. Miniature 4 x 9 x 4 mm bearings at retail ($3.00 to $4.38 each) and magnets at distributor prices make this dearer than a T-Motor.
- **Own, factory parts:**
  - Magnets from a factory ($0.02 to $0.10 each at 1,000), bearings from a factory ($0.16 to $0.88 each at 100), and a lab-etched stator. The model's total is $2.57 to $12.40 per motor.
  - With factory stator cores instead: $3.32 to $13.61, but about $1,000 to $2,000 of cash at the 1,000-piece minimum.
- **Target:** magnets by weight and salvaged wire and shaft bring it to $2.68 to $8.45.
- **Bells:** the printed bell is for the thrust stand only. A flight motor needs a metal bell, which is not priced.
- **Verdict:** build with factory parts, and measure thrust per watt against a T-Motor on the same prop first ([motors-plan.md](motors-plan.md)).

## Steel stator core

- **Material:** electrical steel at $1.44 to $2.09 per kg (Q2 2026 benchmarks). A 25 g core is about $0.04 to $0.05 of steel.
- **Lab etching:** photo-etch thin laminations with ferric chloride, the same setup as PCB etching. Etching vendors say it suits prototypes and thin laminations. No independent data for silicon steel was found. The model uses a $0.20 to $1.00 placeholder for resist and etchant.
- **Laser cutting:** needs a fiber laser or a service. Most makerspace CO2 lasers cannot cut steel.
- **Factory cores:** $0.99 to $1.99 at 1,000 pieces, plus a drawing and 10 to 12 weeks of tooling. Only as a group order.
- **Salvage:** laminations from old motors. Transformer steel is usually grain-oriented, which suits motors less well.

## Lithium cells

- **Why not make cells:** the electrolyte, lithium hexafluorophosphate, turns into hydrogen fluoride with moisture or heat. A small release in a closed room can reach acute exposure levels. Cell making needs a dry room and protective equipment.
- **Why not import cells from a factory:** shipping guides say standalone cells fly on cargo aircraft only, at 30 percent charge or less. Sea freight is slow. Factory listings ($1.14 to $2.20) are not verified as genuine.
- **Buy:** EVE 30P from a US distributor at $3.89 to $4.99 (undated). Drone packs are $24 to $38 (undated).
- **Own:** pack assembly, protection ($2.39 to $7.19 for a TP4056 module), balancing and testing.
- **Salvage:** laptop and power-tool cells, tested, for the tag only. Never in the drone.

## What it adds up to

From [cost-reduction.md](cost-reduction.md):

- **Pass 8, own most (hand-assembled):** $275.09 to $623.11 per drone, 48 percent made in-house.
- **Pass 10, closer to the factory:** $207.86 to $534.21 per drone. The cash at minimum orders is $332.20 to $934.98, and 51 percent of the cost is the owner's design. Still over $100.
- **The levers left, in order:**
  1. The ESC MOSFET price.
  2. The charger and LiPo bag (placeholders).
  3. The flight battery, which is bought.
  4. The camera and Pi.
  5. Duty on factory orders.

## Next steps

1. Price 30 V PDFN5x6 MOSFETs on LCSC.
2. Ask two factories for magnet and bearing quotes.
3. Etch a lamination coupon.
4. Field-test the CH592 BLE link and the ATGM336H against the M9N.
5. Read the LICENSE files for PX4, ArduPilot, ELRS, EdgeTX, AM32 and GNSS-SDR.
6. Re-check the 41 undated or stale prices.
