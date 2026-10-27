// Node's own test runner: node --test tests/js
import assert from "node:assert/strict";
import { test } from "node:test";

import { CLASSES, INPUT, decode, fitScale, iou, nms, rowCount, toInput, unscale } from "../../site/assets/detector.js";

const WIDTH = 5 + CLASSES;

function rowsWith(cells, size = INPUT) {
  // A blank output with chosen candidates: {row, x, y, logW, logH, obj, cls, score}.
  const rows = new Float32Array(rowCount(size) * WIDTH);
  for (const c of cells) {
    const o = c.row * WIDTH;
    rows.set([c.x, c.y, c.logW, c.logH, c.obj], o);
    rows[o + 5 + c.cls] = c.score;
  }
  return rows;
}

test("the 416 input has 3,549 candidate rows", () => {
  assert.equal(rowCount(416), 52 * 52 + 26 * 26 + 13 * 13);
  assert.equal(rowCount(416), 3549);
});

test("a frame is fitted inside the square, keeping its shape", () => {
  assert.equal(fitScale(640, 480), 416 / 640);
  assert.equal(fitScale(480, 640), 416 / 640);
});

test("pixels become BGR planes of raw values", () => {
  const rgba = new Uint8ClampedArray([10, 20, 30, 255, 40, 50, 60, 255, 70, 80, 90, 255, 1, 2, 3, 255]);
  assert.deepEqual(Array.from(toInput(rgba, 2)), [30, 60, 90, 3, 20, 50, 80, 2, 10, 40, 70, 1]);
});

test("a confident person is decoded at its grid cell and stride", () => {
  // Row 2704 is the first cell of the stride-16 grid (after 52 x 52 stride-8 cells).
  const row = 52 * 52 + 26 * 3 + 5; // grid x 5, y 3 at stride 16
  const rows = rowsWith([{ row, x: 0.5, y: 0.25, logW: Math.log(4), logH: Math.log(8), obj: 0.9, cls: 0, score: 0.8 }]);
  const [box] = decode(rows);
  assert.ok(Math.abs(box.score - 0.72) < 1e-6);
  assert.ok(Math.abs(box.x + box.w / 2 - (0.5 + 5) * 16) < 1e-4); // centre x
  assert.ok(Math.abs(box.y + box.h / 2 - (0.25 + 3) * 16) < 1e-4); // centre y
  assert.ok(Math.abs(box.w - 64) < 1e-3 && Math.abs(box.h - 128) < 1e-3);
});

test("weak candidates and other classes are dropped", () => {
  const rows = rowsWith([
    { row: 10, x: 0, y: 0, logW: 0, logH: 0, obj: 0.5, cls: 0, score: 0.5 }, // 0.25, below 0.35
    { row: 20, x: 0, y: 0, logW: 0, logH: 0, obj: 0.9, cls: 2, score: 0.9 }, // a car
  ]);
  assert.equal(decode(rows).length, 0);
  assert.equal(decode(rows, { cls: 2 }).length, 1);
});

test("overlap removal keeps the best box of a group", () => {
  const a = { x: 0, y: 0, w: 10, h: 20, score: 0.9 };
  const b = { x: 1, y: 1, w: 10, h: 20, score: 0.8 };
  const c = { x: 50, y: 0, w: 10, h: 20, score: 0.7 };
  assert.ok(iou(a, b) > 0.45);
  assert.equal(iou(a, c), 0);
  assert.deepEqual(nms([b, c, a]), [a, c]);
});

test("boxes go back to frame pixels", () => {
  assert.deepEqual(unscale([{ x: 13, y: 26, w: 52, h: 104, score: 1 }], 0.65), [{ x: 20, y: 40, w: 80, h: 160, score: 1 }]);
});
