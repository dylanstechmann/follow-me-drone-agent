// Runs OpenSCAD in a worker, so the page stays responsive while a part renders.
import { renderStl } from "./stl.js";

let createOpenSCAD = null;

self.addEventListener("message", async (event) => {
  const { id, source, overrides } = event.data;
  try {
    if (!createOpenSCAD) ({ createOpenSCAD } = await import("./vendor/openscad/openscad.js"));
    const started = performance.now();
    const { bytes, warnings } = await renderStl(createOpenSCAD, source, overrides);
    const buffer = bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
    self.postMessage({ id, buffer, warnings, ms: performance.now() - started }, [buffer]);
  } catch (error) {
    self.postMessage({ id, error: String((error && error.message) || error) });
  }
});
