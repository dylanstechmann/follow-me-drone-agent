# 3D printing

Printing is the cheapest way to make structure, mounts and enclosures. Do not print the parts that carry the most energy or the most current, such as motors, ESCs, batteries and autopilots. Buy those.

Everything here is a starting point to test. No number in this doc has been measured on a printed part yet.

## Printer access

The owner has access to 3D printers at FAU's engineering building and at the IEEE club. Ask about models, materials, charges and rules (see [lab-access.md](lab-access.md)). Other options:

- Your own printer. Filament cost only.
- A print service. Replace the printing rows in [parts-catalog.md](parts-catalog.md) with its quotes.

## Materials

| Material | Good for | Watch out for |
|---|---|---|
| PLA | Bench jigs, camera mounts for the bench, indoor tag cases, fit checks | Brittle under impact. Softens at fairly low temperatures, so a sunny parked car or a warm pocket can deform it. |
| PETG | First flight-frame prototypes, prop guards, mounts that take impacts | Tougher than PLA. Can string and needs dry filament. |
| ASA | Outdoor parts that see sun | Needs ventilation when printing. Stiff and warp-prone without an enclosure. |
| TPU | Vibration isolation, straps, landing-gear feet, bumpers | Flexible, so stiff designs need a different shape. Slow to print. |
| Nylon or CF-nylon | Stiffer arms and mounts once a design is proven | Absorbs moisture, so dry it before printing. Carbon-filled versions wear brass nozzles, so use a hardened nozzle. |

## Parts to consider

| Part | Function | Material to test first | Risk if it fails | Test before flight |
|---|---|---|---|---|
| Frame plates and arms | Carries everything and absorbs crash energy | PETG, then CF-nylon if it flexes too much | High | Bench load test. Drop test on a soft surface with props off. |
| Motor mounts | Holds the motors and takes their vibration | PETG or CF-nylon, with threaded inserts for the screws | High | Run the motors at low throttle with props off and check for cracks. |
| Prop guards | Keeps props away from people and objects | PETG or TPU | Medium | Impact test at low speed. Check for any contact with props. |
| Battery tray and straps | Keeps the battery from moving in a crash | TPU straps, PETG tray | High. A moving battery can short or catch fire. | Pull and shake test. No pinch points near props. |
| Camera mount | Holds the camera steady and isolates vibration | PLA on the bench, PETG or TPU grommets for flight | Low to medium | Check the video for jello and shake. |
| Landing gear | Ground contact | TPU or PETG | Low | Drop test from a low height. |
| GNSS antenna mount | Keeps the antenna clear of props and metal | PLA or PETG | Low | Check the satellite count and fix quality with and without the mount. |
| Tag enclosure | Protects the tag on the rider | PLA indoors, PETG outdoors | Low, but sharp edges hurt on a fall | No sharp edges. Check the battery stays cool while charging. |
| Bench jigs | Motor thrust stand, holders for testing | PLA | None | None |

## Print settings (starting points)

- Layer height of 0.2 mm is a common starting point.
- For stressed parts, use more walls and more infill than a cosmetic part. Test with coupons before trusting a design.
- Orient parts so the load pushes across layers, not peeling them apart.
- Dry nylon and PETG if the air is humid. Wet filament prints weak and noisy.
- Print three small test bars for each design. Break them to see the real strength before printing the full part.
- Record the grams and the print time of each part. Replace the estimates in the catalog with those numbers.

## Costing a part

Printed parts are costed from the raw filament prices in [materials.json](../bom/materials.json):

- PLA at $10.99 to $20 per kg, from 5 kg spools.
- PETG at $15 to $30 per kg. This is a placeholder until a bulk PETG price is searched.

Cost is grams divided by 1000, times the price per kilogram, with 20 percent waste added to the high end. A 150 g PETG frame comes to about $2.25 to $5.40. Time and electricity are not counted yet.

The catalog's printed-part rows are estimates built this way. Measure the real grams in the slicer and replace them before trusting them.

## Safety

- Keep every printed part that is near a prop inside a guard until it has passed its tests.
- Do not fly a part that has not been tested to failure on the bench.
- Keep the printer supervised, especially with nylon and ABS-type materials, which need ventilation.
- Batteries and printed battery mounts: the battery must not be able to move or be crushed in a crash.
- Hot parts burn. Let the nozzle and the bed cool before touching a part.
