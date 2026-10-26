// Replay viewer: draws one tick of a trace from `python -m follow_me.replay --json`.
// The trace is computed by the repo's tested Python; this page only draws it.
import { clear, fetchJSON, fixed, h, initPage, makeTooltip, MODES, modeInfo, signed, sourceInfo, svg } from "./common.js";

const TRACE_FORMAT = "follow-me-trace/1";
const MAKE_TRACE = "PYTHONPATH=src python3 -m follow_me.replay --json LOG.json > trace.json";
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
};

const tip = makeTooltip();
const traces = new Map(); // option value -> {trace, note}
const state = { trace: null, index: 0, timer: null, frame: null, layer: null, playhead: null };

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
  els.scrub.max = String(trace.ticks.length - 1);
  showMessage(note);
  seek(indexFromHash() ?? 0);
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
    const key = `file:${file.name}:${traces.size}`;
    const note = `Your file, ${file.name}: ${data.ticks.length} ticks. It stays in this browser tab.` +
      (data.note ? ` Its note: ${data.note}` : "");
    traces.set(key, { trace: data, note });
    els.select.appendChild(h("option", { value: key }, `Your file: ${file.name}`));
    els.select.value = key;
    history.replaceState(null, "", location.pathname);
    load(data, note);
  };
  reader.onerror = () => showMessage(`Could not read ${file.name}.`, true);
  reader.readAsText(file);
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
  svg("text", { x: f.px(f.forward * Math.sin(half) * 0.62) + 6 * u, y: f.py(f.forward * Math.cos(half) * 0.62) }, root)
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
    ? `${fixed(tick.estimate.x, 2)} m forward, ${fixed(tick.estimate.y, 2)} m left, one sigma ${fixed(Math.sqrt(tick.estimate.variance), 2)} m`
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
  const head = h("thead", {}, h("tr", {},
    h("th", { class: "num" }, "t (s)"), h("th", {}, "Mode"), h("th", {}, "Kept, rejected, off"),
    h("th", { class: "num" }, "Estimate x, y (m)"), h("th", { class: "num" }, "σ (m)"), h("th", { class: "num" }, "Gain"),
    h("th", { class: "num" }, "Yaw"), h("th", { class: "num" }, "Forward"), h("th", { class: "num" }, "Climb")));
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
      h("td", { class: "num" }, signed(tick.command.climb)));
  }));
  clear(els.table).append(head, body);
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
    const file = els.file.files && els.file.files[0];
    if (file) openFile(file);
    els.file.value = "";
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
    const file = e.dataTransfer && e.dataTransfer.files[0];
    if (file) openFile(file);
  });
}

async function main() {
  initPage();
  wire();
  try {
    const trace = await fetchJSON("data/replay-example.json");
    const note = trace.note || "Example trace.";
    traces.set("example", { trace, note });
    load(trace, note);
  } catch (error) {
    showMessage(`Could not load the example trace (${error.message}). Build the site with: PYTHONPATH=src python3 -m follow_me.website`, true);
  }
}

main();
