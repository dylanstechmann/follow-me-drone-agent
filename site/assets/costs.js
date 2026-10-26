// Cost explorer: draws data/costs.json, which the cost model in src/follow_me/bom.py writes.
import { clear, fetchJSON, h, initPage, makeTooltip, percent, svg, usd, usdRange } from "./common.js";

const $ = (id) => document.getElementById(id);
const tip = makeTooltip();
const state = { data: null, pass: null, drones: 0 };

const FRESHNESS = [
  { key: "fresh", label: "Seen in the last 12 months", color: "var(--ramp-1)" },
  { key: "stale", label: "Older than 12 months", color: "var(--ramp-2)" },
  { key: "year only", label: "Year only", color: "var(--ramp-3)" },
  { key: "undated", label: "No date", color: "var(--ramp-4)" },
];

function passNumber(pass) {
  const match = /^pass(\d+)/.exec(pass.id);
  return match ? Number(match[1]) : null;
}

function shortTitle(pass) {
  const head = pass.title.split(":")[0];
  return head.length > 46 ? `${head.slice(0, 44)}…` : head;
}

function passName(pass) {
  const n = passNumber(pass);
  return n === null ? shortTitle(pass) : `Pass ${n}: ${shortTitle(pass)}`;
}

function niceMax(value) {
  const steps = [1, 1.2, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10];
  const power = 10 ** Math.floor(Math.log10(value));
  for (const s of steps) if (s * power >= value) return s * power;
  return 10 * power;
}

function itemName(id) {
  const item = state.data.items[id];
  return item ? item.name : id;
}

// ---- headline tiles ------------------------------------------------------

function tile(label, value, sub) {
  return h("div", { class: "card tile" }, h("p", { class: "label" }, label), h("p", { class: "value" }, value), h("p", { class: "sub" }, sub));
}

function renderKpis() {
  const { passes, price_summary: prices, budget_usd: budget } = state.data;
  const lowest = (list) => list.reduce((best, p) => (best === null || p.core[0] < best.core[0] ? p : best), null);
  const bench = lowest(passes.filter((p) => !p.flying));
  const flying = lowest(passes.filter((p) => p.flying));
  const kpis = $("kpis");
  clear(kpis);
  if (bench) kpis.appendChild(tile("Cheapest bench kit (no flying drone)", usdRange(bench.core), `${passName(bench)}. It ${bench.budget_status}.`));
  if (flying) kpis.appendChild(tile("Cheapest flying drone modelled", usdRange(flying.core), `${passName(flying)}. Per drone, ${flying.budget_status}.`));
  kpis.appendChild(tile("Sourced prices seen in the last 12 months", `${prices.fresh} of ${prices.sourced}`, `${prices.placeholders} more inputs are guesses (placeholders).`));
  kpis.appendChild(tile("Working budget", usd(budget, true), "For the bench and software work. A flying drone is a separate question."));
}

// ---- the pass chart --------------------------------------------------------

function renderPassChart() {
  const { passes, budget_usd: budget } = state.data;
  const max = niceMax(Math.max(...passes.map((p) => p.core[1])) * 1.02);
  const pct = (v) => `${(v / max) * 100}%`;
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((f) => f * max);
  const chart = clear($("pass-chart"));
  const lines = (track) => {
    for (const t of ticks.slice(1)) track.appendChild(h("div", { class: "pass-grid", style: { left: pct(t) } }));
    track.appendChild(h("div", { class: "budget-line", style: { left: pct(budget) } }));
  };

  const header = h("div", { class: "pass-row static", style: { paddingBottom: "0" } }, h("div"), h("div", { class: "pass-track", style: { height: "18px" } },
    h("span", { class: "budget-label", style: { left: pct(budget), top: "0" } }, `${usd(budget, true)} budget`)));
  header.setAttribute("aria-hidden", "true");
  chart.appendChild(header);

  for (const pass of passes) {
    const selected = pass.id === state.pass.id;
    const track = h("div", { class: "pass-track" });
    lines(track);
    track.appendChild(h("div", { class: "pass-bar", style: { left: pct(pass.core[0]), width: pct(pass.core[1] - pass.core[0]) } }));
    if (selected) {
      const roomRight = pass.core[1] / max < 0.66;
      const style = roomRight
        ? { left: `calc(${pct(pass.core[1])} + 6px)` }
        : { right: `calc(${100 - (pass.core[0] / max) * 100}% + 6px)` };
      track.appendChild(h("span", { class: "pass-value", style }, usdRange(pass.core)));
    }
    const row = h("button", {
      type: "button", class: "pass-row", "aria-pressed": selected ? "true" : "false",
      "aria-label": `${passName(pass)}: ${usdRange(pass.core)} per drone`,
      onclick: () => selectPass(pass.id),
    }, h("div", { class: "pass-label" }, h("b", {}, passNumber(pass) === null ? "" : `${passNumber(pass)} `), h("span", {}, shortTitle(pass))), track);
    row.addEventListener("pointermove", (e) => tip.show(passName(pass), [
      { value: usdRange(pass.core), label: "per drone" },
      { value: usdRange(pass.cash_min_orders), label: "cash at minimum orders" },
      { value: pass.budget_status, label: "" },
    ], e.clientX, e.clientY));
    row.addEventListener("pointerleave", () => tip.hide());
    chart.appendChild(row);
  }

  const axis = h("div", { class: "pass-track", style: { height: "20px" } });
  for (const t of ticks) axis.appendChild(h("span", { class: "pass-value", style: { left: pct(t), transform: "translateX(-50%)", color: "var(--muted)" } }, usd(t, true)));
  const axisRow = h("div", { class: "pass-row static" }, h("div"), axis);
  axisRow.setAttribute("aria-hidden", "true");
  chart.appendChild(axisRow);

  const table = clear($("pass-table"));
  table.appendChild(h("thead", {}, h("tr", {},
    h("th", {}, "Pass"), h("th", { class: "num" }, "Core low"), h("th", { class: "num" }, "Core high"),
    h("th", { class: "num" }, "Cash at minimum orders"), h("th", { class: "num" }, "Made in house"),
    h("th", { class: "num" }, "Owner-designed"), h("th", {}, "Budget"))));
  table.appendChild(h("tbody", {}, passes.map((p) => h("tr", {},
    h("td", {}, p.title, h("div", { class: "small muted" }, p.id)),
    h("td", { class: "num" }, usd(p.core[0])), h("td", { class: "num" }, usd(p.core[1])),
    h("td", { class: "num" }, usdRange(p.cash_min_orders)),
    h("td", { class: "num" }, percent(p.made_share)), h("td", { class: "num" }, percent(p.designed_share)),
    h("td", {}, p.budget_status)))));
}

// ---- the pass detail -------------------------------------------------------

function renderDetail() {
  const pass = state.pass;
  const n = state.data.drone_counts[state.drones];
  const base = state.data.passes.find((p) => p.id === pass.based_on);
  const facts = [
    ["Core cost per drone", usdRange(pass.core)],
    ["Cash at minimum orders", usdRange(pass.cash_min_orders)],
    [`Cash for ${n.toLocaleString("en-US")} drone${n === 1 ? "" : "s"}`, usdRange(pass.cash[state.drones])],
    ["Made in house", `${percent(pass.made_share)} of the core cost`],
    ["The owner's design", `${percent(pass.designed_share)} of the core cost`],
    ["Budget", pass.budget_status],
    ["Guesses (placeholders)", String(pass.placeholders)],
    ["Sourced prices seen in the last 12 months", `${pass.fresh} of ${pass.sourced}`],
  ];
  if (pass.optional[1] > 0) facts.push(["Optional extras, not in the core", usdRange(pass.optional)]);
  const changes = [];
  if (pass.added.length) changes.push(h("p", { class: "small" }, h("strong", {}, "Adds: "), pass.added.map(itemName).join(", ")));
  if (pass.removed.length) changes.push(h("p", { class: "small" }, h("strong", {}, "Removes: "), pass.removed.map(itemName).join(", ")));
  const rows = pass.items.map((id) => {
    const item = state.data.items[id];
    const guess = item.status === "placeholder" ? h("span", { class: "badge guess" }, "guess") : null;
    return h("tr", {},
      h("td", {}, item.name, item.optional ? h("span", { class: "small muted" }, " (optional)") : null, " ", guess),
      h("td", {}, item.path.replace(/_/g, " ")),
      h("td", { class: "num" }, String(item.qty)),
      h("td", { class: "num" }, usdRange(item.unit)));
  });
  clear($("pass-detail")).append(
    h("p", { class: "eyebrow" }, passNumber(pass) === null ? pass.id : `Pass ${passNumber(pass)}`),
    h("h2", {}, pass.title),
    base
      ? h("p", { class: "small muted" }, "Changes ", h("a", { href: "#", onclick: (e) => { e.preventDefault(); selectPass(base.id); } }, passName(base)), ".")
      : h("p", { class: "small muted" }, "The starting point for every other pass."),
    h("dl", { class: "facts" }, facts.flatMap(([k, v]) => [h("dt", {}, k), h("dd", {}, v)])),
    h("p", { class: "small" }, pass.note),
    ...changes,
    h("details", {}, h("summary", {}, `Every item in this pass (${pass.items.length})`),
      h("div", { class: "table-wrap" }, h("table", {},
        h("thead", {}, h("tr", {}, h("th", {}, "Item"), h("th", {}, "How it is obtained"), h("th", { class: "num" }, "Qty"), h("th", { class: "num" }, "Each"))),
        h("tbody", {}, rows)))),
  );
}

// ---- the drone-count chart -------------------------------------------------

function renderDrones() {
  const counts = state.data.drone_counts;
  const pass = state.pass;
  const i = state.drones;
  const n = counts[i];
  $("drone-out").textContent = n.toLocaleString("en-US");
  $("drone-title").textContent = `Cost per drone as the number of drones grows: ${passName(pass)}`;
  clear($("drone-kpis")).append(
    tile(`Cash to build ${n.toLocaleString("en-US")}`, usdRange(pass.cash[i], true), "Every order at least its minimum."),
    tile("Per drone at that count", usdRange(pass.per_drone[i], true), `For one drone: ${usdRange(pass.per_drone[0], true)}.`),
    tile("Core cost per drone", usdRange(pass.core, true), "The parts one drone needs, before minimum orders."),
  );

  const W = 720;
  const H = 280;
  const m = { left: 64, right: 56, top: 14, bottom: 34 };
  const plotW = W - m.left - m.right;
  const plotH = H - m.top - m.bottom;
  const logMax = Math.log10(counts[counts.length - 1]);
  const x = (count) => m.left + (Math.log10(count) / logMax) * plotW;
  const yMax = niceMax(Math.max(...pass.per_drone.map((v) => v[1])) * 1.05);
  const y = (v) => m.top + plotH - (v / yMax) * plotH;
  const chart = clear($("drone-chart"));
  chart.setAttribute("viewBox", `0 0 ${W} ${H}`);

  for (let k = 0; k <= 4; k += 1) {
    const v = (yMax / 4) * k;
    svg("line", { x1: m.left, x2: W - m.right, y1: y(v), y2: y(v), stroke: k === 0 ? "var(--axis)" : "var(--grid)", "stroke-width": 1 }, chart);
    svg("text", { x: m.left - 8, y: y(v) + 4, "text-anchor": "end" }, chart).textContent = usd(v, true);
  }
  for (const count of counts) {
    svg("text", { x: x(count), y: H - m.bottom + 18, "text-anchor": "middle" }, chart).textContent = count.toLocaleString("en-US");
  }
  svg("text", { x: m.left + plotW / 2, y: H - 2, "text-anchor": "middle" }, chart).textContent = "Number of drones (log scale)";

  const lowPts = counts.map((c, k) => [x(c), y(pass.per_drone[k][0])]);
  const highPts = counts.map((c, k) => [x(c), y(pass.per_drone[k][1])]);
  const path = (pts) => pts.map(([px, py], k) => `${k ? "L" : "M"}${px},${py}`).join(" ");
  svg("path", { d: `${path(highPts)} L${[...lowPts].reverse().map(([px, py]) => `${px},${py}`).join(" L")} Z`, fill: "var(--accent)", "fill-opacity": 0.1 }, chart);
  for (const pts of [highPts, lowPts]) {
    svg("path", { d: path(pts), fill: "none", stroke: "var(--accent)", "stroke-width": 2, "stroke-linejoin": "round", "stroke-linecap": "round" }, chart);
  }
  svg("text", { x: highPts[highPts.length - 1][0] + 8, y: highPts[highPts.length - 1][1] + 4 }, chart).textContent = "high";
  svg("text", { x: lowPts[lowPts.length - 1][0] + 8, y: lowPts[lowPts.length - 1][1] + 4 }, chart).textContent = "low";

  svg("line", { x1: x(n), x2: x(n), y1: m.top, y2: m.top + plotH, stroke: "var(--ink-2)", "stroke-width": 1 }, chart);
  for (const pts of [highPts, lowPts]) {
    pts.forEach(([px, py], k) => {
      svg("circle", { cx: px, cy: py, r: k === i ? 6 : 4, fill: "var(--accent)", stroke: "var(--surface)", "stroke-width": 2 }, chart);
    });
  }

  const cross = svg("line", { y1: m.top, y2: m.top + plotH, stroke: "var(--muted)", "stroke-width": 1, visibility: "hidden" }, chart);
  const hit = svg("rect", { x: m.left, y: m.top, width: plotW, height: plotH, fill: "transparent" }, chart);
  const nearest = (event) => {
    const box = chart.getBoundingClientRect();
    const sx = ((event.clientX - box.left) / box.width) * W;
    let best = 0;
    counts.forEach((c, k) => { if (Math.abs(x(c) - sx) < Math.abs(x(counts[best]) - sx)) best = k; });
    return best;
  };
  hit.addEventListener("pointermove", (e) => {
    const k = nearest(e);
    cross.setAttribute("x1", x(counts[k]));
    cross.setAttribute("x2", x(counts[k]));
    cross.setAttribute("visibility", "visible");
    tip.show(`${counts[k].toLocaleString("en-US")} drone${counts[k] === 1 ? "" : "s"}`, [
      { value: usdRange(pass.per_drone[k], true), label: "per drone", color: "var(--accent)" },
      { value: usdRange(pass.cash[k], true), label: "cash in total" },
    ], e.clientX, e.clientY);
  });
  hit.addEventListener("pointerleave", () => { cross.setAttribute("visibility", "hidden"); tip.hide(); });
  hit.addEventListener("click", (e) => { state.drones = nearest(e); $("drone-slider").value = String(state.drones); render(); });

  clear($("drone-table")).append(
    h("thead", {}, h("tr", {}, h("th", { class: "num" }, "Drones"), h("th", { class: "num" }, "Per drone"), h("th", { class: "num" }, "Cash in total"))),
    h("tbody", {}, counts.map((c, k) => h("tr", {},
      h("td", { class: "num" }, c.toLocaleString("en-US")),
      h("td", { class: "num" }, usdRange(pass.per_drone[k])),
      h("td", { class: "num" }, usdRange(pass.cash[k]))))),
  );
}

// ---- prices and suppliers ----------------------------------------------------

function renderFreshness() {
  const rows = state.data.prices;
  const sourced = rows.filter((r) => r.status === "snapshot" || r.status === "official");
  const counts = Object.fromEntries(FRESHNESS.map((f) => [f.key, sourced.filter((r) => r.freshness === f.key).length]));
  const total = sourced.length;
  const s = state.data.price_summary;
  $("fresh-sub").textContent = `${total} prices come from a seller's page or a list price. ${s.placeholders} more inputs are guesses, and the rest are estimates or not priced. Cutoff: ${state.data.as_of}.`;
  const stack = clear($("fresh-stack"));
  stack.setAttribute("aria-label", FRESHNESS.map((f) => `${f.label}: ${counts[f.key]}`).join(", "));
  for (const f of FRESHNESS) {
    if (!counts[f.key]) continue;
    const seg = h("div", { style: { flex: `${counts[f.key]} 1 0`, background: f.color } });
    seg.addEventListener("pointermove", (e) => tip.show(f.label, [{ value: `${counts[f.key]} of ${total}`, label: "sourced prices" }], e.clientX, e.clientY));
    seg.addEventListener("pointerleave", () => tip.hide());
    stack.appendChild(seg);
  }
  clear($("fresh-legend")).append(...FRESHNESS.map((f) => h("li", {}, h("span", { class: "key", style: { background: f.color, borderRadius: "3px" } }), `${f.label}: ${counts[f.key]}`)));

  const fill = (select, values) => {
    clear(select).append(h("option", { value: "" }, "All"), ...values.map((v) => h("option", { value: v }, v)));
  };
  fill($("price-status"), [...new Set(rows.map((r) => r.status))].sort());
  fill($("price-fresh"), [...new Set(rows.map((r) => r.freshness))].sort());
  renderPriceTable();
}

function renderPriceTable() {
  const query = $("price-search").value.trim().toLowerCase();
  const status = $("price-status").value;
  const fresh = $("price-fresh").value;
  const named = (r) => (r.kind === "item" ? itemName(r.key) : r.key.replace(/_/g, " "));
  const users = (r) => r.used_by.split(", ").map(itemName).join(", ");
  const rows = state.data.prices
    .filter((r) => (!status || r.status === status) && (!fresh || r.freshness === fresh))
    .filter((r) => !query || `${named(r)} ${r.key} ${users(r)}`.toLowerCase().includes(query))
    .sort((a, b) => (a.freshness !== "fresh") - (b.freshness !== "fresh") || a.kind.localeCompare(b.kind) || named(a).localeCompare(named(b)));
  clear($("price-table")).append(
    h("thead", {}, h("tr", {}, h("th", {}, "Input"), h("th", {}, "Status"), h("th", { class: "num" }, "Low"), h("th", { class: "num" }, "High"), h("th", {}, "Seen"), h("th", {}, "Freshness"))),
    h("tbody", {}, rows.map((r) => h("tr", {},
      h("td", {}, named(r), r.kind === "material" ? h("div", { class: "small muted" }, `material for ${users(r)}`) : null),
      h("td", {}, r.status === "placeholder" ? h("span", { class: "badge guess" }, "guess") : r.status),
      h("td", { class: "num" }, usd(r.low)),
      h("td", { class: "num" }, usd(r.high)),
      h("td", {}, r.checked || "no date"),
      h("td", {}, r.freshness)))),
  );
}

function renderDependency() {
  const dep = state.data.dependency;
  const pass = state.data.passes.find((p) => p.id === dep.pass);
  $("dep-sub").textContent = `Bought parts in ${pass ? passName(pass) : dep.pass}, from the dependency check.`;
  const list = (id, ids) => clear($(id)).append(...(ids.length ? ids.map((i) => h("li", {}, itemName(i))) : [h("li", {}, "None")]));
  list("dep-single", dep.single);
  list("dep-none", dep.none);
}

// ---- state -------------------------------------------------------------------

function render() {
  renderPassChart();
  renderDetail();
  renderDrones();
}

function selectPass(id) {
  state.pass = state.data.passes.find((p) => p.id === id) || state.data.passes[0];
  $("pass-select").value = state.pass.id;
  history.replaceState(null, "", `#${state.pass.id}`);
  render();
}

async function main() {
  initPage();
  try {
    state.data = await fetchJSON("data/costs.json");
  } catch (error) {
    $("kpis").textContent = `Could not load the cost data (${error.message}). Build the site with: PYTHONPATH=src python3 -m follow_me.website`;
    return;
  }
  const data = state.data;
  for (const node of document.querySelectorAll("[data-as-of]")) node.textContent = data.as_of;
  const select = $("pass-select");
  select.append(...data.passes.map((p) => h("option", { value: p.id }, passName(p))));
  select.addEventListener("change", () => selectPass(select.value));
  const slider = $("drone-slider");
  slider.max = String(data.drone_counts.length - 1);
  state.drones = Math.max(0, data.drone_counts.indexOf(20));
  slider.value = String(state.drones);
  slider.addEventListener("input", () => { state.drones = Number(slider.value); renderDetail(); renderDrones(); });
  for (const id of ["price-search", "price-status", "price-fresh"]) $(id).addEventListener("input", renderPriceTable);
  renderKpis();
  renderFreshness();
  renderDependency();
  const fromHash = decodeURIComponent(location.hash.slice(1));
  const flying = data.passes.filter((p) => p.flying);
  const cheapest = flying.reduce((best, p) => (!best || p.core[0] < best.core[0] ? p : best), null);
  selectPass(data.passes.some((p) => p.id === fromHash) ? fromHash : (cheapest || data.passes[0]).id);
  window.addEventListener("hashchange", () => {
    const id = decodeURIComponent(location.hash.slice(1));
    if (data.passes.some((p) => p.id === id) && id !== state.pass.id) selectPass(id);
  });
}

main();
