// Node's own test runner: node --test "tests/js/*.test.mjs"
import assert from "node:assert/strict";
import { test } from "node:test";

import { MARKER_ID, center, holder, pickRider, shareBox } from "../../site/assets/rider.js";

const person = (x, y, w, h, score = 0.9) => ({ x, y, w, h, score });
const markerAt = (x, y, id = MARKER_ID, s = 10) => ({
  id, corners: [{ x: x - s, y: y - s }, { x: x + s, y: y - s }, { x: x + s, y: y + s }, { x: x - s, y: y + s }],
});

test("the marker's centre is the mean of its corners", () => {
  assert.deepEqual(center(markerAt(50, 80).corners), { x: 50, y: 80 });
});

test("the holder is the smallest person box around the marker", () => {
  const behind = person(0, 0, 300, 400);
  const front = person(100, 100, 80, 200);
  assert.equal(holder([behind, front], { x: 140, y: 180 }), front);
  assert.equal(holder([behind, front], { x: 20, y: 20 }), behind);
  assert.equal(holder([front], { x: 20, y: 20 }), null);
});

test("only the person showing the right marker is followed", () => {
  const a = person(0, 0, 100, 300);
  const b = person(200, 0, 100, 300);
  const rider = pickRider([a, b], [markerAt(250, 120)], null, 0);
  assert.equal(rider.box, b);
  assert.equal(rider.byMarker, true);
  assert.equal(pickRider([a, b], [markerAt(250, 120, MARKER_ID + 1)], null, 0), null); // another marker
  assert.equal(pickRider([a, b], [], null, 0), null); // nobody shows a marker
});

test("a hidden marker's holder is kept for a moment by overlap, then let go", () => {
  const b = person(200, 0, 100, 300);
  const first = pickRider([b], [markerAt(250, 120)], null, 0);
  const moved = person(210, 5, 100, 300);
  const kept = pickRider([moved], [], first, 600);
  assert.equal(kept.box, moved);
  assert.equal(kept.byMarker, false);
  assert.equal(kept.seenAt, 0); // still timed from when the marker was last seen
  assert.equal(pickRider([moved], [], kept, 1200), null); // past the hold
  assert.equal(pickRider([person(600, 0, 100, 300)], [], first, 300), null); // nobody overlaps
});

test("a box becomes shares of the frame", () => {
  assert.deepEqual(shareBox(person(270, 60, 100, 240), 640, 480), { cx: 0.5, cy: 0.375, height: 0.5 });
});
