// Scenario page controller. The Python core computes every trace; JavaScript handles
// loading, accessible transport controls, textual telemetry, and viewport rendering.
import { clear, fetchJSON, fixed, h, initPage } from "./common.js";
import {
  PRESETS, TimelineState, describeFrame, eventFrameIndex, formatMass, formatMeters,
  formatPercent, formatSeconds, isTerminal, outcomeText, phaseLabel, presetLabel,
  restoreViewerTrace, sandboxFromConfig, targetLabel, traceProblem,
} from "./scenario-utils.js";

const $ = (id) => document.getElementById(id);
const els = {
  select: $("scenario-select"), form: $("sandbox-form"), target: $("sandbox-target"),
  setting: $("sandbox-setting"), surface: $("sandbox-surface"), waterproof: $("sandbox-waterproof"),
  mass: $("sandbox-mass"), run: $("run-scenario"), reset: $("reset-scenario"),
  status: $("load-status"), error: $("scenario-error"), announcement: $("mission-announcement"),
  viewer: $("scenario-viewer"), viewerStatus: $("viewer-status"), camera: $("camera-select"),
  resetCamera: $("reset-camera"), viewportTitle: $("viewport-title"), viewBadge: $("view-badge"),
  kpis: $("scenario-kpis"), description: $("frame-description"), facts: $("scenario-facts"),
  previous: $("btn-previous"), play: $("btn-play"), next: $("btn-next"), speed: $("playback-speed"),
  timeline: $("timeline"), timelineOutput: $("timeline-output"), counter: $("frame-counter"),
  phaseRail: $("phase-rail"), eventTable: $("event-table"), presetDescription: $("preset-description"),
};

const state = {
  trace: null,
  timeline: new TimelineState(),
  dirty: false,
  busy: false,
  loading: false,
  applying: false,
  python: false,
  three: false,
  viewer: null,
  viewerKind: null,
  worker: null,
  pending: null,
  requestSerial: 0,
  latestRequest: 0,
  loadSerial: 0,
  raf: 0,
  lastPlaybackTime: null,
  playbackRemainder: 0,
  lastPhase: null,
  eventRows: [],
  reducedMotion: window.matchMedia("(prefers-reduced-motion: reduce)"),
};
const traceCache = new Map();

function showError(text = "") {
  els.error.textContent = text;
  els.error.hidden = !text;
}

function showStatus(text, isError = false) {
  els.status.textContent = text;
  els.status.classList.toggle("error", isError);
}

function updateControls() {
  const unavailable = !state.trace || state.busy || state.loading || state.dirty;
  els.play.disabled = unavailable;
  els.previous.disabled = unavailable;
  els.next.disabled = unavailable;
  els.timeline.disabled = unavailable;
  els.run.disabled = state.busy || state.loading;
  els.run.textContent = state.busy ? "Running…" : "Run scenario";
  els.select.disabled = state.loading;
  els.play.setAttribute("aria-pressed", String(state.timeline.playing));
  els.play.textContent = state.timeline.playing ? "⏸ Pause" : "▶ Play";
}

function pause() {
  state.timeline.pause();
  if (state.raf) cancelAnimationFrame(state.raf);
  state.raf = 0;
  state.lastPlaybackTime = null;
  state.playbackRemainder = 0;
  updateControls();
}

function tile(label, value, sub) {
  return h("div", { class: "card tile" },
    h("p", { class: "label" }, label), h("p", { class: "value" }, value), h("p", { class: "sub" }, sub));
}

function factRows(frame) {
  const config = state.trace.config;
  const summary = state.trace.summary;
  const rows = [
    ["Target", `${targetLabel(config.target_kind)} · illustrative`],
    ["World", `${config.setting} · ${config.surface} · z-up metres`],
    ["Waterproof", config.waterproof ? "Enabled in the model" : "Disabled in the model"],
    ["Mission outcome", outcomeText(summary)],
    ["Pickup / released", `${summary.pickup_achieved ? "Yes" : "No"} / ${summary.released ? "Yes" : "No"}`],
    ["Water contact", `${summary.water_contact ? "Yes" : "No"}; drone body ${summary.drone_water_contact ? "entered water" : "stayed dry"}`],
  ];
  if (config.mode === "follow") {
    rows.push(["Synthetic rider consent", frame.follow?.consent_given ? "Explicit scripted consent" : "Not given"],
      ["Simulated framing", `${formatPercent(summary.follow_in_frame_share)} in frame; mean error ${fixed(summary.follow_mean_framing_error, 3)}`]);
  } else {
    rows.push(["Tentacle depth", formatMeters(summary.max_tentacle_depth_m, 3)],
      ["Drop error", formatMeters(summary.drop_error_m, 3)]);
  }
  return rows;
}

function renderCurrent() {
  const trace = state.trace;
  if (!trace) return;
  const index = state.timeline.index;
  const frame = trace.frames[index];
  els.timeline.value = String(index);
  els.timelineOutput.textContent = `${formatSeconds(frame.t_s)} / ${formatSeconds(trace.frames[trace.frames.length - 1].t_s)}`;
  els.counter.textContent = `${index + 1} / ${trace.frames.length}`;
  els.description.textContent = describeFrame(frame, trace.config);
  clear(els.kpis).append(
    tile("Phase", phaseLabel(frame.phase), isTerminal(frame) ? "Terminal frame" : "Synthetic mission state"),
    tile("Mission time", formatSeconds(frame.t_s), `${trace.frames.length} fixed-step frames`),
    tile("Drone altitude", formatMeters(frame.drone_flight.position.z), `${frame.drone_flight.in_water ? "Body in water" : "Body above water"} · z up`),
    tile("Tentacle", formatMeters(frame.tentacle.extension_m), frame.tentacle.in_water ? `Tip submerged ${formatMeters(frame.tentacle.submersion_depth_m)}` : frame.tentacle.grasped ? "Target grasped" : "Tip dry"),
  );
  clear(els.facts).append(...factRows(frame).flatMap(([key, value]) => [h("dt", {}, key), h("dd", {}, value)]));
  const currentEvents = new Set((frame.events || []).map((event) => `${event.t_s}:${event.kind}:${event.message}`));
  for (const { row, event } of state.eventRows) {
    row.dataset.current = String(currentEvents.has(`${event.t_s}:${event.kind}:${event.message}`));
  }
  state.viewer?.update(frame);
  if (frame.phase !== state.lastPhase) {
    state.lastPhase = frame.phase;
    els.announcement.textContent = isTerminal(frame) ? outcomeText(trace.summary) : `Mission phase: ${phaseLabel(frame.phase)}.`;
  }
}

function buildEventTable() {
  const body = clear(els.eventTable.tBodies[0]);
  state.eventRows = state.trace.events.map((event) => {
    const index = eventFrameIndex(state.trace, event);
    const button = h("button", {
      class: "btn event-time", type: "button", "aria-label": `Go to event at ${formatSeconds(event.t_s)}`,
      onclick: () => { pause(); state.timeline.seek(index); renderCurrent(); },
    }, formatSeconds(event.t_s));
    const row = h("tr", {},
      h("td", {}, button),
      h("td", {}, h("span", { class: "event-kind" }, event.kind), " · ", phaseLabel(event.phase)),
      h("td", {}, event.message));
    body.appendChild(row);
    return { row, event };
  });
  if (!state.eventRows.length) body.appendChild(h("tr", {}, h("td", { colspan: 3 }, "No events in this trace.")));
}

function buildPhaseRail() {
  clear(els.phaseRail);
  const frames = state.trace.frames;
  let start = 0;
  for (let index = 1; index <= frames.length; index += 1) {
    if (index < frames.length && frames[index].phase === frames[start].phase) continue;
    els.phaseRail.appendChild(h("span", {
      "data-phase": frames[start].phase,
      style: { "--run": String(index - start) },
      title: `${phaseLabel(frames[start].phase)}: frames ${start + 1}–${index}`,
    }));
    start = index;
  }
}

function syncSandbox(config) {
  const values = sandboxFromConfig(config);
  state.applying = true;
  els.target.value = values.target_kind;
  els.setting.value = values.setting;
  els.surface.value = values.surface;
  els.waterproof.checked = values.waterproof;
  els.mass.value = String(values.generic_mass_kg);
  state.applying = false;
}

function loadTrace(trace, sourceNote) {
  const problem = traceProblem(trace);
  if (problem) throw new Error(problem);
  pause();
  state.trace = trace;
  state.timeline = new TimelineState(trace.frames.length);
  state.lastPhase = null;
  state.dirty = false;
  syncSandbox(trace.config);
  els.timeline.max = String(trace.frames.length - 1);
  buildEventTable();
  buildPhaseRail();
  state.viewer?.setTrace(trace);
  renderCurrent();
  const stopped = !trace.summary.success;
  showStatus(`${sourceNote} ${outcomeText(trace.summary)}`, stopped);
  showError(stopped ? `Mission stopped as configured: ${trace.summary.reason}` : "");
  updateControls();
}

async function loadPreset(id) {
  pause();
  const token = ++state.loadSerial;
  state.latestRequest = ++state.requestSerial; // invalidate a custom response still in flight
  state.pending = null;
  state.busy = false;
  state.loading = true;
  state.dirty = false;
  els.select.value = id;
  showError();
  showStatus(`Loading the prebuilt ${presetLabel(id)} trace…`);
  updateControls();
  try {
    if (!traceCache.has(id)) {
      traceCache.set(id, fetchJSON(`data/scenario-${id}.json`).then((trace) => {
        const problem = traceProblem(trace);
        if (problem) throw new Error(problem);
        return trace;
      }));
    }
    const trace = await traceCache.get(id);
    if (token !== state.loadSerial) return;
    state.loading = false;
    loadTrace(trace, `Prebuilt ${presetLabel(id)}; no Python download needed.`);
  } catch (error) {
    traceCache.delete(id);
    if (token !== state.loadSerial) return;
    state.loading = false;
    showStatus("The preset could not be loaded.", true);
    showError(`Could not load ${presetLabel(id)}: ${error.message}. Rebuild with PYTHONPATH=src python3 -m follow_me.website.`);
    updateControls();
  }
}

function settingsChanged() {
  if (state.applying) return;
  pause();
  state.dirty = true;
  state.latestRequest = ++state.requestSerial; // a response for older settings is stale
  showError();
  showStatus("Settings changed. Run scenario to generate a new trace; the viewport still shows the previous settings.");
  updateControls();
}

function sandboxSettings() {
  const mass = Number(els.mass.value);
  if (!Number.isFinite(mass) || mass < 0.05 || mass > 20) {
    throw new Error("Illustrative generic mass must be between 0.05 and 20 kg. Values above the model's 3 kg limit return an explicit stopped mission.");
  }
  return {
    target_kind: els.target.value,
    setting: els.setting.value,
    surface: els.surface.value,
    waterproof: els.waterproof.checked,
    generic_mass_kg: mass,
  };
}

function scenarioWorker() {
  if (state.worker) return state.worker;
  const worker = new Worker(new URL("./scenario-worker.js", import.meta.url), { type: "module" });
  state.worker = worker;
  worker.addEventListener("message", (event) => {
    const msg = event.data;
    const pending = state.pending;
    if (!pending || msg.id !== pending.id) return; // stale worker response
    if (msg.status) {
      if (msg.id === state.latestRequest) {
        showStatus(msg.status === "loading"
          ? "Loading the site's Python runtime for custom settings (about 6 MB on first use)…"
          : "Computing the custom scenario locally in Python…");
      }
      return;
    }
    state.pending = null;
    state.busy = false;
    if (msg.id !== state.latestRequest) {
      showStatus("Settings changed while Python was running. The stale result was discarded; run the current settings when ready.");
      updateControls();
      return;
    }
    if (msg.error) {
      state.dirty = true;
      showStatus("The custom scenario did not run. The previous trace remains visible.", true);
      showError(`Custom scenario error: ${msg.error}. Check the settings, reset to a preset, or run PYTHONPATH=src python3 -m follow_me.website and the scenario API locally.`);
      updateControls();
      return;
    }
    try {
      const trace = JSON.parse(msg.trace);
      loadTrace(trace, "Custom settings computed locally by the repo's Python; nothing was uploaded.");
    } catch (error) {
      state.dirty = true;
      showStatus("Python returned an unreadable scenario trace.", true);
      showError(error.message);
      updateControls();
    }
  });
  worker.addEventListener("error", (event) => {
    if (state.pending) {
      state.pending = null;
      state.busy = false;
      state.dirty = true;
    }
    showStatus("Python could not start in this browser.", true);
    showError(`Python worker failed${event.message ? `: ${event.message}` : ""}. Presets still work. Use the command-line scenario API or rebuild with --vendor to include the local Python runtime.`);
    worker.terminate();
    state.worker = null;
    updateControls();
  });
  return worker;
}

function runCustom(event) {
  event.preventDefault();
  pause();
  let config;
  try {
    config = sandboxSettings();
  } catch (error) {
    state.dirty = true;
    showError(error.message);
    updateControls();
    return;
  }
  if (!state.python) {
    state.dirty = true;
    showStatus("This site build has no browser Python runtime. All six prebuilt presets still work.", true);
    showError("Custom settings need the --vendor build's local Pyodide runtime. Alternatively run sandbox_config(...) and trace_scenario(...) with PYTHONPATH=src python3; no settings are sent to a backend.");
    updateControls();
    return;
  }
  if (state.busy) return;
  const id = ++state.requestSerial;
  state.latestRequest = id;
  state.pending = { id, config };
  state.busy = true;
  state.dirty = false;
  showError();
  showStatus("Starting a local custom run. Changing any setting will make this response stale.");
  updateControls();
  try {
    scenarioWorker().postMessage({ id, config });
  } catch (error) {
    state.pending = null;
    state.busy = false;
    state.dirty = true;
    showStatus("Python could not start in this browser.", true);
    showError(`Could not start the custom scenario worker: ${error.message}. Presets still work; use a --vendor build or the command-line Python API.`);
    updateControls();
  }
}

function play() {
  if (state.timeline.playing) {
    pause();
    return;
  }
  if (!state.trace || state.busy || state.loading || state.dirty) return;
  const wasTerminal = state.timeline.index >= state.trace.frames.length - 1;
  if (!state.timeline.play()) return;
  if (wasTerminal) renderCurrent();
  state.lastPlaybackTime = null;
  state.playbackRemainder = 0;
  updateControls();
  state.raf = requestAnimationFrame(playbackStep);
}

function playbackStep(now) {
  state.raf = 0;
  if (!state.timeline.playing || !state.trace) return;
  if (state.lastPlaybackTime === null) state.lastPlaybackTime = now;
  const elapsed = Math.min(0.25, Math.max(0, (now - state.lastPlaybackTime) / 1000));
  state.lastPlaybackTime = now;
  state.playbackRemainder += elapsed * (Number(els.speed.value) || 1);
  let safety = 0;
  while (state.timeline.playing && safety < 100) {
    const index = state.timeline.index;
    const frames = state.trace.frames;
    if (index >= frames.length - 1) {
      pause();
      break;
    }
    const dt = Math.max(0.001, frames[index + 1].t_s - frames[index].t_s);
    if (state.playbackRemainder < dt) break;
    state.playbackRemainder -= dt;
    state.timeline.advance();
    renderCurrent();
    safety += 1;
  }
  if (state.timeline.playing) state.raf = requestAnimationFrame(playbackStep);
  else updateControls();
}

function seek(index) {
  pause();
  if (!state.trace || state.dirty || state.busy || state.loading) return;
  state.timeline.seek(index);
  renderCurrent();
}

function setCamera() {
  const onboard = els.camera.value === "onboard";
  els.viewportTitle.textContent = onboard ? "Onboard · simulated footage" : "External inspection";
  els.viewBadge.textContent = onboard ? "SIMULATED FOOTAGE · NOT RECORDED" : "SIMULATED WORLD";
  state.viewer?.setCamera(els.camera.value);
  document.querySelectorAll("[data-camera-nudge]").forEach((button) => { button.disabled = onboard; });
}

async function activateFallback(message) {
  if (state.viewerKind === "svg") {
    els.viewerStatus.textContent = message;
    return;
  }
  state.viewer?.dispose();
  const { createTopDownScene } = await import("./scene3d.js");
  state.viewer = createTopDownScene(els.viewer);
  state.viewerKind = "svg";
  if (state.trace) restoreViewerTrace(state.viewer, state.trace, state.timeline.index);
  state.viewer.setCamera(els.camera.value);
  els.viewerStatus.textContent = message;
}

async function initViewer() {
  try {
    const module = await import("./scene3d.js");
    if (!state.three) {
      await activateFallback("This build has no vendored three.js, so a top-down SVG is shown. All controls, telemetry and events still work. Build with --vendor for 3D.");
      return;
    }
    const viewer = await module.createScene3D(els.viewer, {
      onFailure: (message) => activateFallback(message).catch(() => {}),
    });
    state.viewer = viewer;
    state.viewerKind = "webgl";
    if (state.trace) restoreViewerTrace(viewer, state.trace, state.timeline.index);
    viewer.setCamera(els.camera.value);
    els.viewerStatus.textContent = "Procedural three.js view. Rendering is on demand while playing, scrubbing, resizing, or orbiting; no continuous loop runs while paused.";
  } catch (error) {
    await activateFallback(`3D could not start (${error.message}). A top-down SVG is shown instead; mission controls and event data remain available.`);
  }
}

function wire() {
  els.select.addEventListener("change", () => loadPreset(els.select.value));
  els.reset.addEventListener("click", () => loadPreset(els.select.value));
  els.form.addEventListener("submit", runCustom);
  for (const control of [els.target, els.setting, els.surface, els.waterproof, els.mass]) {
    control.addEventListener("change", settingsChanged);
    control.addEventListener("input", settingsChanged);
  }
  els.play.addEventListener("click", play);
  els.previous.addEventListener("click", () => seek(state.timeline.index - 1));
  els.next.addEventListener("click", () => seek(state.timeline.index + 1));
  els.timeline.addEventListener("input", () => seek(Number(els.timeline.value)));
  els.camera.addEventListener("change", setCamera);
  els.resetCamera.addEventListener("click", () => state.viewer?.reset());
  document.querySelectorAll("[data-camera-nudge]").forEach((button) => {
    button.addEventListener("click", () => state.viewer?.nudge?.(button.dataset.cameraNudge));
  });
  document.addEventListener("keydown", (event) => {
    const target = event.target;
    const tag = target?.tagName || "";
    if (["INPUT", "SELECT", "TEXTAREA", "BUTTON", "A"].includes(tag) || target?.isContentEditable || !state.trace || state.dirty || state.busy) return;
    if (event.key === " ") { play(); event.preventDefault(); }
    else if (event.key === "ArrowRight") { seek(state.timeline.index + 1); event.preventDefault(); }
    else if (event.key === "ArrowLeft") { seek(state.timeline.index - 1); event.preventDefault(); }
  });
  document.addEventListener("visibilitychange", () => { if (document.hidden) pause(); });
  state.reducedMotion.addEventListener("change", () => { if (state.reducedMotion.matches) pause(); });
  window.addEventListener("pagehide", () => {
    pause();
    state.viewer?.dispose();
    state.worker?.terminate();
  }, { once: true });
}

async function main() {
  initPage();
  wire();
  if (state.reducedMotion.matches) els.speed.value = "1";
  const buildPromise = fetchJSON("data/build.json").then((info) => {
    state.python = Boolean(info.python);
    state.three = Boolean(info.scenario3d);
  }).catch(() => {
    state.python = false;
    state.three = false;
  });
  await Promise.all([buildPromise, loadPreset("object_sandbox")]);
  await initViewer();
  updateControls();
}

main();
