// Finds people in the camera page's frames with YOLOX-Nano in onnxruntime-web, in this
// tab. Each frame arrives as the letterboxed square's pixels, is used once, and is not
// kept. Only this site is contacted, for the runtime and the model.
import { detectPeople } from "./detector.js";

let ready = null;

async function start() {
  const ort = await import("./vendor/onnxruntime/ort.wasm.min.mjs");
  ort.env.wasm.wasmPaths = new URL("./vendor/onnxruntime/", import.meta.url).href;
  ort.env.wasm.numThreads = 1; // GitHub Pages cannot enable the cross-origin isolation threads need
  const response = await fetch(new URL("./vendor/yolox/yolox_nano.onnx", import.meta.url));
  if (!response.ok) throw new Error("could not load the detector's model");
  const session = await ort.InferenceSession.create(await response.arrayBuffer(), { executionProviders: ["wasm"] });
  return { ort, session };
}

self.addEventListener("message", async (event) => {
  const { id, pixels, scale } = event.data;
  try {
    ready = ready || start();
    const { ort, session } = await ready;
    if (!pixels) {
      self.postMessage({ id, ready: true });
      return;
    }
    const started = performance.now();
    const people = await detectPeople(ort, session, new Uint8ClampedArray(pixels), scale);
    self.postMessage({ id, people, ms: performance.now() - started });
  } catch (error) {
    ready = null;
    self.postMessage({ id, error: String((error && error.message) || error) });
  }
});
