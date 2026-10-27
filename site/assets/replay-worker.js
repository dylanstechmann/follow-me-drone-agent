// Runs the repo's own Python in this browser tab with Pyodide, so a GPX recording is
// read and simulated without leaving the visitor's machine. Nothing is uploaded: the
// worker only fetches Pyodide and the package's .py files from this site.
import { errorText, loadPython } from "./python.js";

let ready = null;

async function start() {
  const pyodide = await loadPython();
  pyodide.runPython("import follow_me.recording");
  return pyodide;
}

self.addEventListener("message", async (event) => {
  const { id, text, second } = event.data;
  try {
    ready = ready || start();
    const pyodide = await ready;
    self.postMessage({ id, status: "running" });
    pyodide.globals.set("gpx_text", text);
    pyodide.globals.set("gpx_second", second || null);
    const trace = pyodide.runPython(
      "import json\nfrom follow_me.recording import run_gpx\ntry:\n    out = json.dumps(run_gpx(gpx_text, second=gpx_second))\nfinally:\n    del gpx_text, gpx_second\nout",
    );
    self.postMessage({ id, trace });
  } catch (error) {
    // A Python error carries its type; anything else means Pyodide did not load, so retry next time.
    if (!(error && error.type)) ready = null;
    self.postMessage({ id, error: errorText(error) });
  }
});
