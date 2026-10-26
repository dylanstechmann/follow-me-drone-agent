# Tag board plan (PCB)

This is the plan for the first board the owner would design and make: the rider's tag. It is a plan, not a design. No schematic or layout has been drawn or checked, because this environment has no KiCad.

## Scope

The tag reports the rider's position to the drone. Version 0 contains:

- An ESP32-C3-MINI-1 module. Its Wi-Fi links the tag to the drone's access point (see [companion-tiers.md](companion-tiers.md)).
- A NEO-M9N-00B GNSS module, with its own support circuit and a GNSS antenna.
- A single-cell lithium charger and a protected cell connector. The charger IC and regulator are not selected.
- A status LED, a boot and reset button, and test points.
- A programming connector or USB port. Not selected yet.

Not in version 0: LoRa, a display, an IMU, or any sensor beyond GNSS.

## Parts and prices

From [bom/catalog.json](../bom/catalog.json), for one tag:

| Item | Path | Cost (USD) | Note |
|---|---|---|---|
| ESP32-C3-MINI-1 module | bulk | 2.01 to 3.53 | LCSC and DigiKey both listed |
| NEO-M9N-00B bare module | bulk | 10.99 to 16.04 | Largest chip cost; needs a carrier and antenna |
| 2-layer board, 10 x 10 cm | outsourced | 0.40 to 0.70 | One fab listed so far |
| Passives and connectors | bulk | 1 to 3 | Estimate; not searched |
| GNSS antenna and carrier board | retail placeholder | 5 to 15 | Replaced by an own-design patch in pass 7 (unverified) |
| Battery and charge board | retail placeholder | 4 to 10 | Not priced |
| Printed case | make | 0.27 to 0.60 | 25 g of PLA |

The made tag comes to about $23.67 to $48.87. The retail tag, using a HT-CT62 module, comes to about $27.16 to $50.64. The difference is small, because the GNSS module and antenna dominate the cost.

## Board route options

1. **Outsourced 2-layer board (preferred for production).** Cheap per board, with a ground plane. Keep the Gerber and drill files in this repo so another fab can make the same board.
2. **In-house single-sided etch (for iteration).** Copper-clad FR4, ferric chloride and a printer or a photo process. Single-sided only, so it needs jumper wires. The model prices a 100 cm2 board at $1.82 to $15.48, which is more than an outsourced 2-layer board. Use it to test a layout in a day, not to save money.
3. **CNC milling (3018 class or a lab mill).** Good for simple boards and isolation milling. Tool deflection and depth control are the limits. Test a coupon before trusting it.

Test a coupon for each route before the real board: trace width, spacing and drill accuracy.

## Layout constraints to design around

These are general RF and power rules. Check each against the parts' datasheets before layout.

- Keep the ESP32 antenna area free of copper, and do not put a ground plane under it.
- Keep the GNSS antenna far from the Wi-Fi antenna and from the module's switching regulators.
- Put a solid ground plane under the GNSS receiver and keep its supply filtered.
- Keep the battery connector and the charger on one side, away from the antennas.
- Add test points for each supply rail, the UART lines and the boot pin.

## Bring-up checklist

1. Check continuity and shorts before any power is applied.
2. Apply power through a bench supply with a current limit, and check each rail.
3. Confirm the MCU boots and flashes over the programming port.
4. Confirm the GNSS module outputs NMEA on UART and reports a fix outdoors.
5. Measure the GNSS signal strength (C/N0) of the satellites.
6. Confirm Wi-Fi connects to a test access point, then measure range and dropouts.
7. Charge and discharge the cell with the protection in place. Check the temperature.

## Gate

The tag board is accepted when:

- It passes the bring-up checklist with no thermal or power faults.
- It runs for one hour on the bench under load.
- Its Wi-Fi range and dropouts are measured in the field, not on the bench, before any drone test.

## Enclosure

The tag case exists as an adjustable model, `cad/tag_enclosure.scad`, with board posts, a USB slot, strap ears and a push-fit lid (see [3d-printing.md](3d-printing.md)). Its board size, hole positions and component height are placeholders. Set them from the board once it is drawn, and print and test it before use.

## Tools and assumptions

- KiCad is the planned tool. It is free and open source, but it is not installed here, so no layout exists yet.
- The GNSS patch antenna is an unverified design. Measure C/N0 on the module before trusting it.
- Single cells on a tag need a protection circuit. Do not charge an unprotected cell, and do not charge one unattended.
