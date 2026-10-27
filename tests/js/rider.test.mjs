// Node's own test runner: node --test "tests/js/*.test.mjs"
import assert from "node:assert/strict";
import { test } from "node:test";

import { MARKER_ID, center, cropAround, holder, pickRider, shareBox } from "../../site/assets/rider.js";

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

test("only a person showing the right marker starts a follow", () => {
  const a = person(0, 0, 100, 300);
  const b = person(200, 0, 100, 300);
  const rider = pickRider([a, b], [markerAt(250, 120)], null, 0);
  assert.equal(rider.box, b);
  assert.equal(rider.byMarker, true);
  assert.equal(rider.found, true);
  assert.equal(pickRider([a, b], [markerAt(250, 120, MARKER_ID + 1)], null, 0), null); // another marker
  assert.equal(pickRider([a, b], [], null, 0), null); // nobody shows a marker
});

test("after the marker, the same person is followed by overlap, for as long as it lasts", () => {
  let rider = pickRider([person(200, 0, 100, 300)], [markerAt(250, 120)], null, 0);
  for (const [t, x] of [[500, 215], [1000, 230], [1500, 245], [2500, 260]]) {
    rider = pickRider([person(x, 0, 100, 300), person(700, 0, 100, 300)], [], rider, t);
    assert.equal(rider.found, true, `at ${t} ms`);
    assert.equal(rider.box.x, x);
    assert.equal(rider.byMarker, false);
  }
});

test("a lost rider is waited for a moment, unseen, then let go", () => {
  const first = pickRider([person(200, 0, 100, 300)], [markerAt(250, 120)], null, 0);
  const waiting = pickRider([], [], first, 600);
  assert.equal(waiting.found, false); // not drawn sharp or followed while lost
  assert.equal(waiting.seenAt, 0);
  assert.equal(pickRider([], [], waiting, 1200), null);
  assert.equal(pickRider([person(600, 0, 100, 300)], [], first, 300).found, false); // nobody overlaps
});

test("two people where the rider was stops the follow instead of guessing", () => {
  const first = pickRider([person(200, 0, 100, 300)], [markerAt(250, 120)], null, 0);
  const crowd = [person(190, 0, 100, 300), person(215, 10, 100, 300)];
  assert.equal(pickRider(crowd, [], first, 500), null);
});

test("a box becomes shares of the frame", () => {
  assert.deepEqual(shareBox(person(270, 60, 100, 240), 640, 480), { cx: 0.5, cy: 0.375, height: 0.5 });
});

test("the crop is three heights around the rider, at least 160 px, inside the frame", () => {
  assert.deepEqual(cropAround(person(300, 200, 20, 60), 640, 480), { x: 220, y: 140, side: 180 }); // centred on (310, 230)
  assert.deepEqual(cropAround(person(300, 200, 10, 30), 640, 480), { x: 225, y: 135, side: 160 });
  assert.deepEqual(cropAround(person(0, 0, 20, 60), 640, 480), { x: 0, y: 0, side: 180 }); // kept inside
  assert.deepEqual(cropAround(person(100, 0, 100, 400), 640, 480), { x: 0, y: 0, side: 480 }); // a tall rider
});
