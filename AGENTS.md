# Agent guidance

This is a personal hobby and learning project. Keep it framed that way in public text. Disclose AI-assisted development in README and release notes. Do not add employment or resume framing.

## Safety rules (hard)

- Never add or change flight-control, geofence, or obstacle-avoidance code without a passing simulation test. Simulation runs come first.
- Do not write code that follows, tracks, or records a person who has not agreed to it. Note bystander privacy in any footage-related change.
- Do not claim the drone is safe, autonomous, or ready to fly. Mark anything untested as untested.
- Any hardware-facing change needs a human review before flight, and the review is recorded in the PR.

## Working rules

- One coding agent at a time on the working tree. Commit or save work before switching tools.
- Use the `dev` Docker Compose service for builds and tests once it exists.
- Keep provider sign-ins out of the repo.
- Credit sources (papers, docs, datasets, libraries) in docs/references.md.
