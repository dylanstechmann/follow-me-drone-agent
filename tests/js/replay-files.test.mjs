import assert from "node:assert/strict";
import { test } from "node:test";
import { replayFileKind } from "../../site/assets/replay-files.js";

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
