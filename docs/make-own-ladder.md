# Make or own: the ladder for each part

For each part on the list, this doc gives three things: what it costs to buy (with the date that price was seen), what it costs to make or own (from the model), and what can realistically be made at home. Costs come from [bom/materials.json](../bom/materials.json) and [bom/catalog.json](../bom/catalog.json). Dates are in [price-audit.md](price-audit.md).

Read the dates first. Only 9 of the 39 sourced prices in the model are dated within the last 12 months. The rest are undated, year-only or older, so treat every bought price as provisional until it is re-checked at the seller.

## Summary

| Part | Can it be made at home? | Cheapest bought route (date seen) | Own route (model) | Verdict |
|---|---|---|---|---|
| Silicon chips in general | Design and firmware, yes. The silicon, no. | See the chips section | Custom digital blocks through a shuttle (about EUR 70 per tile, not priced here) | Buy the chips, own the design. |
| ESP32 (MCU and Wi-Fi radio) | No. The radio is silicon. | ESP32-C3-MINI-1 at $2.01 to $3.06 (LCSC page fetched 2026-10-10) | Own board and firmware | Buy the module, own the board and firmware. |
| LoRa chip | No. The RF is silicon. | SX1262 module at $4.10 to $7.99 (undated) | Software LoRa modem on an SDR, plus a radio | Skip LoRa for version 0. Use Wi-Fi. |
| GPS (GNSS) | No. The RF and baseband are silicon. | M9N at $10.99 to $16.04 (undated). Clone ATGM336H at $1.82 to $3.24 (undated, untested) | Software receiver: about $133 to $145 of hardware | Buy the chip, and test the clone. Build the software route to learn. |
| Autopilot | Board and firmware, yes. Sensors, no. | Used Pix32 v5 at $149 (undated). New $147 to $263 (undated) | Own board at $12.97 to $36.24, plus a firmware port | Stage 4: after simulation and bench tests. |
| ESC | Yes: MCU, MOSFETs, drivers, board, AM32 firmware | Retail 4-in-1 not priced (placeholder $25 to $55) | Own 4-in-1 at $15.92 to $82.18 (MOSFET prices are placeholders) | Stage 3: bench at low voltage first. |
| Transmitter | Yes: MCU, 2.4 GHz module, gimbals, case, open firmware | Retail ELRS transmitter (placeholder $60 to $120) | Own at $12.88 to $49.12 | After the ESC. Test the kill path. |
| Motors | Yes, as outrunners | T-Motor V2207 at $10 to $13.50 each (undated) | DIY at $8.41 to $27.81 each. Target route at $4.86 to $10.19 | Research first. Not a saving at retail magnet prices. |
| Steel stator core | Yes: laser-cut laminations | Electrical steel at $1.44 to $2.09 per kg (Q2 2026 benchmark) | About $0.04 to $0.05 of material per core, plus cutting (placeholder) | Yes, if laser cutting is available. |
| Lithium cells | No. Cell making is hazardous. | 18650 at $1.00 to $3.20 (undated). Drone packs $24 to $38 (undated) | Pack assembly, protection and testing only | Buy new cells from known suppliers. Salvage only for the tag, after testing. |

## What you can own, and what you cannot

You can own the design, the board, the firmware, the choice of parts, the second sources, and the documentation. You cannot make the silicon or the RF radio at home. These are the chips and the cells you cannot make:

- MEMS sensors: IMU, barometer, magnetometer. Made on wafer lines.
- Radio silicon: Wi-Fi and Bluetooth in the ESP32, LoRa, 2.4 GHz and GNSS receivers.
- MCU and MOSFET silicon.
- Lithium cells. Making them needs a dry room and handling lithium hexafluorophosphate electrolyte (see the cells section).

Custom chips are possible in a shared shuttle. Tiny Tapeout's calculator lists a single digital tile at EUR 70, plus a EUR 300 development kit and EUR 15 shipping, all undated. A 2026 news post says TTSKY26a was fully taken and TTSKY26b was next. A tile holds a small digital block, such as a motor commutation or sensor interface block. It does not hold a microcontroller or a radio. It is a learning route, not a replacement for the chips above.

Chip supply is a dependency too. DigiKey quotes a 45-week lead time for the ICM-42688-P IMU, and Mouser 53 weeks. Owning more chip-level designs means owning more supply risk, so keep two sources for each chip and buy spares before a build.

Salvage is a real source. Crashed flight controllers carry an MCU, an IMU and regulators. Phones carry GNSS, an IMU, a camera, Wi-Fi, a battery and magnets in the speaker and vibration motor. The condition is unknown, so test before use.

## ESP32 (MCU and Wi-Fi)

- **Buy:** ESP32-C3-MINI-1-N4 at $3.06 for one piece and $2.01 at 1,300 pieces, from an LCSC page fetched 2026-10-10. The page has no price date, but the fetch is from today. Stock 3,563.
- **Own:** the board around the module, the firmware, and the link protocol. The module's Wi-Fi radio stays bought.
- **Model:** the module is $2.01 to $3.06 in the tag and in the transmitter.
- **Why not make it:** the Wi-Fi radio is silicon. A RISC-V core on an FPGA can take over the non-radio logic, but the FPGA is not priced here.

## LoRa chip

- **Buy:** SX1262 modules at $4.10 (Wifiblemodule, with a validity field to August 2027) to $7.99 (Waveshare), both undated. The bare SX1262 is $9.04 at DigiKey, probably a 2018 snapshot, so unverified for 2026.
- **Own:** the LoRa modem in software. The gr-lora_sdr project implements the LoRa physical layer in GNU Radio under GPL-3.0. It reportedly handles spreading factors 5 to 12, though SX126x chips cannot do SF5 or SF6. That makes the modem yours, but the radio still needs hardware: a receive-only RTL-SDR costs about $40, and a transmit-capable SDR is not priced here.
- **Verdict:** skip LoRa for version 0. Use the ESP32's Wi-Fi to reach the drone's access point at follow distance. Keep LoRa as a later option if Wi-Fi fails in the field.

## GPS (GNSS)

- **Buy, bulk u-blox:** NEO-M9N at $10.99 (ten units) to $16.04 (one unit), undated. The Holybro finished board is $54.99 to $74.90 (undated). The NEO-M8N is not cheaper: Mouser lists $34.06, and Symmetry $26.55 at ten units. Check its lifecycle status before using it.
- **Buy, clone:** ATGM336H at $1.82 (1,000 or more) to $3.24 (one piece), LCSC, undated. It is a clone family with lower performance than u-blox and is untested here. Test it against the M9N in the field before trusting it.
- **Own, software receiver:** an RTL-SDR V4 at $39.95 (about May 2026) to $44.95 (about August 2026), plus a filtered L1 amplifier at $93 to $99 (undated), plus a patch antenna on a bought board at $0.40 to $0.70. The total is about $133 to $145. GNSS-SDR is an open-source software receiver under GPL-3.0 that tracks GPS L1 C/A from RTL-SDR-class dongles. Its last push was reported in May 2025, so check the current activity first.
- **Verdict:** buy the chip, and test the clone. Build the software receiver to learn the signal processing, not to save money. The software route costs about 10 times the chip.

## Autopilot

- **Buy:** a used Holybro Pix32 v5 for $149 (one listing, undated). The new Pix32 v6 is $146.99 to $262.99 (undated). Holybro lists the v5 as discontinued.
- **Own, the board:** an STM32H743 at $5.90 to $9.38 (undated), an ICM-42688-P IMU at $3.07 to $6.50 (the high end dated 2026-08-23), passives, and a 4-layer board at a placeholder $2 to $6. The model's total is $12.97 to $36.24 (waste allowance on the high end).
- **Not costed:** the barometer, magnetometer, regulators, SD card, connectors, the GNSS (bought separately), and the firmware port.
- **Firmware:** PX4 is reported under the BSD 3-clause licence, and ArduPilot under GPLv3. Both come from forum summaries. Read the LICENSE files before shipping or reusing code. The name Pixhawk is reported as a trademark, so do not use it for your own board.
- **Verdict:** stage 4. Build the board only after the follow logic runs in simulation. Bench-test with props off, and never fly it before review.

## ESC

- **Buy:** no retail 4-in-1 price was found. The model's placeholder is $25 to $55.
- **Own:** an AT32F421 at $0.43 (1,000 or more) to $1.37 (one piece), undated. AM32 lists the AT32F421 as supported. The power stage is 24 MOSFETs (six per motor) and four three-phase gate drivers, both placeholders. The MOSFET high end is a June 2026 retail price of $1.75. A bulk price was not found. The model's total is $15.92 to $82.18. The width of that range is the price gap, not the design.
- **Verdict:** stage 3. Price bulk MOSFETs and gate drivers first. Test at low voltage with a current limit, with props off. No LiPo until a reviewer has checked the build.
- **Licence:** AM32 is open source. Check its licence file before reuse.

## Transmitter

- **Buy:** a retail ELRS-compatible transmitter, placeholder $60 to $120, not priced in research.
- **Own:** an ESP32-C3 at $2.01 to $3.06, a 2.4 GHz module at $3.22 to $13.98 (an SX1280 chip or module), four gimbal pots as placeholders at $0.50 to $2 each, one protected cell with a charge board, a 2-layer board, and a printed case. The model's total is $12.88 to $49.12.
- **Firmware:** ELRS is reported as open source, with the main repository under GPL-3.0 (a third-party index, March 2024 snapshot). The hardware licence is not confirmed. EdgeTX firmware is reported under GPL-2.0. Check both LICENSE files.
- **Checks before use:** confirm that the chosen MCU is supported by the firmware, that the 2.4 GHz output meets the regulations, and that the kill path works at range. The transmitter is safety-critical.
- **Verdict:** after the ESC. Bench-test the link before any drone uses it.

## Motors

- **Buy:** T-Motor V2207 V2 at $10 to $13.50 each (undated).
- **Own, retail-material route:** 40 g of 0.3 mm wire, 14 N52 discs bought per disc at $0.26 to $0.78 each, two skate-size bearings, one shaft, a laser-cut 25 g stator core, and a 30 g printed bell. The model's total is $8.41 to $27.81 per motor, so four motors are $33.64 to $111.24.
- **Own, target route:** magnets bought by weight. Raw neodymium metal was reported at $129.76 to $140.88 per kg in September 2026, and N52 vendor pricing at $95 to $130 per kg (undated). That is about $1.57 to $2.15 per motor of magnets instead of $3.64 to $10.92. Add salvaged wire and shaft, and the model's total is $4.86 to $10.19 per motor.
- **Bearings:** skate-size 608 bearings at $1.25 to $1.55 each (VXB at $9.99 for eight, eBay timestamp February 2026).
- **Verdict:** research first. At retail magnet prices the DIY motor is not cheaper. The target route is cheaper only if a magnet supplier quotes by weight and the wire and shaft can be salvaged. Measure thrust per watt against the T-Motor before using any DIY motor. See [motors-plan.md](motors-plan.md).

## Steel core

- **Buy:** electrical steel at $1.44 per kg (China) to $2.09 per kg (Germany), Q2 2026 benchmarks from market research. Small lots pay a premium. A 25 g stator core is about $0.04 to $0.05 of material.
- **Own:** laser-cut laminations. The cutting cost is a placeholder at $0.50 to $2 per stator. Ask FAU or IEEE whether a laser cutter is available.
- **Salvage:** laminations from old motors and transformers. Check the grade and the thickness. Transformer steel is usually grain-oriented, which suits motors less well than the non-oriented grades.
- **Skip:** stamping. A die costs more than the whole run.
- **Verdict:** yes. The material is cheap. The cutting is the question.

## Lithium cells

- **Why not make cells at home:** the electrolyte is lithium hexafluorophosphate in an organic solvent. Moisture or heat (reported onset near 70 degrees C) turns it into hydrogen fluoride. NIOSH's exposure limit for HF is 3 ppm as a 10-hour time-weighted average. The EU's Joint Research Centre reports that a small electrolyte release in a closed room can reach acute exposure levels. Cell making needs a dry room, ventilation and protective equipment. It is not a home project.
- **Buy:** unprotected 18650 cells at $1.00 (China wholesale) to $3.20 (Panasonic-class, bulk-only page). Both undated. Protected cells are $10 to $12. Drone packs (4S 1500 mAh) are $24 to $38 (undated).
- **Own:** pack assembly, protection, balancing and testing. A TP4056 module with DW01A protection costs $2.39 to $7.19 (August 2026 listings at the high end). Protection specs come from listing titles, not datasheets.
- **Salvage:** cells from laptop and power-tool packs are free. Test every cell's capacity and internal resistance. Discard any cell that is swollen, damaged or mismatched. Use salvaged cells for the tag, not for the drone.
- **Verdict:** buy new cells from known suppliers. Own the pack assembly and the testing. Do not fly salvaged cells. Do not build flight packs at home without an experienced reviewer.

## What it adds up to

From [cost-reduction.md](cost-reduction.md):

- **Pass 8, own most:** the made autopilot board, ESC, transmitter and tag battery replace the bought ones. Core cost falls to $267 to $594, and 45 percent of the cost is made in-house. It is still over $100.
- **What remains:** the DIY motors at retail magnet prices ($34 to $111), the Holybro GPS ($55 to $75), the ESC ($16 to $82), the charger and LiPo bag (placeholders, $33 to $70), the transmitter ($13 to $49), the 4S battery ($24 to $38), and the camera and Pi ($40 to $50).
- **Pass 9, the target motors:** core cost falls to $253 to $524.

The levers, in order of size: the motor magnet route, the GPS chip, the ESC MOSFET price, the charger and LiPo bag, and then the flight battery, which cannot be made here.

## Next steps

1. Price bulk MOSFETs and gate drivers for the ESC. Both are placeholders.
2. Ask two magnet suppliers for a quote by weight for N52 10 x 2 mm discs.
3. Bench-test the ATGM336H against the M9N, outdoors, on the same antenna.
4. Ask FAU engineering or IEEE about a laser cutter and a CNC mill.
5. Check the MCU for the transmitter against the ELRS and EdgeTX support lists.
6. Read the LICENSE files for PX4, ArduPilot, ELRS, EdgeTX, AM32 and GNSS-SDR. The licences above come from forum and index summaries.
7. Re-check the undated prices. Start with the 30 that are not fresh.
