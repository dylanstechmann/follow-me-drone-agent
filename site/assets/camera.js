// Camera page: a person detector in this tab, a marker that says who the rider is, a
// blurred picture, and the repo's follow logic. Frames stay in the tab: each one is
// drawn blurred except for the rider's box, then dropped. Nothing is recorded or sent.
import { clear, fetchJSON, fixed, h, initPage, modeInfo, signed } from "./common.js";
import { INPUT, PAD } from "./detector.js";
import { MARKER_DICTIONARY, MARKER_ID, cropAround, pickRider, shareBox } from "./rider.js";

const $ = (id) => document.getElementById(id);
const els = {
  start: $("start"), stop: $("stop"), photo: $("photo"), fov: $("fov"), status: $("status"),
  view: $("view"), caption: $("caption"), panel: $("panel"), marker: $("marker"), print: $("print-marker"),
};
const frame = document.createElement("canvas"); // the frame being worked on, never shown as is
const square = document.createElement("canvas"); // the detector's letterboxed input
const small = document.createElement("canvas"); // the picture shrunk, for the blur
square.width = square.height = INPUT;
const state = { stream: null, video: null, running: false, rider: null, ready: false, detectMs: 0, frames: 0, crop: null };
let markers = null; // js-aruco2's detector
let detector = null; // camera-worker.js
let follower = null; // follow-worker.js
let jobs = 0;

function say(text, isError = false) {
  els.status.textContent = text;
  els.status.classList.toggle("error", isError);
}

// One request to a worker, answered by its id.
function ask(worker, message, transfer = []) {
  const id = ++jobs;
  return new Promise((resolve, reject) => {
    const onMessage = (event) => {
      if (event.data.id !== id) return;
      worker.removeEventListener("message", onMessage);
      if (event.data.error) reject(new Error(event.data.error));
      else resolve(event.data);
    };
    worker.addEventListener("message", onMessage);
    worker.postMessage({ ...message, id }, transfer);
  });
}

async function setUp(aspect) {
  if (!window.AR || !window.CV) throw new Error("the marker detector did not load (this build may lack its libraries)");
  markers = markers || new AR.Detector({ dictionaryName: MARKER_DICTIONARY });
  detector = detector || new Worker(new URL("./camera-worker.js", import.meta.url), { type: "module" });
  follower = follower || new Worker(new URL("./follow-worker.js", import.meta.url), { type: "module" });
  if (!state.ready) say("Loading the detector and Python in this tab, about 15 MB the first time. Nothing is uploaded.");
  await Promise.all([
    ask(detector, {}),
    ask(follower, { kind: "setup", hfov: Number(els.fov.value), aspect }),
  ]);
  state.ready = true;
}

// Find people and the marker in the frame on `frame`, pick the rider, and step the follow logic.
// While there is a rider, found last frame or being waited for, the detector looks at a
// crop around their last box, enlarged, which finds a small rider far more often, and
// where a briefly missed rider most likely still is. Otherwise it looks at the whole frame.
async function work(width, height) {
  const fctx = frame.getContext("2d", { willReadFrequently: true });
  const seen = markers.detect(fctx.getImageData(0, 0, width, height));
  const sctx = square.getContext("2d", { willReadFrequently: true });
  sctx.fillStyle = `rgb(${PAD}, ${PAD}, ${PAD})`;
  sctx.fillRect(0, 0, INPUT, INPUT);
  state.crop = state.rider ? cropAround(state.rider.box, width, height) : null;
  const region = state.crop || { x: 0, y: 0, side: Math.max(width, height) };
  const scale = INPUT / region.side;
  sctx.drawImage(frame, region.x, region.y, region.side, region.side, 0, 0, INPUT, INPUT);
  const pixels = sctx.getImageData(0, 0, INPUT, INPUT).data.buffer;
  const found = await ask(detector, { pixels, scale }, [pixels]);
  state.detectMs = found.ms;
  const people = found.people.map((p) => ({ ...p, x: p.x + region.x, y: p.y + region.y }));
  state.rider = pickRider(people, seen, state.rider, performance.now());
  const box = state.rider && state.rider.found ? shareBox(state.rider.box, width, height) : null;
  const reply = await ask(follower, { kind: "step", now: performance.now() / 1000, box });
  draw(width, height, seen);
  panel(JSON.parse(reply.tick), people.length, seen.some((m) => m.id === MARKER_ID));
}

// Blur the whole picture, then draw only the rider's box sharp, so anyone the detector
// missed stays blurred too.
function draw(width, height, seen) {
  const view = els.view;
  view.width = width;
  view.height = height;
  const ctx = view.getContext("2d");
  small.width = Math.max(4, Math.round(width / 24));
  small.height = Math.max(3, Math.round(height / 24));
  small.getContext("2d").drawImage(frame, 0, 0, small.width, small.height);
  ctx.imageSmoothingEnabled = true;
  ctx.drawImage(small, 0, 0, width, height);
  const line = Math.max(2, Math.round(width / 240));
  if (state.crop) {
    ctx.setLineDash([6, 6]);
    ctx.lineWidth = 1;
    ctx.strokeStyle = "rgba(255, 255, 255, 0.8)";
    ctx.strokeRect(state.crop.x, state.crop.y, state.crop.side, state.crop.side);
    ctx.setLineDash([]);
  }
  // Only a rider found in this very frame is drawn sharp: a lost rider's last box may hold someone else.
  if (state.rider && state.rider.found) {
    const b = state.rider.box;
    const x = Math.max(0, Math.floor(b.x));
    const y = Math.max(0, Math.floor(b.y));
    const w = Math.min(width, Math.ceil(b.x + b.w)) - x;
    const hgt = Math.min(height, Math.ceil(b.y + b.h)) - y;
    if (w > 0 && hgt > 0) ctx.drawImage(frame, x, y, w, hgt, x, y, w, hgt);
    ctx.lineWidth = line;
    ctx.strokeStyle = getComputedStyle(document.documentElement).getPropertyValue("--good").trim() || "#0ca30c";
    ctx.strokeRect(x, y, w, hgt);
  }
  for (const m of seen.filter((s) => s.id === MARKER_ID)) {
    ctx.beginPath();
    m.corners.forEach((c, i) => (i ? ctx.lineTo(c.x, c.y) : ctx.moveTo(c.x, c.y)));
    ctx.closePath();
    ctx.lineWidth = line;
    ctx.strokeStyle = "#2a78d6";
    ctx.stroke();
  }
  const cropping = state.crop ? " The detector looked at the dashed crop around them." : "";
  els.caption.textContent = !state.rider
    ? "Nobody is followed: everything is blurred. Show the marker to start a follow."
    : !state.rider.found
      ? "Lost the rider: waiting a moment, with everything blurred, before the follow stops."
      : (state.rider.byMarker ? "Following the person holding the marker." : "Following the same person by box overlap; the marker can be too small to read.") +
        ` Everything else is blurred.${cropping}`;
}

function commandRows(command) {
  return [["Yaw", "+ turns right", command.yaw], ["Forward", "+ toward the rider", command.forward], ["Climb", "+ up", command.climb]]
    .flatMap(([label, hint, value]) => {
      const v = Math.max(-1, Math.min(1, value));
      return [
        h("div", {}, label, h("div", { class: "small muted" }, hint)),
        h("div", { class: "track", role: "img", "aria-label": `${label} ${signed(value)}` }, h("div", { class: "zero" }),
          h("div", { class: "bar", style: { left: `${v < 0 ? 50 + v * 50 : 50}%`, width: `${Math.abs(v) * 50}%` } })),
        h("div", { class: "val" }, signed(value)),
      ];
    });
}

function panel(tick, people, markerSeen) {
  const info = modeInfo(tick.mode);
  const e = tick.estimate;
  const where = e
    ? `${fixed(Math.hypot(e.x, e.y), 1)} m away, ${fixed(Math.abs((Math.atan2(e.y, e.x) * 180) / Math.PI), 0)}° ${e.y > 0 ? "left" : "right"}, one sigma ${fixed(Math.sqrt(e.variance), 1)} m.` +
      (tick.margin ? ` Safety margin: the controller treats the rider as ${fixed(tick.margin, 1)} m closer.` : "")
    : "No rider this frame.";
  state.frames += 1;
  clear(els.panel).append(
    h("div", { class: "tick-head" },
      h("span", { class: "chip" }, h("span", { class: "dot", style: { background: info.color } }), `${info.icon} ${info.label}`),
      h("span", { class: "small muted" }, `${people} ${people === 1 ? "person" : "people"} found${state.crop ? " in the crop" : ""}, marker ${markerSeen ? "seen" : "not seen"}, ${fixed(state.detectMs, 0)} ms to detect`)),
    h("div", { class: "panel-block" }, h("h3", {}, "Where the rider is"), h("p", { class: "small" }, where)),
    h("div", { class: "panel-block" }, h("h3", {}, "What the drone would do"), h("div", { class: "cmd" }, commandRows(tick.command))),
    h("p", { class: "small muted" }, "The drone does not move here, so a lost rider walks down the modes: dead reckoning, hold after 5 s, a return-home request after 50 s."),
  );
}

async function loop() {
  const video = state.video;
  while (state.running) {
    const width = video.videoWidth;
    const height = video.videoHeight;
    if (width && height) {
      frame.width = width;
      frame.height = height;
      frame.getContext("2d", { willReadFrequently: true }).drawImage(video, 0, 0, width, height);
      try {
        await work(width, height);
      } catch (error) {
        say(`Something went wrong: ${error.message}`, true);
        stop();
        return;
      }
    }
    await new Promise((resolve) => requestAnimationFrame(resolve));
  }
}

async function start() {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    say("This browser cannot open a camera here. Try a photo instead.", true);
    return;
  }
  els.start.disabled = true;
  try {
    state.stream = await navigator.mediaDevices.getUserMedia({ video: { width: { ideal: 640 }, height: { ideal: 480 } }, audio: false });
  } catch (error) {
    els.start.disabled = false;
    say(`The camera did not start: ${error.message}. Try a photo instead.`, true);
    return;
  }
  const video = (state.video = state.video || document.createElement("video"));
  video.muted = true;
  video.playsInline = true;
  video.srcObject = state.stream;
  await video.play();
  try {
    await setUp(video.videoWidth / video.videoHeight || 4 / 3);
  } catch (error) {
    say(`Could not start the detector: ${error.message}`, true);
    stop();
    return;
  }
  els.stop.disabled = false;
  say("Running in this tab. Hold up the marker to be followed.");
  state.running = true;
  loop();
}

function stop() {
  state.running = false;
  if (state.stream) state.stream.getTracks().forEach((track) => track.stop());
  state.stream = null;
  if (state.video) state.video.srcObject = null;
  els.start.disabled = false;
  els.stop.disabled = true;
}

async function usePhoto(file) {
  stop();
  const url = URL.createObjectURL(file);
  try {
    const img = new Image();
    img.src = url;
    await img.decode();
    const scale = Math.min(1, 1280 / Math.max(img.width, img.height));
    const width = Math.round(img.width * scale);
    const height = Math.round(img.height * scale);
    frame.width = width;
    frame.height = height;
    frame.getContext("2d", { willReadFrequently: true }).drawImage(img, 0, 0, width, height);
    await setUp(width / height);
    state.rider = null;
    await work(width, height);
    say(`Your photo, ${file.name}, worked on in this tab. It was not uploaded.`);
  } catch (error) {
    say(`Could not use ${file.name}: ${error.message}`, true);
  } finally {
    URL.revokeObjectURL(url);
  }
}

function showMarker() {
  if (!window.AR) {
    els.marker.textContent = "The marker library is not in this build of the site.";
    return;
  }
  // The library builds the marker's SVG from its own dictionary; nothing from a visitor goes in.
  const svgText = new AR.Dictionary(MARKER_DICTIONARY).generateSVG(MARKER_ID);
  const svgNode = new DOMParser().parseFromString(svgText, "image/svg+xml").documentElement;
  els.marker.replaceChildren(svgNode);
}

function wire() {
  els.start.addEventListener("click", start);
  els.stop.addEventListener("click", () => {
    stop();
    say("Stopped. The camera is off.");
  });
  els.photo.addEventListener("change", () => {
    const file = els.photo.files && els.photo.files[0];
    if (file) usePhoto(file);
    els.photo.value = "";
  });
  els.fov.addEventListener("change", () => {
    if (state.ready && state.video && state.running) ask(follower, { kind: "setup", hfov: Number(els.fov.value), aspect: state.video.videoWidth / state.video.videoHeight });
  });
  els.print.addEventListener("click", () => {
    document.body.classList.add("printing-marker");
    window.print();
    document.body.classList.remove("printing-marker");
  });
  // Leaving the page, or hiding it, turns the camera off.
  document.addEventListener("visibilitychange", () => {
    if (document.hidden && state.running) {
      stop();
      say("The camera was turned off when the page was hidden.");
    }
  });
  window.addEventListener("pagehide", stop);
}

async function main() {
  initPage();
  wire();
  showMarker();
  try {
    const build = await fetchJSON("data/build.json");
    if (!build.camera) {
      els.start.disabled = true;
      say("This build of the site has no detector. The published site has one.", true);
    }
  } catch (error) {
    // The page still offers the marker without build information.
  }
}

main();
