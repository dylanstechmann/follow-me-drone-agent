import test from "node:test";
import assert from "node:assert/strict";
import { ImportRace } from "../../site/assets/common.js";

test("Forget invalidates a worker completion without accepting stale data", () => {
  const race = new ImportRace();
  const job = race.begin();
  let imported = false;
  race.forget();
  if (race.isCurrent(job)) imported = true;
  assert.equal(imported, false);
});

test("a new import after Forget has its own current generation", () => {
  const race = new ImportRace();
  const forgotten = race.begin();
  race.forget();
  const current = race.begin();
  assert.equal(race.isCurrent(forgotten), false);
  assert.equal(race.isCurrent(current), true);
});
