# Cost reduction

Budget: $100 (see [budget.md](budget.md)). Every price here comes from [bom/catalog.json](../bom/catalog.json), where each row has its own source links. Prices were searched on 2026-10-10. Most sources are undated snapshots or older listings, so check every price at the seller before buying.

Re-run the report after any change:

```
PYTHONPATH=src python3 -m follow_me.bom
```

## Status labels

- **snapshot**: a price seen in a search result or a listing. Date unknown.
- **official**: a manufacturer's list price.
- **estimate**: my calculation from a stated assumption, such as grams of filament.
- **placeholder**: a guess, counted in totals so the total is not too low. Replace it with a quote.
- **owned**: already owned, counted at $0. A new purchase is not in the budget.
- **unpriced**: not priced, counted as $0. Reported separately so it is not forgotten.

## The method

Each pass starts from the pass it is based on and makes one kind of change:

1. Buy less of the same thing: drop the features the logs do not need yet.
2. Buy used or refurbished, only for parts whose condition you can check before flight.
3. Substitute a cheaper equivalent: a smaller computer, a nano receiver, a bare module instead of a finished board.
4. Repurpose what you already own, such as a spare phone.
5. Print instead of buy: structure, mounts, enclosures.
6. Test on the bench before buying the parts that carry risk.

A cheaper part is only a saving if its risk is tested. Each pass in [passes.json](../bom/passes.json) records the risk it adds.

## Pass results

Core costs in USD, low to high. Optional items are listed separately in the report.

| Pass | Based on | Core low | Core high | Change vs base (low to high) | Budget | Placeholders |
|---|---|---|---|---|---|---|
| pass0 retail autopilot | none | 570.60 | 1,003.75 | none (starting point) | over | 8 |
| pass1 used autopilot, Pi Zero streams video | pass0 | 508.66 | 777.56 | -61.94 to -226.19 | over | 8 |
| pass2 printed frame and guards | pass1 | 481.66 | 724.56 | -27.00 to -53.00 | over | 7 |
| pass3 bench-first kit | pass2 | 78.18 | 129.54 | -403.48 to -595.02 | fits at low prices only | 2 |
| pass4 owned phone as drone computer | pass2 | 446.66 | 684.56 | -35.00 to -40.00 | over | 8 |

The optional Tello (refurbished, $79 to $139) is in pass 3 but not in the core totals.

### What each pass does and the risk it adds

- **Pass 0, retail autopilot.** Every part a first complete build would want, priced from retail. The flight controller alone is $147 to $263.
- **Pass 1, used autopilot.** Replaces the new flight controller with a used v5 at $149, the Pi 5 with a Pi Zero 2 W, and drops the close-range ToF. The Pi Zero only streams video, so detection runs on a phone or laptop on the ground. Risk added: control now depends on the ground link, so the autopilot's own link-loss failsafe must be tested in simulation first.
- **Pass 2, printed frame and guards.** Replaces the commercial frame placeholder with printed parts, estimated at $2 to $4 of filament. Risk added: printed parts fail differently from moulded ones, so each load-bearing part needs a bench stress test. See [3d-printing.md](3d-printing.md).
- **Pass 3, bench-first kit.** Removes every flying part and keeps what the desk tests need: a Pi Zero, a camera, the tag, filament and a camera mount. This is the one pass that fits $100 at low prices. Flying waits until the logs justify it.
- **Pass 4, owned phone as drone computer.** A spare Android phone replaces the Pi Zero and the camera. Risk added: the phone adds weight, needs its own battery and mounting, and its heat and power behaviour is untested.

## Findings

- **The used autopilot does not save money at the low end.** A used Pix32 v5 is $149 from one listing. The new v6 starts at $146.99. The pass 1 saving comes from dropping the Pi 5 (about $55 at the low end) and the ToF, not from the used board.
- **A flying drone does not fit in $100 with any pass so far.** The flight controller, the GPS, and the transmitter together cost more than $100 on their own. The $100 budget covers the bench kit and one tag.
- **The transmitter is the largest placeholder.** Its placeholder is $60 to $120. Owning an ELRS-compatible transmitter removes it, which is why that question is in the progress log.
- **Each tag costs $27 to $52.** The Heltec board and the bare GNSS module are snapshot prices. The antenna board and the battery are placeholders, so they are the least certain part of the tag cost.
- **Printing the frame and mounts saves $27 to $53 net,** after the guards and camera mount are added. This is an estimate until real grams are measured.

## Ideas not yet priced

- A PX4-compatible autopilot cheaper than the current options. This is the biggest open question for a flying drone.
- A 4-in-1 ESC and a 5-inch propeller set, both still placeholders.
- A balance charger and a LiPo bag, both placeholders.
- Access to a printer. If you have a printer, the printing rows stay as they are. If you use a print service, replace them with its quotes.
- A lab or makerspace that lends tools or parts. Whether FAU or its IEEE chapter offers one is unconfirmed.

## Repeating the loop

1. Check a price at the seller and update its row in [catalog.json](../bom/catalog.json). Change its status to match the source.
2. Add a new pass that is based on the latest one, and list its adds and removes with the reason and the risk.
3. Run the report and check the numbers in this doc.
4. Commit the catalog, the passes, and this doc together.
