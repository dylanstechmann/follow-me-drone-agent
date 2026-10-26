# Motor plan (DIY outrunner research)

The aim is to understand motors well enough to build them, measure them, and judge whether building them is worth it. It is not a cost win yet. This plan is for a learning and dependence project first.

## What the model says

For one 2207-class outrunner, from [bom/catalog.json](../bom/catalog.json) and [bom/materials.json](../bom/materials.json). Two parts routes:

| Input | Quantity per motor | Retail and distributor parts (USD) | Factory parts and lab stator (USD) |
|---|---|---|---|
| 0.3 mm enamelled copper wire | 40 g | 0.47 to 1.78 | 0.47 to 1.78 (or salvaged) |
| N52 neodymium discs, 10 x 2 mm | 14 | 3.64 to 10.92 (distributor) | 0.28 to 1.40 (factory, 1,000 minimum) |
| Miniature bearings, 4 x 9 x 4 mm (684ZZ) | 2 | 6.00 to 8.76 (retail) | 0.32 to 1.76 (factory, 100 minimum) |
| Steel shaft | 1 | 1.00 to 3.00 (placeholder) | 1.00 to 3.00 (placeholder) |
| Electrical steel for the stator | 25 g | 0.04 to 0.05 | 0.04 to 0.05 |
| Stator laminations | 1 set | 0.50 to 2.00 (laser-cut placeholder) | 0.20 to 1.00 (lab etch placeholder) |
| Printed bell (PLA, thrust stand only) | 30 g | 0.26 to 0.54 | 0.26 to 0.54 |
| **Total, with 30 percent waste on the high end** | | **11.91 to 35.17** | **2.57 to 12.40** |

A retail T-Motor V2207 V2 is $10 to $13.50 (undated). Only the factory-parts route is cheaper. The 14-magnet count is an assumption for a 2207-class outrunner, so check it against the chosen stator design.

**Correction:** an earlier version used 608 skateboard bearings. They are 22 mm across, the same size as a 2207 stator, so they cannot fit. Small drone motors use miniature bearings around 4 x 9 x 4 mm.

**Laminations:** most makerspace CO2 lasers cannot cut steel. Use a fiber laser, a cutting service, or photo-etching with ferric chloride (unverified for silicon steel, so test a coupon first). Factory stator cores are $0.99 to $1.99 at a 1,000-piece minimum, which is about $1,000 to $2,000 of cash.

**Bells:** a printed bell is for the thrust stand only. A flight motor needs a metal bell, which is not priced.

## Design options

- **Steel-core outrunner.** Closest to commercial motors, and the most efficient option. Needs a laminated stator core, from salvage or a laser-cut stack. The core is the main unknown in cost and in build effort.
- **Coreless motor.** No steel core, so simpler to build and cheap in material, but usually less efficient. Good for learning the winding and magnet geometry first.

Start with whichever has a core source you can actually get. Do not start with a design that needs parts you cannot buy.

## Magnets and wire

- N52 discs are brittle and very strong. They can pinch fingers hard and shatter if they snap together. Keep them away from pacemakers, phones, cards and drives, and handle them with spacers.
- Hard-drive voice-coil magnets are often NdFeB, but grade and strength vary. Test before using salvaged magnets.
- Buy magnet wire from a supplier that lists 0.3 mm round wire. The model's wire price range is wide (see the materials file), so ask for a quote before ordering.

## Measurement plan

Build the thrust stand first. It is in the catalog as a printed base plus a 1 kg load cell with an HX711 amplifier. Calibrate it with a known mass before any motor test. The printed jig exists as an adjustable model, `cad/thrust_stand.scad` (see [3d-printing.md](3d-printing.md)); it is unprinted, and the load cell's size and bolt holes must be measured and set before printing.

For each motor:

1. Mount it on the stand with a balanced prop, and check the prop for balance first.
2. Run a bench power supply with a current limit set below the motor's safe current. Start at a low current and step up.
3. At each throttle step, record thrust (grams), voltage, current and motor temperature.
4. Compute thrust per watt at each step.
5. Repeat with a retail 2207 on the same prop and the same supply.
6. Run 10 minutes at a safe current and check the temperature and any bearing play.

Props stay off during any test that is not a balanced prop test. Keep eyes and fingers away from the prop disc.

## Gates

A DIY motor is adopted only if all of the following hold:

- Thrust per watt matches or beats the retail motor on the same prop.
- It runs 10 minutes at a safe current with no overheating.
- Bearing play is within limits after one hour.
- The total cost, including the steel core, is at or below the retail motor's cost.
- No winding or magnet fault appears in the bench runs.

Until those gates pass, the DIY motor stays out of any drone pass. The pass report already shows the research track as pass 6.

## Safety

- No flight. Motors are tested on the stand only.
- A bench supply with a current limit, always.
- Balanced props and guards on, eye protection on.
- Magnet handling with spacers and away from electronics.
- Let windings and motors cool before touching them.
