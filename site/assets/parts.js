// Parts page: shows each part from cad/ in 3D, re-renders it with OpenSCAD in a worker
// when a slider moves, and offers the STL and the OpenSCAD source for download.
import { clear, fetchJSON, fixed, h, initPage } from "./common.js";
import { meshStats } from "./stl.js";

const $ = (id) => document.getElementById(id);
const state = { data: null, part: null, values: {}, bytes: null, viewer: null, sources: {}, renderId: 0, timer: null, worker: null };

// ---- the 3D view -------------------------------------------------------------

function cssColor(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || "#888888";
}

async function createViewer(container) {
  const THREE = await import("three");
  const { OrbitControls } = await import("three/addons/controls/OrbitControls.js");
  const { STLLoader } = await import("three/addons/loaders/STLLoader.js");

  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  container.appendChild(renderer.domElement);
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(35, 4 / 3, 0.5, 5000);
  camera.up.set(0, 0, 1); // OpenSCAD's Z is up
  const controls = new OrbitControls(camera, renderer.domElement);
  const sky = new THREE.HemisphereLight(0xffffff, 0x303030, 0.9);
  sky.position.set(0, 0, 1);
  scene.add(sky);
  const sun = new THREE.DirectionalLight(0xffffff, 2.2);
  scene.add(sun);
  const fill = new THREE.DirectionalLight(0xffffff, 0.5);
  scene.add(fill);
  const material = new THREE.MeshStandardMaterial({ roughness: 0.6, metalness: 0 });
  const loader = new STLLoader();
  let mesh = null;
  let grid = null;
  let gridAt = null; // where the build-plate grid goes, rebuilt in the theme's colour

  const draw = () => renderer.render(scene, camera);
  controls.addEventListener("change", draw);

  const placeGrid = () => {
    if (grid) {
      scene.remove(grid);
      grid.geometry.dispose();
      grid.material.dispose();
      grid = null;
    }
    if (!gridAt) return;
    const color = new THREE.Color(cssColor("--muted"));
    grid = new THREE.GridHelper(gridAt.cells * 10, gridAt.cells, color, color); // 10 mm squares
    grid.rotation.x = Math.PI / 2;
    grid.position.set(gridAt.x, gridAt.y, gridAt.z);
    grid.material.transparent = true;
    grid.material.opacity = 0.45;
    scene.add(grid);
  };

  const recolor = () => {
    scene.background = new THREE.Color(cssColor("--surface"));
    material.color = new THREE.Color(cssColor("--accent"));
    placeGrid();
    draw();
  };

  const resize = () => {
    const width = container.clientWidth || 600;
    const height = Math.round(Math.min(width * 0.72, 520));
    renderer.setSize(width, height);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    draw();
  };

  const frame = () => {
    if (!mesh) return;
    const box = mesh.geometry.boundingBox;
    const centre = new THREE.Vector3();
    box.getCenter(centre);
    const size = new THREE.Vector3();
    box.getSize(size);
    const span = Math.max(size.x, size.y, size.z, 10);
    controls.target.copy(centre);
    camera.position.set(centre.x + span * 1.1, centre.y - span * 1.5, centre.z + span * 1.1);
    sun.position.set(centre.x + span, centre.y - span * 0.6, centre.z + span * 2);
    fill.position.set(centre.x - span * 1.5, centre.y + span, centre.z + span * 0.5);
    camera.near = span / 100;
    camera.far = span * 50;
    camera.updateProjectionMatrix();
    controls.update();
    draw();
  };

  const show = (bytes, refit) => {
    const buffer = bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
    const geometry = loader.parse(buffer);
    geometry.computeBoundingBox();
    if (mesh) {
      scene.remove(mesh);
      mesh.geometry.dispose();
    }
    mesh = new THREE.Mesh(geometry, material);
    scene.add(mesh);
    const box = geometry.boundingBox;
    const size = Math.max(box.max.x - box.min.x, box.max.y - box.min.y);
    gridAt = {
      cells: Math.max(10, Math.ceil((size * 1.6) / 10)),
      x: (box.min.x + box.max.x) / 2,
      y: (box.min.y + box.max.y) / 2,
      z: box.min.z - 0.05,
    };
    recolor();
    if (refit) frame();
    else draw();
  };

  if (window.ResizeObserver) new ResizeObserver(resize).observe(container);
  new MutationObserver(recolor).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", recolor);
  resize();
  return { show, frame };
}

// ---- rendering ---------------------------------------------------------------

function overrides() {
  const changed = {};
  for (const p of state.part.params) {
    if (state.values[p.name] !== p.default) changed[p.name] = state.values[p.name];
  }
  return changed;
}

async function sourceOf(part) {
  if (!state.sources[part.id]) {
    const response = await fetch(part.scad);
    if (!response.ok) throw new Error(`${part.scad}: ${response.status}`);
    state.sources[part.id] = await response.text();
  }
  return state.sources[part.id];
}

function renderInBrowser(source, changed) {
  if (!state.worker) state.worker = new Worker(new URL("./parts-worker.js", import.meta.url), { type: "module" });
  const id = ++state.renderId;
  return new Promise((resolve, reject) => {
    const onMessage = (event) => {
      if (event.data.id !== id) return;
      state.worker.removeEventListener("message", onMessage);
      if (event.data.error) reject(new Error(event.data.error));
      else resolve({ ...event.data, id });
    };
    state.worker.addEventListener("message", onMessage);
    state.worker.postMessage({ id, source, overrides: changed });
  });
}

function setStatus(text, isError = false) {
  $("render-status").textContent = text;
  $("render-status").classList.toggle("error", isError);
}

function showBytes(bytes, refit) {
  state.bytes = bytes;
  $("download-stl").disabled = false;
  if (state.viewer) state.viewer.show(bytes, refit);
  renderCard();
}

async function rerender(refit = false) {
  const part = state.part;
  const changed = overrides();
  if (!Object.keys(changed).length && part.stl) return loadPrebuilt(part, refit);
  if (!state.data.openscad) {
    setStatus("This build of the site cannot render in the browser. Download the OpenSCAD source and open it in OpenSCAD.");
    return;
  }
  setStatus("Rendering in your browser…");
  try {
    const result = await renderInBrowser(await sourceOf(part), changed);
    if (result.id !== state.renderId || part !== state.part) return; // a newer render is on its way
    const note = result.warnings.length ? ` OpenSCAD warned: ${result.warnings.join(" ")}` : "";
    setStatus(`Rendered in your browser in ${fixed(result.ms / 1000, 1)} s.${note}`, Boolean(result.warnings.length));
    showBytes(new Uint8Array(result.buffer), refit);
  } catch (error) {
    setStatus(`OpenSCAD could not render these settings: ${error.message}`, true);
  }
}

async function loadPrebuilt(part, refit) {
  setStatus("Loading…");
  try {
    const response = await fetch(part.stl);
    if (!response.ok) throw new Error(`${part.stl}: ${response.status}`);
    const bytes = new Uint8Array(await response.arrayBuffer());
    if (part !== state.part) return;
    setStatus("Default settings, rendered when the site was built.");
    showBytes(bytes, refit);
  } catch (error) {
    setStatus(`Could not load the STL: ${error.message}`, true);
  }
}

// ---- the panels ------------------------------------------------------------------

function renderTabs() {
  const tabs = clear($("part-tabs"));
  for (const part of state.data.parts) {
    tabs.appendChild(h("button", {
      type: "button", class: "btn", "aria-pressed": part === state.part ? "true" : "false",
      onclick: () => selectPart(part.id),
    }, part.title));
  }
}

function renderCard() {
  const part = state.part;
  const facts = [];
  if (state.bytes) {
    const stats = meshStats(state.bytes);
    const cm3 = stats.volume / 1000;
    facts.push(["Size on the plate", `${stats.size.map((s) => fixed(s, 1)).join(" × ")} mm`]);
    facts.push(["Solid volume", `${fixed(cm3, 1)} cm³`]);
    const solid = Object.entries(state.data.density).map(([m, d]) => `${Math.round(cm3 * d)} g of ${m}`).join(", ");
    facts.push(["If printed fully solid", solid]);
  }
  if (part.catalog) facts.push(["Parts catalog estimate", `${part.catalog.grams} g of ${part.catalog.material}`]);
  facts.push(["Material", part.material], ["Layer height", `${part.layer_mm} mm`], ["Walls", String(part.walls)],
    ["Infill", part.infill], ["Supports", part.supports], ["Stage", part.gate]);
  const measured = part.measured
    ? h("p", { class: "small" }, h("strong", {}, "Measured: "), `${part.measured.grams} g, ${part.measured.minutes} min in ${part.measured.material}, ${part.measured.date}.`)
    : h("p", { class: "small muted" }, "Nothing measured yet. A slicer gives the real grams and time for your settings, and a scale gives the printed weight; those numbers replace the catalog's estimate.");
  clear($("part-card")).append(
    h("p", { class: "eyebrow" }, part.status === "unprinted" ? "Unprinted and untested" : part.status),
    h("h2", {}, part.title),
    h("p", { class: "small" }, part.purpose),
    h("dl", { class: "facts parts-facts" }, facts.flatMap(([k, v]) => [h("dt", {}, k), h("dd", {}, v)])),
    measured,
    h("h3", {}, "How to print it"),
    h("p", { class: "small" }, part.orientation),
    h("h3", {}, "Test before you rely on it"),
    h("p", { class: "small" }, part.test),
    h("h3", {}, "Safety"),
    h("p", { class: "small" }, part.safety),
  );
}

function formatValue(p, value) {
  if (typeof value === "number") {
    const digits = p.step && p.step < 1 ? String(p.step).split(".")[1].length : 0;
    return value.toFixed(digits);
  }
  return String(value);
}

function renderParams() {
  const form = clear($("params"));
  const canRender = state.data.openscad;
  $("params-note").textContent = canRender
    ? "Changes render in your browser with OpenSCAD, about a second each. The defaults are guesses: measure your own hardware."
    : "This build of the site cannot render in the browser, so the sliders are off. Download the source and change the same values in OpenSCAD's Customizer.";
  const groups = new Map();
  for (const p of state.part.params) {
    if (!groups.has(p.group)) groups.set(p.group, []);
    groups.get(p.group).push(p);
  }
  for (const [group, list] of groups) {
    const fieldset = h("fieldset", {}, h("legend", {}, group));
    for (const p of list) {
      const id = `param-${p.name}`;
      const output = h("output", { for: id }, formatValue(p, state.values[p.name]));
      let input;
      if (p.choices && p.choices.length) {
        input = h("select", { id, disabled: !canRender }, p.choices.map((c) => h("option", { value: c, selected: String(state.values[p.name]) === c }, c)));
      } else {
        input = h("input", { id, type: "range", min: p.min, max: p.max, step: p.step, value: state.values[p.name], disabled: !canRender });
      }
      input.addEventListener("input", () => {
        const raw = input.value;
        state.values[p.name] = p.choices && p.choices.length ? raw : Number(raw);
        output.textContent = formatValue(p, state.values[p.name]);
        clearTimeout(state.timer);
        state.timer = setTimeout(() => rerender(false), 300);
      });
      fieldset.appendChild(h("div", { class: "param" }, h("label", { for: id }, p.label), input, output));
    }
    form.appendChild(fieldset);
  }
}

function download(name, blob) {
  const url = URL.createObjectURL(blob);
  const link = h("a", { href: url, download: name });
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

async function downloadScad() {
  const part = state.part;
  let text = await sourceOf(part);
  const changed = overrides();
  if (Object.keys(changed).length) {
    // OpenSCAD uses the last value given to a top-level variable, as with its -D option.
    text += "\n// Values chosen on the website\n";
    for (const [name, value] of Object.entries(changed)) text += `${name} = ${typeof value === "string" ? JSON.stringify(value) : value};\n`;
  }
  download(`${part.id}${Object.keys(changed).length ? "-custom" : ""}.scad`, new Blob([text], { type: "text/plain" }));
}

function selectPart(id) {
  const part = state.data.parts.find((p) => p.id === id) || state.data.parts[0];
  state.part = part;
  state.values = Object.fromEntries(part.params.map((p) => [p.name, p.default]));
  state.bytes = null;
  $("download-stl").disabled = true;
  history.replaceState(null, "", `#${part.id}`);
  renderTabs();
  renderParams();
  renderCard();
  if (part.stl) loadPrebuilt(part, true);
  else rerender(true);
}

async function main() {
  initPage();
  try {
    state.data = await fetchJSON("data/parts.json");
  } catch (error) {
    setStatus(`Could not load the parts list (${error.message}).`, true);
    return;
  }
  if (state.data.viewer) {
    try {
      state.viewer = await createViewer($("viewer"));
    } catch (error) {
      $("viewer").textContent = `The 3D view could not start (${error.message}). The downloads still work.`;
    }
  } else {
    $("viewer").textContent = "This build of the site has no 3D viewer (it was built without --vendor). The downloads still work.";
  }
  $("download-stl").addEventListener("click", () => {
    if (state.bytes) download(`${state.part.id}${Object.keys(overrides()).length ? "-custom" : ""}.stl`, new Blob([state.bytes], { type: "model/stl" }));
  });
  $("download-scad").addEventListener("click", downloadScad);
  $("reset-view").addEventListener("click", () => state.viewer && state.viewer.frame());
  $("reset-params").addEventListener("click", () => selectPart(state.part.id));
  window.addEventListener("hashchange", () => {
    const id = location.hash.slice(1);
    if (id !== state.part.id && state.data.parts.some((p) => p.id === id)) selectPart(id);
  });
  selectPart(location.hash.slice(1));
}

main();
