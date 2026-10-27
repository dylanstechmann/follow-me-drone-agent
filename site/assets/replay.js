// Replay viewer: draws one tick of a trace from `python -m follow_me.replay --json`,
// or of a simulated follow from `python -m follow_me.recording --json`.
// Traces are computed by the repo's tested Python; this page only draws them. A GPX
// recording is simulated by that same Python, run in this tab by replay-worker.js.
import { clear, fetchJSON, fixed, h, initPage, makeTooltip, MODES, modeInfo, niceMax, percent, signed, sourceInfo, svg } from "./common.js";

const TRACE_FORMAT = "follow-me-trace/1";
const MAKE_TRACE = "PYTHONPATH=src python3 -m follow_me.replay --json LOG.json > trace.json";
const SIM_CMD = "PYTHONPATH=src python3 -m follow_me.recording --json RECORDING.gpx > recording.trace.json";
const W = 640; // plot viewBox width

const $ = (id) => document.getElementById(id);
const els = {
  plot: $("plot"),
  legend: $("plot-legend"),
  panel: $("tick-panel"),
  strip: $("strip"),
  scrub: $("scrub"),
  modeLegend: $("mode-legend"),
  table: $("tick-table"),
  note: $("log-note"),
  count: $("tick-count"),
  play: $("btn-play"),
  speed: $("speed"),
  select: $("log-select"),
  file: $("file-input"),
  gpx: $("gpx-input"),
  follow: $("follow"),
  kpis: $("follow-kpis"),
  distance: $("distance-chart"),
  world: $("world-plot"),
  worldLegend: $("world-legend"),
};

const tip = makeTooltip();
const traces = new Map(); // option value -> {trace, note}
const state = { trace: null, index: 0, timer: null, frame: null, layer: null, playhead: null, follow: null, python: false };

// ---- loading -------------------------------------------------------------

function problemWith(data) {
  if (!data || typeof data !== "object") return "This file is not a replay trace.";
  if (data.format !== TRACE_FORMAT) {
    if (Array.isArray(data.ticks)) return `This looks like a raw log, not a trace. Make a trace first: ${MAKE_TRACE}`;
    return `This file is not a replay trace (expected format ${TRACE_FORMAT}).`;
  }
  if (!Array.isArray(data.ticks) || data.ticks.length === 0) return "This trace has no ticks.";
  for (const tick of data.ticks) {
    if (typeof tick.t !== "number" || !Array.isArray(tick.readings) || typeof tick.mode !== "string") {
      return "This trace has a tick without t, readings or mode.";
    }
  }
  return null;
}

function showMessage(text, isError = false) {
  els.note.textContent = text;
  els.note.classList.toggle("error", isError);
}

function load(trace, note) {
  stop();
  state.trace = trace;
  state.frame = frameFor(trace);
  drawStatic();
  drawStrip();
  drawModeLegend();
  drawTable();
  drawFollow();
  els.scrub.max = String(trace.ticks.length - 1);
  showMessage(note);
  seek(indexFromHash() ?? 0);
}

function addTrace(key, label, trace, note) {
  traces.set(key, { trace, note });
  els.select.appendChild(h("option", { value: key }, label));
  els.select.value = key;
  history.replaceState(null, "", location.pathname);
  load(trace, note);
}

function openFile(file) {
  const reader = new FileReader();
  reader.onload = () => {
    let data;
    try {
      data = JSON.parse(reader.result);
    } catch (error) {
      showMessage(`Could not read ${file.name}: ${error.message}`, true);
      return;
    }
    const problem = problemWith(data);
    if (problem) {
      showMessage(problem, true);
      return;
    }
    const note = `Your file, ${file.name}: ${data.ticks.length} ticks. It stays in this browser tab.` +
      (data.note ? ` Its note: ${data.note}` : "");
    addTrace(`file:${file.name}:${traces.size}`, `Your file: ${file.name}`, data, note);
  };
  reader.onerror = () => showMessage(`Could not read ${file.name}.`, true);
  reader.readAsText(file);
}

// ---- recordings, simulated in this tab -------------------------------------

let worker = null;
let jobs = 0;

function pythonWorker() {
  if (!worker) {
    worker = new Worker(new URL("./replay-worker.js", import.meta.url), { type: "module" });
    worker.addEventListener("error", () => {
      showMessage(`Python could not start in this browser. The command line gives the same trace: ${SIM_CMD}`, true);
      worker = null;
    });
  }
  return worker;
}

const ACCURACY_FROM = {
  recorded: "recorded in the file",
  hdop: "HDOP × 4 m, a guess",
  default: "a 5 m default, a guess",
};

function recordingNote(name, rec) {
  const sources = Object.entries(rec.accuracy_from)
    .map(([key, n]) => `${ACCURACY_FROM[key] || key} for ${n}`)
    .join("; ");
  let note = `Your recording, ${name}: ${rec.fixes} fixes over ${fixed(rec.duration_s, 0)} s and ${fixed(rec.path_m, 0)} m of track, ` +
    `simulated in this tab. It was not uploaded, and only meters and seconds from its first fix were kept. Accuracy: ${sources}.` +
    (rec.skipped ? ` ${rec.skipped} points were skipped (no usable time or position, or a repeated time).` : "");
  if (rec.apart) {
    const gap = rec.apart;
    note += ` The second phone stands in for the tag. The phones were apart by a median ${fixed(gap.median_m, 1)} m ` +
      `(95% within ${fixed(gap.p95_m, 1)} m) over ${fixed(gap.shared_s, 0)} s; their reported accuracy predicts ${fixed(gap.predicted_median_m, 1)} m, ` +
      `so it looks ${gap.verdict}. Errors both phones share cancel, so each is off by at least this much.`;
  }
  return note;
}

function readText(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(new Error(`could not read ${file.name}`));
    reader.readAsText(file);
  });
}

async function openRecording(files) {
  if (!state.python) {
    showMessage(`This build of the site has no Python runtime. The command line gives the same trace: ${SIM_CMD}`, true);
    return;
  }
  if (files.length > 2) {
    showMessage("Open one recording, or two of the same walk from two phones.", true);
    return;
  }
  const big = files.find((f) => f.size > 50e6);
  if (big) {
    showMessage(`${big.name} is over 50 MB, more than a recording should need.`, true);
    return;
  }
  const file = files[0];
  const name = files.map((f) => f.name).join(" and ");
  let texts;
  try {
    texts = await Promise.all(files.map(readText));
  } catch (error) {
    showMessage(`Could not read ${name}: ${error.message}`, true);
    return;
  }
  const id = ++jobs;
  const w = pythonWorker();
  showMessage(`Starting Python in this tab to read ${name}. The first time downloads about 6 MB from this site; nothing is uploaded.`);
  const onMessage = (event) => {
    const msg = event.data;
    if (msg.id !== id) return;
    if (msg.status === "running") {
      showMessage(`Simulating a drone following ${name}…`);
      return;
    }
    w.removeEventListener("message", onMessage);
    if (msg.error) {
      showMessage(`Could not use ${name}: ${msg.error}`, true);
      return;
    }
    const data = JSON.parse(msg.trace);
    const problem = problemWith(data);
    if (problem) {
      showMessage(problem, true);
      return;
    }
    addTrace(`gpx:${name}:${traces.size}`, `Your recording: ${files.length === 2 ? `${file.name} and one more` : file.name}`, data, recordingNote(name, data.recording));
  };
  w.addEventListener("message", onMessage);
  w.postMessage({ id, text: texts[0], second: texts[1] || null });
}

function openAny(files) {
  const gpx = files.filter((f) => /\.gpx$/i.test(f.name));
  if (gpx.length) openRecording(gpx);
  else if (files[0]) openFile(files[0]);
}

// ---- the top-down plot ---------------------------------------------------

function frameFor(trace) {
  // Fit the positions, not the uncertainty circles, so a single wide circle does not
  // shrink every other tick. Wide circles are clipped at the frame's edge.
  let forward = 5;
  let back = 0;
  let side = 3;
  const grow = (x, y) => {
    forward = Math.max(forward, x);
    back = Math.max(back, -x);
    side = Math.max(side, Math.abs(y));
  };
  for (const tick of trace.ticks) {
    for (const r of tick.readings) grow(r.x, r.y);
    if (tick.estimate) grow(tick.estimate.x, tick.estimate.y);
  }
  forward = Math.ceil((forward + 3) / 5) * 5;
  back = Math.max(2, Math.ceil(back + 2));
  side = Math.max(Math.ceil(side + 3), Math.ceil(((forward + back) / 2) * 0.8));
  const scale = W / (2 * side);
  const top = 12;
  return {
    forward, back, side, scale, top,
    height: Math.round((forward + back) * scale + top + 12),
    px: (y) => W / 2 - y * scale, // +y is the drone's left, drawn to the left
    py: (x) => top + (forward - x) * scale, // +x is forward, drawn up
  };
}

function ringLabel(f, r) {
  // Label each range ring where it leaves the frame on the right, away from the rider.
  const u = state.u;
  if (r <= f.side) {
    const y = -Math.sqrt(Math.max(r * r - f.back * f.back, 0));
    return { x: f.px(y) + 4 * u, y: f.py(-f.back) - 5 * u, anchor: "start" };
  }
  const x = Math.sqrt(r * r - f.side * f.side);
  if (x <= f.forward) return { x: W - 5 * u, y: f.py(x) - 5 * u, anchor: "end" };
  const y = -Math.sqrt(r * r - f.forward * f.forward);
  return { x: f.px(y) - 5 * u, y: f.top + 14 * u, anchor: "end" };
}

function plotUnit() {
  // One unit is one screen pixel at the plot's drawn size, so marks and text keep their
  // size on a phone instead of shrinking with the drawing. The drawing is scaled to fit
  // both the width and the capped height.
  const box = els.plot.getBoundingClientRect();
  const height = state.frame ? state.frame.height : W;
  const shrink = Math.max(W / (box.width || W), height / (box.height || height));
  return Math.min(2.6, Math.max(1, shrink));
}

function drawStatic() {
  const f = state.frame;
  clear(els.plot);
  els.plot.setAttribute("viewBox", `0 0 ${W} ${f.height}`);
  const u = (state.u = plotUnit());
  const settings = state.trace.settings || {};
  els.plot.style.setProperty("--plot-font", `${14 * u}px`);
  const defs = svg("defs", {}, els.plot);
  svg("rect", { width: W, height: f.height }, svg("clipPath", { id: "plot-clip" }, defs));
  const root = svg("g", { "clip-path": "url(#plot-clip)" }, els.plot);
  svg("rect", { width: W, height: f.height, fill: "var(--surface)" }, root);
  const ox = f.px(0);
  const oy = f.py(0);

  const hfov = Number(settings.hfov_deg) || 90;
  const half = (hfov * Math.PI) / 360;
  const reach = 4 * (f.forward + f.side);
  const edge = (sign) => `${f.px(sign * reach * Math.sin(half))},${f.py(reach * Math.cos(half))}`;
  svg("path", { d: `M${ox},${oy} L${edge(1)} L${edge(-1)} Z`, fill: "var(--s-camera)", "fill-opacity": 0.06 }, root);

  for (let r = 5; r < Math.hypot(f.forward, f.side); r += 5) {
    svg("circle", { cx: ox, cy: oy, r: r * f.scale, fill: "none", stroke: "var(--grid)", "stroke-width": u }, root);
    const at = ringLabel(f, r);
    svg("text", { x: at.x, y: at.y, "text-anchor": at.anchor, fill: "var(--muted)" }, root).textContent = `${r} m`;
  }
  svg("line", { x1: ox, y1: f.py(f.forward), x2: ox, y2: f.py(-f.back), stroke: "var(--axis)", "stroke-width": u }, root);
  // In a deep frame the wedge's edge leaves the plot, so keep the label inside it.
  svg("text", { x: Math.max(6 * u, f.px(f.forward * Math.sin(half) * 0.62) + 6 * u), y: f.py(f.forward * Math.cos(half) * 0.62) }, root)
    .textContent = `camera view, ${Math.round(hfov)}°`;
  svg("path", { d: `M${ox},${oy - 12 * u} L${ox + 8 * u},${oy + 7 * u} L${ox - 8 * u},${oy + 7 * u} Z`, fill: "var(--ink)" }, root);
  svg("text", { x: ox + 12 * u, y: oy + 6 * u }, root).textContent = "drone";
  state.layer = svg("g", {}, root);

  clear(els.legend);
  const seen = [...new Set(state.trace.ticks.flatMap((t) => t.readings.map((r) => r.source)))];
  for (const source of seen) {
    const info = sourceInfo(source);
    els.legend.appendChild(h("li", {}, h("span", { class: "key", style: { background: info.color } }), info.label));
  }
  els.legend.appendChild(h("li", {}, h("span", { class: "key", style: { background: "var(--ink)", borderRadius: "2px", transform: "rotate(45deg) scale(0.85)" } }), "Fused estimate"));
  els.legend.appendChild(h("li", {}, h("span", { "aria-hidden": "true" }, "+"), "Gate centre"));
  els.legend.appendChild(h("li", {}, h("span", { class: "key", style: { background: "transparent", border: "2px solid var(--muted)" } }), "Hollow: switched off"));
}

function placeLabel(group, placed, x, y, text, side = "right") {
  // Put the label beside its mark; on a collision, step it down and draw a leader line.
  const u = state.u;
  const node = svg("text", { fill: "var(--ink)", class: "halo", "stroke-width": 4 * u }, group);
  node.textContent = text;
  const at = (s) => (s === "right" ? { x: x + 11 * u, anchor: "start" } : { x: x - 11 * u, anchor: "end" });
  let pos = at(side);
  node.setAttribute("x", pos.x);
  node.setAttribute("y", y + 4 * u);
  node.setAttribute("text-anchor", pos.anchor);
  let box = node.getBBox();
  if (box.x + box.width > W - 4 || box.x < 4) {
    pos = at(side === "right" ? "left" : "right");
    node.setAttribute("x", pos.x);
    node.setAttribute("text-anchor", pos.anchor);
    box = node.getBBox();
  }
  const inward = box.x < 4 ? 4 - box.x : box.x + box.width > W - 4 ? W - 4 - (box.x + box.width) : 0;
  if (inward) {
    // Too wide for either side: slide it back into the frame.
    pos = { ...pos, x: pos.x + inward };
    node.setAttribute("x", pos.x);
    box = node.getBBox();
  }
  const hits = (b) => placed.some((p) => b.x < p.x + p.width && b.x + b.width > p.x && b.y < p.y + p.height && b.y + b.height > p.y);
  const step = 15 * u;
  let shift = 0;
  let current = { x: box.x, y: box.y, width: box.width, height: box.height };
  while (hits(current) && shift < 8 * step) {
    shift += step;
    current = { ...current, y: box.y + shift };
  }
  if (shift || inward) {
    node.setAttribute("y", y + 4 * u + shift);
    const lx = pos.anchor === "start" ? pos.x - 2 * u : pos.x + 2 * u;
    svg("line", { x1: x, y1: y, x2: lx, y2: y + shift, stroke: "var(--muted)", "stroke-width": u }, group);
  }
  placed.push(current);
}

function hoverTarget(group, x, y, title, rows) {
  const target = svg("circle", { cx: x, cy: y, r: 13 * state.u, fill: "transparent" }, group);
  target.addEventListener("pointermove", (e) => tip.show(title, rows, e.clientX, e.clientY));
  target.addEventListener("pointerleave", () => tip.hide());
}

function drawTick(tick) {
  const f = state.frame;
  const u = state.u;
  const g = clear(state.layer);
  const discs = svg("g", {}, g);
  const marks = svg("g", {}, g);
  const labels = svg("g", {}, g);
  const hits = svg("g", {}, g);
  const placed = [];

  if (tick.estimate) {
    const e = tick.estimate;
    svg("circle", {
      cx: f.px(e.y), cy: f.py(e.x), r: Math.sqrt(e.variance) * f.scale,
      fill: "none", stroke: "var(--ink)", "stroke-width": 1.5 * u, "stroke-opacity": 0.7,
    }, discs);
  }
  for (const r of tick.readings) {
    if (r.status === "off") continue;
    const info = sourceInfo(r.source);
    svg("circle", {
      cx: f.px(r.y), cy: f.py(r.x), r: Math.sqrt(r.variance) * f.scale,
      fill: r.status === "kept" ? info.color : "none", "fill-opacity": 0.1,
      stroke: info.color, "stroke-width": 1.5 * u, "stroke-opacity": r.status === "kept" ? 1 : 0.5,
    }, discs);
  }

  if (tick.estimate) {
    const x = f.px(tick.estimate.y);
    const y = f.py(tick.estimate.x);
    const s = 6 * u;
    svg("rect", {
      x: x - s, y: y - s, width: 2 * s, height: 2 * s, rx: 2 * u, transform: `rotate(45 ${x} ${y})`,
      fill: "var(--ink)", stroke: "var(--surface)", "stroke-width": 2 * u,
    }, marks);
    placeLabel(labels, placed, x - 2 * u, y, "Fused estimate", "left");
    hoverTarget(hits, x, y, "Fused estimate", [
      { value: `${fixed(tick.estimate.x, 2)} m`, label: "forward" },
      { value: `${fixed(tick.estimate.y, 2)} m`, label: "left" },
      { value: `${fixed(Math.sqrt(tick.estimate.variance), 2)} m`, label: "one sigma" },
    ]);
  }

  const groups = []; // readings drawn within a few pixels of each other share one label
  for (const r of tick.readings) {
    const info = sourceInfo(r.source);
    const x = f.px(r.y);
    const y = f.py(r.x);
    if (r.status === "kept") {
      svg("circle", { cx: x, cy: y, r: 5 * u, fill: info.color, stroke: "var(--surface)", "stroke-width": 2 * u }, marks);
    } else if (r.status === "rejected") {
      svg("circle", { cx: x, cy: y, r: 5 * u, fill: info.color, "fill-opacity": 0.45, stroke: "var(--surface)", "stroke-width": 2 * u }, marks);
    } else {
      svg("circle", { cx: x, cy: y, r: 4.5 * u, fill: "var(--surface)", stroke: info.color, "stroke-width": 2 * u }, marks);
    }
    const suffix = r.status === "kept" ? "" : r.status === "rejected" ? " (rejected)" : " (off)";
    const near = groups.find((g) => Math.hypot(g.x - x, g.y - y) < 9 * u);
    if (near) near.texts.push(info.label + suffix);
    else groups.push({ x, y, texts: [info.label + suffix] });
    hoverTarget(hits, x, y, info.label, [
      { value: r.status, label: "gate", color: info.color },
      { value: `${fixed(r.x, 2)}, ${fixed(r.y, 2)} m`, label: "forward, left" },
      { value: `${fixed(Math.sqrt(r.variance), 2)} m`, label: "one sigma" },
      { value: fixed(r.trust, 2), label: "trust" },
    ]);
  }

  for (const g of groups) placeLabel(labels, placed, g.x, g.y, g.texts.join(", "));

  if (tick.reference) {
    const x = f.px(tick.reference[1]);
    const y = f.py(tick.reference[0]);
    const s = 6 * u;
    svg("path", { d: `M${x - s},${y} H${x + s} M${x},${y - s} V${y + s}`, stroke: "var(--ink-2)", "stroke-width": 1.5 * u }, marks);
  }

  if (!tick.readings.length || !tick.estimate) {
    const text = tick.readings.length ? "No estimate: no reading passed the gate" : "No readings this tick";
    svg("text", { x: W / 2, y: f.py(f.forward * 0.55), "text-anchor": "middle", fill: "var(--ink-2)", style: `font-size: ${16 * u}px` }, labels)
      .textContent = text;
  }
}

// ---- the side panel ------------------------------------------------------

function conditionLines(tick) {
  const lines = [];
  const wx = tick.weather;
  if (!wx) {
    lines.push("Weather unknown: the camera's weight is lowered to 0.8.");
  } else {
    const wet = wx.precipitation_mm > 0.2 || wx.fog;
    const parts = [wx.precipitation_mm > 0 ? `rain ${wx.precipitation_mm} mm` : "dry", `wind ${wx.wind_mps} m/s`];
    if (wx.fog) parts.push("fog");
    let effect = "";
    if (wet) effect = " The camera's weight is lowered to 0.4.";
    if (wx.wind_mps > 8) effect += " High wind lowers it a further 30%.";
    lines.push(`Weather: ${parts.join(", ")}.${effect}`);
  }
  const perSource = (value, all, each) => {
    if (value === null || value === undefined) return;
    if (typeof value === "number") {
      lines.push(`${all} for both companions: ${value}.`);
      return;
    }
    for (const [source, q] of Object.entries(value)) lines.push(`${sourceInfo(source).label} ${each}: ${q}.`);
  };
  perSource(tick.link_quality, "Link quality", "link quality");
  perSource(tick.gnss_quality, "GNSS fix quality", "fix quality");
  if (tick.overrides) {
    for (const [source, factor] of Object.entries(tick.overrides)) {
      lines.push(`Known trouble spot: ${sourceInfo(source).label} weight × ${factor}.`);
    }
  }
  return lines;
}

function gateText(r, tick, gate) {
  if (r.status === "kept") return "kept";
  if (r.status === "off") return "off";
  if (!tick.reference) return "rejected";
  const d = Math.hypot(r.x - tick.reference[0], r.y - tick.reference[1]);
  const limit = Math.sqrt(gate * r.variance);
  return `rejected, ${fixed(d, 1)} m out (limit ${fixed(limit, 1)})`;
}

function commandRows(command) {
  const rows = [
    ["Yaw", "+ turns right", command.yaw],
    ["Forward", "+ toward the rider", command.forward],
    ["Climb", "+ up", command.climb],
  ];
  return rows.flatMap(([label, hint, value]) => {
    const v = Math.max(-1, Math.min(1, value));
    const bar = h("div", { class: "bar", style: { left: `${v < 0 ? 50 + v * 50 : 50}%`, width: `${Math.abs(v) * 50}%` } });
    return [
      h("div", {}, label, h("div", { class: "small muted" }, hint)),
      h("div", { class: "track", role: "img", "aria-label": `${label} ${signed(value)}` }, h("div", { class: "zero" }), bar),
      h("div", { class: "val" }, signed(value)),
    ];
  });
}

function renderPanel(tick) {
  const info = modeInfo(tick.mode);
  const gate = (state.trace.settings && state.trace.settings.gate) || 9;
  const n = state.trace.ticks.length;
  const estimate = tick.estimate
    ? `${fixed(tick.estimate.x, 2)} m forward, ${fixed(tick.estimate.y, 2)} m left, one sigma ${fixed(Math.sqrt(tick.estimate.variance), 2)} m.` +
      (tick.margin ? ` Safety margin: the controller treats the rider as ${fixed(tick.margin, 1)} m closer.` : "")
    : "None this tick.";
  const rows = tick.readings.map((r) => {
    const s = sourceInfo(r.source);
    const attention = tick.attention && r.source in tick.attention ? `× ${fixed(tick.attention[r.source], 2)}` : "×1.00";
    return h("tr", {},
      h("td", { style: { whiteSpace: "nowrap" } }, h("span", { class: "key", style: { background: s.color, marginRight: "6px" } }), s.label),
      h("td", { class: "num" }, `${fixed(r.x, 1)}, ${fixed(r.y, 1)} ± ${fixed(Math.sqrt(r.variance), 1)}`),
      h("td", { class: "num" }, attention),
      h("td", { class: "num" }, fixed(r.trust, 2)),
      h("td", {}, gateText(r, tick, gate)),
    );
  });
  clear(els.panel).append(
    h("div", { class: "tick-head" },
      h("span", { class: "t" }, `t = ${fixed(tick.t, 1)} s`),
      h("span", { class: "chip" }, h("span", { class: "dot", style: { background: info.color } }), `${info.icon} ${info.label}`),
      h("span", { class: "small muted" }, `gain ${fixed(tick.gain, 1)} · tick ${state.index + 1} of ${n}`),
    ),
    h("div", { class: "panel-block" }, h("h3", {}, "Fused estimate"), h("p", { class: "small" }, estimate)),
    // The DOM's append would print a null, so add the block only when there is motion.
    ...(tick.motion ? [h("div", { class: "panel-block" }, h("h3", {}, "Rider's motion"), h("p", { class: "small" },
      `${fixed(Math.hypot(tick.motion.forward, tick.motion.left), 1)} m/s over the ground (± ${fixed(tick.motion.sigma, 1)}), ` +
      `${fixed(tick.motion.forward, 1)} along the drone's nose. Fed forward: ${signed(tick.motion.feed)} of full speed.`))] : []),
    h("div", { class: "panel-block" }, h("h3", {}, "Command"), h("div", { class: "cmd" }, commandRows(tick.command))),
    h("div", { class: "panel-block" },
      h("h3", {}, "Sources"),
      tick.readings.length
        ? h("div", { class: "table-wrap" }, h("table", { class: "compact" },
            h("thead", {}, h("tr", {},
              h("th", {}, "Source"), h("th", { class: "num" }, "x, y ± σ (m)"),
              h("th", { class: "num" }, "Attention"), h("th", { class: "num" }, "Trust"), h("th", {}, "Gate"))),
            h("tbody", {}, rows)))
        : h("p", { class: "small muted" }, "No readings this tick."),
    ),
    h("div", { class: "panel-block" }, h("h3", {}, "Conditions"), h("ul", { class: "conditions" }, conditionLines(tick).map((line) => h("li", {}, line)))),
  );
}

// ---- the mode strip, legend and table -------------------------------------

function runsOf(ticks) {
  const runs = [];
  ticks.forEach((tick, i) => {
    const last = runs[runs.length - 1];
    if (last && last.mode === tick.mode) last.end = i + 1;
    else runs.push({ mode: tick.mode, start: i, end: i + 1 });
  });
  return runs;
}

function fitRunLabels() {
  // Show "icon label" inside a run when it fits, else the icon, else nothing.
  for (const run of els.strip.querySelectorAll(".run")) {
    const info = modeInfo(run.dataset.mode);
    for (const text of [`${info.icon} ${info.label}`, info.icon, ""]) {
      run.textContent = text;
      if (run.scrollWidth <= run.clientWidth) break;
    }
  }
}

function drawStrip() {
  const ticks = state.trace.ticks;
  const n = ticks.length;
  clear(els.strip);
  for (const run of runsOf(ticks)) {
    const info = modeInfo(run.mode);
    els.strip.appendChild(h("div", {
      class: `run${run.mode === "degraded" ? " dark-text" : ""}`,
      "data-mode": run.mode,
      style: { flex: `${run.end - run.start} 1 0`, background: info.color },
    }));
  }
  state.playhead = h("div", { class: "playhead" });
  els.strip.appendChild(state.playhead);
  fitRunLabels();
  $("strip-sub").textContent = `From t = ${fixed(ticks[0].t, 1)} s to ${fixed(ticks[n - 1].t, 1)} s, ${n} ticks. Click or drag to jump.`;
}

function indexAt(event) {
  const box = els.strip.getBoundingClientRect();
  const n = state.trace.ticks.length;
  const i = Math.floor(((event.clientX - box.left) / box.width) * n);
  return Math.max(0, Math.min(n - 1, i));
}

function drawModeLegend() {
  const counts = {};
  for (const tick of state.trace.ticks) counts[tick.mode] = (counts[tick.mode] || 0) + 1;
  clear(els.modeLegend);
  const known = Object.keys(MODES);
  const extra = Object.keys(counts).filter((m) => !known.includes(m));
  for (const mode of [...known, ...extra]) {
    const info = modeInfo(mode);
    const count = counts[mode] || 0;
    els.modeLegend.appendChild(h("li", {},
      h("span", { class: "key", style: { background: info.color } }),
      `${info.icon} ${info.label}: ${count} tick${count === 1 ? "" : "s"}`));
  }
}

function drawTable() {
  const sim = isSimulation(state.trace);
  const head = h("thead", {}, h("tr", {},
    h("th", { class: "num" }, "t (s)"), h("th", {}, "Mode"), h("th", {}, "Kept, rejected, off"),
    h("th", { class: "num" }, "Estimate x, y (m)"), h("th", { class: "num" }, "σ (m)"), h("th", { class: "num" }, "Gain"),
    h("th", { class: "num" }, "Yaw"), h("th", { class: "num" }, "Forward"), h("th", { class: "num" }, "Climb"),
    sim ? h("th", { class: "num" }, "To the rider (m)") : null));
  const body = h("tbody", {}, state.trace.ticks.map((tick) => {
    const count = (s) => tick.readings.filter((r) => r.status === s).length;
    const e = tick.estimate;
    return h("tr", {},
      h("td", { class: "num" }, fixed(tick.t, 1)),
      h("td", {}, `${modeInfo(tick.mode).icon} ${modeInfo(tick.mode).label}`),
      h("td", {}, `${count("kept")}, ${count("rejected")}, ${count("off")}`),
      h("td", { class: "num" }, e ? `${fixed(e.x, 2)}, ${fixed(e.y, 2)}` : "none"),
      h("td", { class: "num" }, e ? fixed(Math.sqrt(e.variance), 2) : ""),
      h("td", { class: "num" }, fixed(tick.gain, 1)),
      h("td", { class: "num" }, signed(tick.command.yaw)),
      h("td", { class: "num" }, signed(tick.command.forward)),
      h("td", { class: "num" }, signed(tick.command.climb)),
      sim ? h("td", { class: "num" }, fixed(tick.world.distance, 1)) : null);
  }));
  clear(els.table).append(head, body);
}

// ---- the simulated follow --------------------------------------------------

const LOSS_MODES = ["degraded", "dead_reckoning", "hold", "return_home_requested"];

function isSimulation(trace) {
  return trace.kind === "simulation" && trace.ticks.every((t) => t.world) && Boolean(trace.summary);
}

function tile(label, value, sub) {
  return h("div", { class: "card tile" }, h("p", { class: "label" }, label), h("p", { class: "value" }, value), h("p", { class: "sub" }, sub));
}

function drawFollow() {
  const sim = isSimulation(state.trace);
  els.follow.hidden = !sim;
  state.follow = null;
  if (!sim) return;
  const s = state.trace.summary;
  const [near, far] = s.band_m;
  // Each tick counts for one tick length, so shares are of the summed mode times.
  const seconds = s.seconds_in_mode;
  const total = Object.values(seconds).reduce((sum, v) => sum + v, 0);
  const lost = LOSS_MODES.reduce((sum, m) => sum + (seconds[m] || 0), 0);
  const detail = LOSS_MODES.filter((m) => seconds[m]).map((m) => `${modeInfo(m).label} ${fixed(seconds[m], 1)} s`).join(", ");
  clear(els.kpis).append(
    tile("Median distance to the rider", `${fixed(s.median_distance_m, 1)} m`,
      s.min_distance_m === undefined ? `The most was ${fixed(s.max_distance_m, 1)} m.`
        : `Closest ${fixed(s.min_distance_m, 1)} m, farthest ${fixed(s.max_distance_m, 1)} m.`),
    s.too_close_share === undefined
      ? tile("Time inside the follow band", percent(s.in_band_share), `${fixed(near, 2)} to ${fixed(far, 2)} m from the rider.`)
      : tile("Time closer than the band", percent(s.too_close_share), `Under ${fixed(near, 2)} m from the rider, the band's near edge.`),
    tile("Time below full tracking", percent(total ? lost / total : 0), detail || "Tracking the whole time."),
    tile("Return-home requested", s.return_home_requested ? "Yes" : "No", "Recorded, not flown."),
  );
  state.follow = { width: els.follow.getBoundingClientRect().width, distance: drawDistance(), world: drawWorld() };
}

function stepFor(span) {
  // A round step that gives three to six labels.
  return niceMax(span / 5);
}

function trim(value) {
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

function drawDistance() {
  const ticks = state.trace.ticks;
  const [near, far] = state.trace.summary.band_m;
  const chart = clear(els.distance);
  // Draw at the rendered size, so 12 px text stays 12 px on a phone.
  const width = Math.max(300, Math.round(chart.getBoundingClientRect().width || 640));
  const height = 230;
  const pad = { left: 50, right: 12, top: 12, bottom: 28 };
  chart.setAttribute("viewBox", `0 0 ${width} ${height}`);
  const t0 = ticks[0].t;
  const t1 = Math.max(ticks[ticks.length - 1].t, t0 + 1);
  const top = niceMax(Math.max(far * 1.6, ...ticks.map((t) => t.world.distance)) * 1.05);
  const x = (t) => pad.left + ((t - t0) / (t1 - t0)) * (width - pad.left - pad.right);
  const y = (d) => height - pad.bottom - (d / top) * (height - pad.top - pad.bottom);

  // Gridlines on a round step, so the labels stay short.
  const ystep = niceMax(top / 4);
  for (let d = 0; d <= top + 1e-9; d += ystep) {
    svg("line", { x1: pad.left, x2: width - pad.right, y1: y(d), y2: y(d), stroke: d ? "var(--grid)" : "var(--axis)" }, chart);
    svg("text", { x: pad.left - 6, y: y(d) + 4, "text-anchor": "end" }, chart).textContent = `${trim(d)} m`;
  }
  const step = stepFor(t1 - t0);
  for (let t = Math.ceil(t0 / step) * step; t <= t1 + 1e-9; t += step) {
    svg("text", { x: x(t), y: height - 8, "text-anchor": "middle" }, chart).textContent = `${trim(t)} s`;
  }
  // The band the controller aims for, pushed out by each tick's safety margin. A tick
  // with no estimate keeps the last margin; nothing is being followed then.
  let carried = 0;
  const margins = ticks.map((t) => (carried = typeof t.margin === "number" ? t.margin : carried));
  const edge = (base) => ticks.map((t, i) => `${x(t.t).toFixed(1)},${y(Math.min(top, base + margins[i])).toFixed(1)}`);
  svg("polygon", { points: [...edge(far), ...edge(near).reverse()].join(" "), fill: "var(--good)", "fill-opacity": 0.18 }, chart);
  svg("line", {
    x1: pad.left, x2: width - pad.right, y1: y(near), y2: y(near),
    stroke: "var(--critical)", "stroke-width": 1.2, "stroke-dasharray": "4 3",
  }, chart);
  // Label the band where the line is farthest above it, so the two do not collide.
  const farthest = ticks.reduce((best, t) => (t.world.distance > best.world.distance ? t : best), ticks[0]);
  const labelX = Math.min(width - pad.right - 40, Math.max(pad.left + 40, x(farthest.t)));
  const labelMargin = margins[ticks.indexOf(farthest)];
  svg("text", { x: labelX, y: y(Math.min(top, far + labelMargin)) - 5, "text-anchor": "middle", class: "halo", "stroke-width": 4 }, chart)
    .textContent = "target band";
  const d = ticks.map((t, i) => `${i ? "L" : "M"}${x(t.t).toFixed(1)},${y(t.world.distance).toFixed(1)}`).join("");
  svg("path", { d, fill: "none", stroke: "var(--ink)", "stroke-width": 2, "stroke-linejoin": "round" }, chart);

  const line = svg("line", { y1: pad.top, y2: height - pad.bottom, stroke: "var(--accent)", "stroke-width": 1.5 }, chart);
  const dot = svg("circle", { r: 5, fill: "var(--ink)", stroke: "var(--surface)", "stroke-width": 2 }, chart);
  const hit = svg("rect", { x: pad.left, y: 0, width: width - pad.left - pad.right, height: height - pad.bottom, fill: "transparent" }, chart);
  const indexAtX = (clientX) => {
    const box = chart.getBoundingClientRect();
    const t = t0 + (((clientX - box.left) / box.width) * width - pad.left) / (width - pad.left - pad.right) * (t1 - t0);
    let best = 0;
    for (let i = 1; i < ticks.length; i++) if (Math.abs(ticks[i].t - t) < Math.abs(ticks[best].t - t)) best = i;
    return best;
  };
  hit.addEventListener("pointermove", (e) => {
    const tick = ticks[indexAtX(e.clientX)];
    const info = modeInfo(tick.mode);
    tip.show(`t = ${fixed(tick.t, 1)} s`, [
      { value: `${fixed(tick.world.distance, 1)} m`, label: "to the rider" },
      { value: `${info.icon} ${info.label}`, color: info.color },
    ], e.clientX, e.clientY);
  });
  hit.addEventListener("pointerleave", () => tip.hide());
  hit.addEventListener("click", (e) => { stop(); seek(indexAtX(e.clientX)); });
  return { x, y, line, dot };
}

function drawWorld() {
  const ticks = state.trace.ticks;
  const plot = clear(els.world);
  const width = Math.max(280, Math.round(plot.getBoundingClientRect().width || 480));
  let minE = Infinity, maxE = -Infinity, minN = Infinity, maxN = -Infinity;
  for (const t of ticks) {
    for (const [e, n] of [t.world.rider, t.world.drone]) {
      minE = Math.min(minE, e); maxE = Math.max(maxE, e);
      minN = Math.min(minN, n); maxN = Math.max(maxN, n);
    }
  }
  // The paths fill the middle; a strip at the top holds the north mark and one at the
  // bottom the scale bar, so neither lands on a path.
  const pad = 16;
  const top = 24;
  const bottom = 30;
  const spanE = Math.max(maxE - minE, 20);
  const spanN = Math.max(maxN - minN, 20);
  const height = Math.round(Math.min(width * 1.15, Math.max(240, ((width - 2 * pad) * spanN) / spanE + top + bottom)));
  const scale = Math.min((width - 2 * pad) / spanE, (height - top - bottom) / spanN);
  const midE = (minE + maxE) / 2;
  const midN = (minN + maxN) / 2;
  const px = (e) => width / 2 + (e - midE) * scale;
  const py = (n) => top + (height - top - bottom) / 2 - (n - midN) * scale;
  plot.setAttribute("viewBox", `0 0 ${width} ${height}`);
  svg("rect", { width, height, fill: "var(--surface)" }, plot);

  const bar = niceMax(spanE / 5);
  svg("line", { x1: width - pad - bar * scale, x2: width - pad, y1: height - 8, y2: height - 8, stroke: "var(--ink-2)", "stroke-width": 2 }, plot);
  svg("text", { x: width - pad - bar * scale - 6, y: height - 4, "text-anchor": "end" }, plot).textContent = `${trim(bar)} m`;
  svg("text", { x: width - pad, y: 16, "text-anchor": "end" }, plot).textContent = "N ↑";

  const path = (key) => ticks.map((t, i) => `${i ? "L" : "M"}${px(t.world[key][0]).toFixed(1)},${py(t.world[key][1]).toFixed(1)}`).join("");
  svg("path", { d: path("rider"), fill: "none", stroke: "var(--s-phone)", "stroke-width": 2, "stroke-linejoin": "round" }, plot);
  svg("path", { d: path("drone"), fill: "none", stroke: "var(--ink-2)", "stroke-width": 1.5, "stroke-dasharray": "5 4", "stroke-linejoin": "round" }, plot);
  const seconds = ticks.filter((t) => t.world.second);
  if (seconds.length > 1) {
    const d = seconds.map((t, i) => `${i ? "L" : "M"}${px(t.world.second[0]).toFixed(1)},${py(t.world.second[1]).toFixed(1)}`).join("");
    svg("path", { d, fill: "none", stroke: "var(--s-tag)", "stroke-width": 1.5, "stroke-linejoin": "round", "stroke-opacity": 0.85 }, plot);
  }
  const [se, sn] = ticks[0].world.rider;
  svg("circle", { cx: px(se), cy: py(sn), r: 4, fill: "var(--surface)", stroke: "var(--ink)", "stroke-width": 1.5 }, plot);
  svg("text", { x: px(se) + 7, y: py(sn) + 4, class: "halo", "stroke-width": 4 }, plot).textContent = "start";

  const link = svg("line", { stroke: "var(--muted)", "stroke-width": 1, "stroke-dasharray": "2 3" }, plot);
  const rider = svg("circle", { r: 6, fill: "var(--s-phone)", stroke: "var(--surface)", "stroke-width": 2 }, plot);
  const drone = svg("path", { d: "M0,-10 L7,7 L-7,7 Z", fill: "var(--ink)", stroke: "var(--surface)", "stroke-width": 1.5 }, plot);

  clear(els.worldLegend).append(
    h("li", {}, h("span", { class: "key-line", style: { color: "var(--s-phone)" }, "aria-hidden": "true" }),
      ticks.some((t) => t.world.second) ? "Rider, midway between the two phones" : "Rider, from the track"),
    h("li", {}, h("span", { class: "key-line dashed", style: { color: "var(--ink-2)" }, "aria-hidden": "true" }), "Drone, simulated"),
    h("li", {}, h("span", { "aria-hidden": "true" }, "▲"), "Drone now, pointing where its nose points"),
    ...(ticks.some((t) => t.world.second)
      ? [h("li", {}, h("span", { class: "key-line", style: { color: "var(--s-tag)" }, "aria-hidden": "true" }), "Second phone, as the tag")]
      : []),
  );
  return { px, py, link, rider, drone };
}

function seekFollow(tick) {
  const f = state.follow;
  if (!f || !tick.world) return;
  const x = f.distance.x(tick.t);
  f.distance.line.setAttribute("x1", x);
  f.distance.line.setAttribute("x2", x);
  f.distance.dot.setAttribute("cx", x);
  f.distance.dot.setAttribute("cy", f.distance.y(tick.world.distance));
  const w = f.world;
  const [re, rn] = tick.world.rider;
  const [de, dn, heading] = tick.world.drone;
  w.rider.setAttribute("cx", w.px(re));
  w.rider.setAttribute("cy", w.py(rn));
  w.drone.setAttribute("transform", `translate(${w.px(de)},${w.py(dn)}) rotate(${heading})`);
  for (const [a, v] of [["x1", w.px(de)], ["y1", w.py(dn)], ["x2", w.px(re)], ["y2", w.py(rn)]]) w.link.setAttribute(a, v);
}

// ---- playback --------------------------------------------------------------

function indexFromHash() {
  const match = /^#tick=(\d+)$/.exec(location.hash);
  if (!match || !state.trace) return null;
  return Math.min(Number(match[1]) - 1, state.trace.ticks.length - 1);
}

function seek(i) {
  const ticks = state.trace.ticks;
  state.index = Math.max(0, Math.min(ticks.length - 1, i));
  const tick = ticks[state.index];
  drawTick(tick);
  renderPanel(tick);
  seekFollow(tick);
  els.scrub.value = String(state.index);
  els.count.textContent = `Tick ${state.index + 1} of ${ticks.length}`;
  state.playhead.style.left = `${((state.index + 0.5) / ticks.length) * 100}%`;
  if (els.select.value === "example") history.replaceState(null, "", `#tick=${state.index + 1}`);
}

function stop() {
  if (state.timer) clearTimeout(state.timer);
  state.timer = null;
  els.play.setAttribute("aria-pressed", "false");
  els.play.textContent = "▶ Play";
}

function play() {
  if (state.timer) {
    stop();
    return;
  }
  const ticks = state.trace.ticks;
  if (state.index >= ticks.length - 1) seek(0);
  els.play.setAttribute("aria-pressed", "true");
  els.play.textContent = "⏸ Pause";
  const step = () => {
    if (state.index >= ticks.length - 1) {
      stop();
      return;
    }
    const dt = ticks[state.index + 1].t - ticks[state.index].t;
    seek(state.index + 1);
    const speed = Number(els.speed.value) || 1;
    state.timer = setTimeout(step, Math.max(25, ((dt > 0 ? dt : 0.5) * 1000) / speed));
  };
  state.timer = setTimeout(step, 0);
}

function wire() {
  $("btn-start").addEventListener("click", () => { stop(); seek(0); });
  $("btn-prev").addEventListener("click", () => { stop(); seek(state.index - 1); });
  $("btn-next").addEventListener("click", () => { stop(); seek(state.index + 1); });
  $("btn-end").addEventListener("click", () => { stop(); seek(state.trace.ticks.length - 1); });
  els.play.addEventListener("click", play);
  els.scrub.addEventListener("input", () => { stop(); seek(Number(els.scrub.value)); });

  let dragging = false;
  els.strip.addEventListener("pointerdown", (e) => {
    dragging = true;
    els.strip.setPointerCapture(e.pointerId);
    stop();
    seek(indexAt(e));
  });
  els.strip.addEventListener("pointermove", (e) => {
    const i = indexAt(e);
    if (dragging) seek(i);
    const tick = state.trace.ticks[i];
    const info = modeInfo(tick.mode);
    tip.show(`t = ${fixed(tick.t, 1)} s, tick ${i + 1}`, [{ value: `${info.icon} ${info.label}`, color: info.color }], e.clientX, e.clientY);
  });
  els.strip.addEventListener("pointerup", () => { dragging = false; });
  els.strip.addEventListener("pointerleave", () => tip.hide());
  if (window.ResizeObserver) {
    new ResizeObserver(() => state.trace && fitRunLabels()).observe(els.strip);
    new ResizeObserver(() => {
      if (!state.trace || Math.abs(plotUnit() - state.u) < 0.05) return;
      drawStatic();
      seek(state.index);
    }).observe(els.plot.parentElement);
    new ResizeObserver(() => {
      // The follow charts are drawn at their rendered size, so redraw them when it changes.
      if (!state.follow || Math.abs(els.follow.getBoundingClientRect().width - state.follow.width) < 8) return;
      drawFollow();
      seekFollow(state.trace.ticks[state.index]);
    }).observe(els.follow);
  }

  document.addEventListener("keydown", (e) => {
    const tag = (e.target && e.target.tagName) || "";
    if (["INPUT", "SELECT", "TEXTAREA"].includes(tag) || !state.trace) return;
    if (e.key === "ArrowRight") { stop(); seek(state.index + 1); e.preventDefault(); }
    if (e.key === "ArrowLeft") { stop(); seek(state.index - 1); e.preventDefault(); }
    // Space on a focused button already clicks it.
    if (e.key === " " && tag !== "BUTTON") { play(); e.preventDefault(); }
  });

  els.file.addEventListener("change", () => {
    if (els.file.files && els.file.files.length) openAny([...els.file.files]);
    els.file.value = "";
  });
  els.gpx.addEventListener("change", () => {
    if (els.gpx.files && els.gpx.files.length) openRecording([...els.gpx.files]);
    els.gpx.value = "";
  });
  window.addEventListener("hashchange", () => {
    const i = indexFromHash();
    if (i !== null && i !== state.index) seek(i);
  });
  els.select.addEventListener("change", () => {
    const entry = traces.get(els.select.value);
    if (entry) load(entry.trace, entry.note);
  });
  document.addEventListener("dragover", (e) => {
    e.preventDefault();
    document.body.classList.add("dragging");
  });
  document.addEventListener("dragleave", (e) => {
    if (e.target === document.documentElement || e.clientX <= 0 || e.clientY <= 0) document.body.classList.remove("dragging");
  });
  document.addEventListener("drop", (e) => {
    e.preventDefault();
    document.body.classList.remove("dragging");
    const files = e.dataTransfer ? [...e.dataTransfer.files] : [];
    if (files.length) openAny(files);
  });
}

async function main() {
  initPage();
  wire();
  fetchJSON("data/build.json").then((b) => { state.python = Boolean(b.python); }).catch(() => {});
  try {
    const trace = await fetchJSON("data/replay-example.json");
    const note = trace.note || "Example trace.";
    traces.set("example", { trace, note });
    load(trace, note);
  } catch (error) {
    showMessage(`Could not load the example trace (${error.message}). Build the site with: PYTHONPATH=src python3 -m follow_me.website`, true);
  }
  for (const [key, file, label] of [
    ["sim-example", "data/sim-example.json", "Example: a simulated follow, made up"],
    ["sim-camera", "data/sim-example-camera.json", "Example: the same ride with a camera"],
    ["sim-before", "data/sim-example-before.json", "Example: the same ride, original controller"],
  ]) {
    try {
      const trace = await fetchJSON(file);
      traces.set(key, { trace, note: trace.note });
      els.select.appendChild(h("option", { value: key }, label));
    } catch (error) {
      // The first example still works without these.
    }
  }
}

main();
