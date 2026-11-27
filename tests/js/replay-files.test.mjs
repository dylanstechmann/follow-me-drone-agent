import assert from "node:assert/strict";
import { test } from "node:test";
import { replayFileKind, traceProblem } from "../../site/assets/replay-files.js";

const file = (name, size = 1) => ({ name, size });

test("routes complete local selections, including a trace without an extension", () => {
  assert.equal(replayFileKind([]), null);
  assert.equal(replayFileKind([file("example")]), "trace");
  assert.equal(replayFileKind([file("recording")], true), "recording");
  assert.equal(replayFileKind([file("one.GPX"), file("two.gpx")]), "recording");
});

test("reports ambiguous selections and oversized traces or recordings before parsing", () => {
  assert.throws(() => replayFileKind([file("a.json"), file("b.json")]), /one JSON/);
  assert.throws(() => replayFileKind([file("a.gpx"), file("b.json")]), /separately/);
  assert.throws(() => replayFileKind(["a", "b", "c"].map((x) => file(x + ".gpx"))), /one or two/);
  assert.throws(() => replayFileKind([file("a.json")], true), /trace picker/);
  for (const name of ["demo.json", "demo.gpx"]) {
    assert.throws(() => replayFileKind([file(name, 50_000_001)]), /50 MB/);
    assert.doesNotThrow(() => replayFileKind([file(name, 50_000_000)]));
  }
});

test("checks imported ticks before they replace the current offline replay", () => {
  const tick = { t: 0, mode: "hold", readings: [], command: { yaw: 0, forward: 0, climb: 0 } };
  const position = { x: 1, y: 2, variance: 0 };
  const trace = (second) => ({ format: "follow-me-trace/1", ticks: [tick, second] });
  assert.equal(traceProblem(trace({ ...tick, readings: [{ ...position, source: "fixture" }], estimate: position })), null);
  for (const [second, expected] of [
    [null, /Tick 2 needs a time/],
    [{ ...tick, t: Infinity }, /Tick 2 needs a time/],
    [{ ...tick, command: null }, /Tick 2 needs numeric/],
    [{ ...tick, readings: [null] }, /Tick 2, reading 1/],
    [{ ...tick, readings: [{ ...position, source: "fixture", variance: -1 }] }, /Tick 2, reading 1/],
    [{ ...tick, estimate: {} }, /Tick 2 has an invalid estimate/],
    [{ ...tick, attention: "wrong" }, /Tick 2 needs attention/],
  ]) {
    assert.match(traceProblem(trace(second)), expected);
  }
  assert.match(traceProblem({ ticks: [tick] }), /raw log/);
});
