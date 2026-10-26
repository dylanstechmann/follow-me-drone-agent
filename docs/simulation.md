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

## Findings (2026-10-26, default settings)

These numbers come from the model with its placeholder limits. They show how the current follow logic behaves, not how a real drone would fly. They are where the drone settles behind a rider moving in a straight line, or standing still:

| Rider | Fix accuracy (one sigma) | Where the drone settles |
|---|---|---|
| Standing | 1 m | 5.05 m away, the far edge of the follow band |
| 2 m/s | 1 m | 7.6 m behind |
| 3 m/s | 1 m | 10.1 m behind |
| 4 m/s | 1 m | 15.2 m behind |
| 5 m/s | 1 m | About 30 m behind |
| 7 m/s | 1 m | Falls behind without limit |
| 2 m/s | 4 m, like a phone | 15.2 m behind, degraded at half gain |
| 3 m/s | 4 m, like a phone | Falls behind without limit |

What the table shows:

- **The drone trails a moving rider.** The controller acts on distance alone, with no feed-forward of the rider's speed. So the drone settles where its forward command times the top speed equals the rider's speed.
- **There is a speed ceiling.** The forward command tops out at 0.6: the gain times the target box height minus the deadband. So the drone never passes 6 m/s with the 10 m/s placeholder.
- **A phone alone is degraded.** A 4 m fix has a 16 m² variance, above the mode machine's 9 m² threshold. Every tick is then degraded at half gain, and the drone tops out at 3 m/s.
- **Falling behind makes it worse.** The 3 degree heading uncertainty adds variance in proportion to range. Past about 54 m, even a 1 m fix is degraded, which halves the speed again.

Candidates that follow from this. Each is a change to the follow logic, so it needs simulation tests before it is made:

- Feed the rider's speed forward in the controller.
- Review the degraded threshold with real phone and tag data.

## Tests

`tests/test_sim.py` checks:
- the follow band's edges;
- turning toward a rider off to one side;
- the trailing distance against the controller's arithmetic;
- the speed ceiling;
- the phone case;
- that stale fixes give no reading;
- the dead-reckoning hold;
- the trace format, which adds each tick's drone position, rider position and distance to the replay viewer's format.
