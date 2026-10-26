# The kinematic follow simulation

`src/follow_me/sim.py` flies a point drone after a rider, using the council's commands. It sits between the replay tool and the SITL gate. It closes the loop: where the drone goes changes what the next reading says. Like the rest of the repo, it was written by AI coding agents at the owner's direction, and nothing here has flown.

## What it is, and what it is not

- **The drone** is a point in a flat local frame, in meters east and north of the track's first fix. Each tick, 0.5 s by default, it does two things, both scaled by the council's normalized commands:
  - it turns at up to 90 degrees per second (the yaw command);
  - it moves along its nose at up to 10 m/s (the forward command).

  Both limits are placeholders, which an autopilot and a real airframe would set.
- **No physics, wind, battery, autopilot or camera.** Climb is ignored. A return-home request is recorded, not flown.
- **The rider** is a track of timed fixes:
  - Each tick, the latest fix no older than 2 s becomes a `phone_gnss` reading, seen from where the drone is, through the same body-frame math as `companion.py`.
  - Older fixes give no reading.
  - While the mode machine allows it (dead reckoning), the drone keeps flying its last command.
- **It does not replace the SITL gate** (decision D02). Passing it says nothing about flight safety.

## Findings: before and after feed-forward (2026-10-26, default settings)

These numbers come from the model with its placeholder limits. They show how the follow logic behaves, not how a real drone would fly.

**Iteration 21 found these problems with the original controller:**
- **The drone trails a moving rider.** The controller acted on distance alone, so the drone settled where its forward command times the top speed equalled the rider's speed.
- **There is a speed ceiling.** The forward command topped out at 0.6, the gain times the target box height minus the deadband, so the drone never passed 6 m/s with the 10 m/s placeholder.
- **A phone alone is degraded.** A 4 m fix has a 16 m² variance, above the mode machine's 9 m² threshold, so every tick is degraded at half gain.
- **Falling behind makes it worse.** The 3 degree heading uncertainty adds variance in proportion to range, so past about 54 m even a 1 m fix is degraded.

**Iteration 27 added feed-forward.** `motion.py` estimates the rider's speed over the ground with a Kalman filter, and the controller adds the part along the drone's nose to its forward command:
- The added share shrinks when the speed estimate is uncertain.
- The approaching part fades out across the follow band, so it cannot push the drone inside the band.
- The mode's gain still scales the whole command.

The table shows where the drone settles behind a rider moving in a straight line, with one fix a second, like a phone:

| Rider | Fix accuracy (one sigma) | Before | With feed-forward |
|---|---|---|---|
| Standing | 1 m | 4.4 m, where it starts, inside the band | 4.4 m |
| 2 m/s | 1 m | 8.0 to 8.2 m | 6.2 to 6.5 m |
| 3 m/s | 1 m | 10.9 m | 6.3 to 6.9 m |
| 4 m/s | 1 m | 16.2 m | 6.7 to 7.4 m |
| 5 m/s | 1 m | 31.2 to 31.6 m | 7.1 to 8.0 m |
| 7 m/s | 1 m | Falls behind without limit | 7.7 to 10.0 m |
| 2 m/s | 4 m, like a phone, degraded | 15.7 m | 10.9 m |
| 3 m/s | 4 m, like a phone, degraded | Falls behind without limit | 16.3 m |

Other cases:
- **A rider who stops suddenly from 4 m/s:** the closest approach is 3.4 m, just inside the band's 3.79 m near edge, because a 1 Hz fix lags the rider. Without the fade, the drone came within 2 m.
- **A 90 degree turn at 4 m/s:** the drone stays 5.1 to 7.6 m from the rider, against 11 to 16 m before.
- **The made-up example ride:**
  - the median distance is 7.0 m, against 20.4 m before;
  - it is in the band 17% of the time, against 7%;
  - it tracks for 98 s of 145, against 64.5 s, because staying close keeps the range term small.

**Iteration 27 also found that noisy fixes bring the drone too close.** A standing rider with made-up 3 m errors on each fix was approached to between 0.3 and 1.8 m in five runs, with or without feed-forward. The drone held 4 to 5 m from where the fixes said the rider was, which can be next to where the rider really was.

## The safety margin (iteration 29)

The council now shows the controller the rider closer than estimated, by 2.5 times the estimate's one-sigma uncertainty (`margin_sigmas`). The drone therefore holds back further when it is less sure where the rider is. If the reported accuracy is honest, 2.5 one-sided sigmas keep the real rider outside the band's near edge about 99% of the time.

Where the drone settles behind a rider moving in a straight line, one fix a second:

| Rider | Fix accuracy | Original | Feed-forward | Feed-forward and margin (now) |
|---|---|---|---|---|
| 2 m/s | 1 m | 8.0 to 8.2 m | 6.2 to 6.5 m | 8.9 to 9.3 m |
| 3 m/s | 1 m | 10.9 m | 6.3 to 6.9 m | 9.1 to 9.6 m |
| 4 m/s | 1 m | 16.2 m | 6.7 to 7.4 m | 9.4 to 10.1 m |
| 5 m/s | 1 m | 31.2 to 31.6 m | 7.1 to 8.0 m | 9.8 to 10.7 m |
| 7 m/s | 1 m | Falls behind without limit | 7.7 to 10.0 m | 10.4 to 12.5 m |
| 2 m/s | 4 m, like a phone | 15.7 m | 10.9 m | 21.3 m |
| 3 m/s | 4 m, like a phone | Falls behind without limit | 16.3 m | 27.0 m |

The closest the drone came, after the first 10 s where noted:

| Case | Original | Feed-forward | Now |
|---|---|---|---|
| Standing rider, 3 m errors reported honestly, five runs, after 10 s | 0.3 to 1.8 m | 0.4 to 1.5 m | 8.2 to 9.5 m |
| The same errors reported as 2 m, after 10 s | 0.3 to 1.2 m | 0.0 to 0.7 m | 2.9 to 4.9 m |
| Sudden stop from 4 m/s | 5.1 m | 3.4 m | 6.1 m |
| 90 degree turn at 4 m/s | 11.1 m | 5.1 m | 7.3 m |

What this shows:
- **The margin fixes the close approach when the accuracy is honest.**
- **It is only as good as the reported accuracy.** When a receiver reports 2 m for 3 m errors, the clearance falls to 3 to 5 m. Phones are often optimistic, so the reported accuracy needs checking against real data. Recording the same walk on two phones at once would show how far apart they really are.
- **It costs distance.** Clean following moves about 2.7 m further back, and a phone alone (degraded) is followed 21 to 27 m back.

**Still open:**
- Check reported accuracy against real recordings.
- Follow the filtered position instead of the raw estimate.
- Require the camera to confirm before following close.
- Review the degraded threshold with real phone and tag data.

Each is a change to the follow logic, so it needs simulation tests first.

## Replaying your own recording

Record a walk or ride with a GPS-logging app on your phone, and export it as GPX. Keep the file outside the repo. These apps' GPX writers were read in their source code on 2026-10-26:

| App | Phones | Accuracy in its GPX |
|---|---|---|
| OsmAnd | Android and iPhone | The phone's own accuracy estimate, in meters, in `hdop`. The best choice here. |
| GPSLogger | Android | HDOP, a unitless ratio, sometimes missing. The importer turns it into a guess. |
| Open GPX Tracker | iPhone | None, so the importer uses its 5 m guess. |

Then run, or open the file on the website's replay page:

```
PYTHONPATH=src python3 -m follow_me.recording ~/walk.gpx                          # a summary
PYTHONPATH=src python3 -m follow_me.recording --json ~/walk.gpx > ~/walk.trace.json  # open it in the replay viewer
```

- **What it keeps.** `recording.py` keeps each fix's seconds and meters from the first fix, and its accuracy. It drops the coordinates, dates and names as it reads them, and writes no files. See [privacy-and-rules.md](privacy-and-rules.md).
- **Where the drone starts.** The simulated drone starts mid-band behind the rider, against the direction of their first 10 m.
- **How long a recording can be.** Up to 2 hours. A longer trace is too big for a browser tab.
- **Accuracy.** GPX has no standard accuracy field, so the summary counts where each fix's accuracy came from:
  - **Recorded:** an accuracy extension. In OsmAnd files, the `hdop` field, which OsmAnd fills with the phone's accuracy in meters.
  - **HDOP:** in other files, `hdop` is a unitless ratio (GPSLogger writes it this way), so the accuracy is taken as HDOP times 4 m, a guess.
  - **Default:** 5 m when the file has neither, also a guess.

  With a phone's typical accuracy, expect most of the track to be degraded (see the findings above).

## In the browser

The website's replay page has the made-up example ride, and it opens a GPX recording too. It runs this same Python in the browser tab with Pyodide, and draws three things:
- the distance to the rider over time, with the follow band shaded;
- a top-down view of both paths, relative to the start, with no map;
- the time in each mode.

The recording is not uploaded. See [website.md](website.md).

## Tests

`tests/test_sim.py` checks:
- the follow band's edges, and turning toward a rider off to one side;
- stale fixes, the dead-reckoning hold, and fallback timing at two loop rates;
- the trace format and the summary, including the closest approach;
- for the original controller (`feed_forward=False, margin_sigmas=0`), the iteration 21 findings: the trailing distance against the controller's arithmetic, the speed ceiling, and the phone case;
- the safety margin: noisy fixes kept at a distance, the limit when accuracy is under-reported, following and stopping with the margin, and the margin's size;
- with feed-forward and no margin:
  - riders at 2 to 7 m/s are kept close;
  - a sudden stop is never approached closer than 3 m;
  - a turn is followed without a large overshoot;
  - noisy fixes make the drone move at most 25% more;
  - degraded still halves the whole command.

`tests/test_motion.py` checks the Kalman filter, and `tests/test_controller.py` the feed-forward and its fade.
