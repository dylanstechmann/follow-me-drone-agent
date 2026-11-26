import assert from "node:assert/strict";
import { test } from "node:test";

import {
  PRESETS, SCENARIO_FORMAT, TimelineState, clampIndex, describeFrame, eventFrameIndex,
  formatMass, formatPercent, formatSeconds, outcomeText, phaseLabel, presetLabel,
  restoreViewerTrace, sandboxFromConfig, targetLabel, traceProblem,
} from "../../site/assets/scenario-utils.js";

const frame = (overrides = {}) => ({
  t_s: 1.2,
  phase: "approach",
  status: "approach",
  drone_flight: { position: { x: 1, y: 2, z: 3 }, in_water: false },
  target: { kind: "object", position: { x: 6, y: 4, z: 0.03 }, attached: false, dimensions_m: { x: 0.12, y: 0.08, z: 0.06 } },
  tentacle: { tip_position: { x: 1, y: 2, z: 3 }, extension_m: 0, in_water: false, submersion_depth_m: 0 },
  onboard_camera_pose: { position: { x: 1, y: 2, z: 3 }, look_at: { x: 6, y: 4, z: 0 } },
  camera_framing: { in_frame: true },
  ...overrides,
});
const trace = (frames = [frame()]) => ({ format: SCENARIO_FORMAT, config: { mode: "retrieval" }, frames, events: [], summary: { success: true, reason: "done" } });

test("the six stable preset IDs and object labels are explicit", () => {
  assert.deepEqual(Object.keys(PRESETS), ["follow_ride", "soccer_land", "soccer_water", "indoor_soda", "pennyboard_land", "object_sandbox"]);
  assert.match(presetLabel("soccer_water"), /shallow water/);
  assert.equal(targetLabel("soda_can"), "Soda can");
  assert.equal(phaseLabel("dead_reckoning"), "Dead reckoning");
});

test("sandbox conversion keeps setting, surface, and waterproof independent", () => {
  assert.deepEqual(sandboxFromConfig({ target_kind: "soda_can", setting: "indoor", surface: "water", waterproof: false, generic_mass_kg: 0.4 }), {
    target_kind: "soda_can", setting: "indoor", surface: "water", waterproof: false, generic_mass_kg: 0.4,
  });
  assert.equal(sandboxFromConfig({}).waterproof, true);
});

test("trace validation checks the core frame contract without a DOM", () => {
  assert.equal(traceProblem(trace()), null);
  assert.match(traceProblem({}), /not a follow-me-scenario-v1/);
  assert.match(traceProblem(trace([])), /needs config, frames, events/);
  const broken = trace();
  delete broken.frames[0].onboard_camera_pose;
  assert.match(traceProblem(broken), /incomplete frame/);
});

test("frame indices are clamped and malformed counts are safe", () => {
  assert.equal(clampIndex(-3, 10), 0);
  assert.equal(clampIndex(99, 10), 9);
  assert.equal(clampIndex(2.9, 10), 2);
  assert.equal(clampIndex(4, 0), 0);
});

test("timeline playback is manual, steps, and stops at the terminal frame", () => {
  const timeline = new TimelineState(3);
  assert.equal(timeline.playing, false);
  assert.equal(timeline.play(), true);
  assert.equal(timeline.advance(), 1);
  assert.equal(timeline.playing, true);
  assert.equal(timeline.advance(), 2);
  assert.equal(timeline.playing, false);
  assert.equal(timeline.advance(), 2);
});

test("playing from a terminal frame restarts at zero; pause preserves position", () => {
  const timeline = new TimelineState(2);
  timeline.seek(1);
  timeline.play();
  assert.equal(timeline.index, 0);
  timeline.advance();
  timeline.seek(0);
  timeline.play();
  timeline.pause();
  assert.equal(timeline.index, 0);
  assert.equal(timeline.playing, false);
});

test("a stopped non-waterproof water frame remains visibly explained", () => {
  const stopped = frame({
    phase: "stopped",
    status: "stopped: waterproof tentacles are required on water; stopped before submerging",
    tentacle: { tip_position: { x: 1, y: 2, z: 3 }, extension_m: 0, in_water: false, submersion_depth_m: 0, waterproof: false },
  });
  const text = describeFrame(stopped, { surface: "water", waterproof: false });
  assert.match(text, /Stopped/);
  assert.match(text, /waterproof tentacles are required/);
  assert.match(text, /before submerging/);
});

test("follow descriptions identify simulated footage and scripted consent", () => {
  const following = frame({
    phase: "follow",
    follow: { synthetic: true, consent_given: true },
  });
  const text = describeFrame(following);
  assert.match(text, /simulated camera frame/);
  assert.match(text, /synthetic rider only/);
  assert.match(text, /no bystanders or real footage/);
});

test("viewer restoration preserves the selected frame across a 3D fallback", () => {
  const data = trace([
    frame({ t_s: 0, phase: "approach" }),
    frame({ t_s: 0.1, phase: "carry" }),
    frame({ t_s: 0.2, phase: "complete" }),
  ]);
  const calls = [];
  const viewer = {
    setTrace(value) { calls.push(["setTrace", value]); },
    update(value) { calls.push(["update", value]); },
  };
  restoreViewerTrace(viewer, data, 1);
  assert.deepEqual(calls, [["setTrace", data], ["update", data.frames[1]]]);
});

test("event navigation picks the nearest frame with the matching phase", () => {
  const data = trace([frame({ t_s: 1, phase: "carry" }), frame({ t_s: 1, phase: "release" }), frame({ t_s: 2, phase: "complete" })]);
  assert.equal(eventFrameIndex(data, { t_s: 1, phase: "release" }), 1);
  assert.equal(eventFrameIndex(data, { t_s: 1.9, phase: "complete" }), 2);
});

test("formatting handles mission units and absent statistics", () => {
  assert.equal(formatSeconds(2.25), "2.3 s");
  assert.equal(formatMass(0.4), "0.40 kg");
  assert.equal(formatPercent(1), "100%");
  assert.equal(formatPercent(null), "—");
  assert.equal(outcomeText({ success: false, reason: "payload too heavy" }), "Stopped: payload too heavy");
});
