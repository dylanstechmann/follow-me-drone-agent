// Runs the repo's follow logic on the rider's box from the camera page, in this tab,
// with Pyodide. follow_me.camera_view keeps one council between frames, so a lost
// rider is timed as on the drone. Only the box's position and size arrive here.
import { errorText, loadPython } from "./python.js";

let ready = null;

async function start() {
  const pyodide = await loadPython();
  pyodide.runPython("import json\nfrom follow_me.camera_view import CameraView\nview = CameraView()");
  return pyodide;
}

self.addEventListener("message", async (event) => {
  const { id, kind } = event.data;
  try {
    ready = ready || start();
    const pyodide = await ready;
    if (kind === "setup") {
      pyodide.globals.set("setup_json", JSON.stringify({ hfov: event.data.hfov, aspect: event.data.aspect }));
      pyodide.runPython("s = json.loads(setup_json)\nview = CameraView(s['hfov'], s['aspect'])");
      self.postMessage({ id, ok: true });
      return;
    }
    pyodide.globals.set("frame_json", JSON.stringify({ now: event.data.now, box: event.data.box }));
    const tick = pyodide.runPython("f = json.loads(frame_json)\njson.dumps(view.step(f['now'], f['box']))");
    self.postMessage({ id, tick });
  } catch (error) {
    if (!(error && error.type)) ready = null;
    self.postMessage({ id, error: errorText(error) });
  }
});
