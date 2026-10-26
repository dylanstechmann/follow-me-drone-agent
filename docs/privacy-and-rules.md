# Privacy and rules

## Location data stays local

This repo is public. Your routes, home, and any place profiles with real coordinates must never be committed.

- Real place profiles live in a JSON file outside the repo, by default `~/.config/follow-me/places.json`, or at the path in the `FOLLOW_ME_PLACES` environment variable.
- The repo ships only fake examples in `examples/`.
- `.gitignore` excludes `places.json` and `*.local.json` as a safety net, but do not rely on it alone.

Recorded tracks are location data too:

- A GPX recording from a phone stays on the owner's machine. `python -m follow_me.recording` reads it and prints to the terminal; it writes no files. The website's replay page reads it inside the browser tab and uploads nothing.
- The importer keeps only offsets in meters from the first fix and seconds from the first fix. It drops the coordinates, dates and names as each point is read.
- A trace made from a real recording still holds the route's shape, so it is not committed either. Name it `*.trace.json` and keep it outside the repo. `.gitignore` excludes `*.gpx` and `*.trace.json` as a safety net.
- Record only yourself, or a rider who has agreed.

## Group orders stay anonymous

The IEEE group order plan ([group-order.md](group-order.md)) is public. It names roles only, such as the coordinator. Names, email addresses, phone numbers, delivery addresses, payment records and order screenshots stay in the club's private channel. A test fails if email-like or phone-like text appears in the plan files.

## Consent

- The tracked person is the owner. If anyone else ever carries a tag or is filmed, they must agree first.
- Footage stays on the owner's device unless every person in it has agreed to sharing.

## Bystanders and airspace

- No flights over people, roads, or busy skate areas.
- Check local drone rules before any flight. Verify these with official sources:
  - In the US, drones over 250 g generally need FAA registration and Remote ID.
  - Recreational flyers need to pass the FAA's free Recreational UAS Safety Test (TRUST).
  - Controlled airspace near airports needs FAA authorization. LAANC gives it through approved apps, including to recreational flyers.
  - Flying over people and commercial use (for example, paid footage) have their own rules.
  - Cellular-connected drones may need checking against carrier and FCC rules.
- FAU is in Florida, so the US rules apply if flying there. FAU's own safety page says recreational drone use on university property is strictly prohibited, and its Boca Raton campus borders Boca Raton Airport's Class D airspace. See [lab-access.md](lab-access.md). Plan flights off campus unless FAU approves one.

## Honest framing

- This is a hobby and learning project, written by AI coding assistants at the owner's direction. No review of the code by the owner is recorded.
- Nothing here is tested on real hardware or certified for flight. Do not present it as safe or autonomous.
