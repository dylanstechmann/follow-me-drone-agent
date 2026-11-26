// Pure helpers for the scenario page. No DOM, storage, network, or simulation logic:
// traces always come from the repo's Python, either prebuilt or through the worker.

export const SCENARIO_FORMAT = "follow-me-scenario-v1";
export const PRESETS = Object.freeze({
  follow_ride: { label: "Follow-me pennyboard footage", short: "Follow ride" },
  soccer_land: { label: "Outdoor soccer pickup · land", short: "Soccer on land" },
  soccer_water: { label: "Waterproof soccer retrieval · shallow water", short: "Soccer in water" },
  indoor_soda: { label: "Indoor soda pickup · living room", short: "Indoor soda" },
  pennyboard_land: { label: "Pennyboard pickup · land", short: "Pennyboard pickup" },
  object_sandbox: { label: "Generic object sandbox · land or water", short: "Object sandbox" },
});
export const TARGETS = Object.freeze({
  soccer_ball: "Soccer ball",
  soda_can: "Soda can",
  pennyboard: "Pennyboard",
  object: "Generic object",
});
export const PHASES = Object.freeze({
  approach: "Approach", align: "Align", descend: "Descend", extend: "Extend",
  grasp: "Grasp", lift: "Lift", carry: "Carry", release: "Release",
  complete: "Complete", stopped: "Stopped", follow: "Simulated follow",
});

export function presetLabel(id) {
  return PRESETS[id]?.label || String(id || "Unknown scenario");
}

export function targetLabel(kind) {
  return TARGETS[kind] || String(kind || "object").replaceAll("_", " ");
}

export function phaseLabel(phase) {
  const text = String(phase || "unknown").replaceAll("_", " ");
  return PHASES[phase] || text.charAt(0).toUpperCase() + text.slice(1);
}

export function sandboxFromConfig(config = {}) {
  return {
    target_kind: config.target_kind || "object",
    setting: config.setting || "outdoor",
    surface: config.surface || "land",
    waterproof: config.waterproof !== false,
    generic_mass_kg: Number.isFinite(config.generic_mass_kg) ? config.generic_mass_kg : 0.25,
  };
}

export function traceProblem(data) {
  if (!data || typeof data !== "object" || data.format !== SCENARIO_FORMAT) {
    return `This is not a ${SCENARIO_FORMAT} scenario trace.`;
  }
  if (!data.config || !data.summary || !Array.isArray(data.frames) || !data.frames.length || !Array.isArray(data.events)) {
    return "The scenario trace needs config, frames, events, and a summary.";
  }
  for (const frame of data.frames) {
    if (!Number.isFinite(frame.t_s) || typeof frame.phase !== "string" || !frame.drone_flight?.position ||
        !frame.target?.position || !frame.tentacle?.tip_position || !frame.onboard_camera_pose?.position) {
      return "The scenario trace has an incomplete frame.";
    }
  }
  return null;
}

export function clampIndex(index, frameCount) {
  if (!Number.isInteger(frameCount) || frameCount < 1) return 0;
  const number = Number.isFinite(Number(index)) ? Math.trunc(Number(index)) : 0;
  return Math.max(0, Math.min(frameCount - 1, number));
}

export function restoreViewerTrace(viewer, trace, index = 0) {
  // setTrace resets procedural viewers to frame zero; restore the selected frame too.
  viewer.setTrace(trace);
  viewer.update(trace.frames[clampIndex(index, trace.frames.length)]);
}

export function isTerminal(frame) {
  return frame?.phase === "complete" || frame?.phase === "stopped";
}

// Small state machine kept separate from browser timing so its edge cases are testable.
export class TimelineState {
  constructor(frameCount = 1) {
    this.frameCount = Math.max(1, Math.trunc(frameCount) || 1);
    this.index = 0;
    this.playing = false;
  }

  seek(index) {
    this.index = clampIndex(index, this.frameCount);
    return this.index;
  }

  pause() {
    this.playing = false;
  }

  play() {
    if (this.frameCount < 2) return false;
    if (this.index >= this.frameCount - 1) this.index = 0;
    this.playing = true;
    return true;
  }

  toggle() {
    if (this.playing) this.pause();
    else this.play();
    return this.playing;
  }

  advance() {
    if (!this.playing) return this.index;
    if (this.index >= this.frameCount - 1) {
      this.pause();
      return this.index;
    }
    this.index += 1;
    if (this.index >= this.frameCount - 1) this.pause();
    return this.index;
  }
}

export function fixedNumber(value, digits = 1, fallback = "—") {
  return Number.isFinite(value) ? Number(value).toFixed(digits) : fallback;
}

export function formatSeconds(value) {
  return `${fixedNumber(value, 1, "0.0")} s`;
}

export function formatMeters(value, digits = 2) {
  return `${fixedNumber(value, digits)} m`;
}

export function formatMass(value) {
  return `${fixedNumber(value, 2)} kg`;
}

export function formatPercent(share) {
  return Number.isFinite(share) ? `${Math.round(share * 100)}%` : "—";
}

export function describeFrame(frame, config = {}) {
  if (!frame) return "No frame loaded.";
  const phase = phaseLabel(frame.phase);
  const position = frame.drone_flight.position;
  const where = `Drone at x ${fixedNumber(position.x, 1)}, y ${fixedNumber(position.y, 1)}, z ${fixedNumber(position.z, 1)} m (z up).`;
  if (frame.phase === "stopped") {
    return `${phase}. ${frame.status || "Mission stopped before completion."} ${where}`;
  }
  if (frame.follow) {
    const framing = frame.camera_framing?.in_frame ? "Rider inside the simulated camera frame" : "Rider outside the simulated camera frame";
    return `${phase}. ${framing}; synthetic rider only, with scripted consent and no bystanders or real footage. ${where}`;
  }
  const target = `${targetLabel(frame.target.kind)} ${frame.target.attached ? "attached to the gripper" : "not attached"}`;
  const tentacle = `Tentacle extension ${formatMeters(frame.tentacle.extension_m)}${frame.tentacle.in_water ? ", tip in water" : ""}.`;
  const action = {
    approach: `Moving toward the ${targetLabel(frame.target.kind).toLowerCase()} at cruise altitude.`,
    align: "Holding over the target before descent.",
    descend: "Descending to the pickup hover position.",
    extend: "Extending the idealized prismatic tentacle toward the target.",
    grasp: "The scripted grasp engages; no contact physics are modelled.",
    lift: "Lifting the attached target.",
    carry: "Carrying the target to the synthetic dry drop pad.",
    release: "Releasing the target onto the synthetic dry drop pad.",
    complete: "Retrieval and release are complete in this synthetic trace.",
  }[frame.phase] || frame.status || "Scenario running.";
  return `${phase}. ${action} ${target}. ${tentacle} ${where}`;
}

export function eventFrameIndex(trace, event) {
  let best = 0;
  let distance = Infinity;
  trace.frames.forEach((frame, index) => {
    const next = Math.abs(frame.t_s - event.t_s) + (frame.phase === event.phase ? 0 : 0.001);
    if (next < distance) {
      best = index;
      distance = next;
    }
  });
  return best;
}

export function outcomeText(summary) {
  if (!summary) return "No mission result.";
  return summary.success ? `Complete: ${summary.reason}` : `Stopped: ${summary.reason}`;
}
