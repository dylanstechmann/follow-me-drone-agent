# Agent guidance

This is a personal hobby and learning project. Keep it framed that way in public text. Disclose AI-assisted development in README and release notes. Do not add employment or resume framing.

## Start here

Read these in order before changing anything. They are written for any coding agent, and they are this project's memory.

1. docs/project-context.md: what exists, what is only a plan, how it fits together, how to continue.
2. docs/vision.md: the owner's stance and ambition.
3. docs/decisions.md: decisions not to reverse without asking, and corrections that are traps.
4. docs/history.md: what was discussed and done, in order.
5. docs/progress.md: the iteration log and the open questions.

Keep these current. When something changes, update the docs in the same commit.

## Owner preferences (hard)

- The owner does not like asking for money. Never draft a funding, sponsorship, grant, crowdfunding or donation request unless the owner asks. Group orders are cost-sharing, not fundraising.
- The owner wants to own the capability, not every process: hold the design files, get closer to the factory, fab and lab where it pays, and keep two sources for bought parts.
- The owner is curious about building many drones, and the software that may power them, by getting each part themselves, somewhat. This is a direction, not a plan. Do not invent a fleet size, a revenue plan or a product plan.
- Report outcomes faithfully. Say what is a guess. Date every price. Do not say the owner reviewed or built something unless it is recorded.

## Safety rules (hard)

- Never add or change flight-control, geofence, or obstacle-avoidance code without a passing simulation test. Simulation runs come first.
- Do not write code that follows, tracks, or records a person who has not agreed to it. Note bystander privacy in any footage-related change.
- Do not claim the drone is safe, autonomous, or ready to fly. Mark anything untested as untested.
- Any hardware-facing change needs a human review before flight, and the review is recorded in the PR.

## Working rules

- One coding agent at a time on the working tree. Commit or save work before switching tools.
- Run builds and tests directly with `python3 -m pytest` in this project's dev environment. The workspace-level AGENTS.md, one folder above this repo, describes the isolated per-project containers and the reservation rules. Follow it when you work inside that workspace.
- Keep provider sign-ins out of the repo.
- Credit sources (papers, docs, datasets, libraries) in docs/references.md.

## Location data (hard)

- Never commit real coordinates, routes, home or regular-place data. Real place profiles live outside the repo (see docs/privacy-and-rules.md). Only fake examples belong in examples/.

## Group order (hard)

- bom/group_order.json and docs/group-order.md are public. Never add names, email addresses, phone numbers, delivery addresses, payment records, or screenshots of orders or invoices. Use roles only. Keep those details in the club's private channel. A test scans for email-like and phone-like text.
- Keep the plan current. When anything changes (interest, a quote, a decision, an order, a delivery, an inspection result), update the line's `state`, `order_qty` or `quote`, answer the open decision, set `last_updated`, run the docs sync, and commit and push. Record only aggregate results.
- Never claim an order is placed, a supplier is contacted, or a quote exists unless the plan's state and the quote field say so.

## Loop

- Work in plan, do, record cycles. Write each plan in docs/progress.md before doing it, commit and push each iteration, and record the outcome in docs/progress.md.
- Generated docs: after changing anything under bom/, run `PYTHONPATH=src python3 -m follow_me.docs_sync` and commit the result. Never edit text between `<!-- generated:... -->` markers by hand. The test suite fails when a generated block is stale.
