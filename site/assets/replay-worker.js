// Runs the repo's own Python in this browser tab with Pyodide, so a GPX recording is
// read and simulated without leaving the visitor's machine. Nothing is uploaded: the
// worker only fetches Pyodide and the package's .py files from this site.
let ready = null;

async function start() {
  const { loadPyodide } = await import("./vendor/pyodide/pyodide.mjs");
  const pyodide = await loadPyodide({ indexURL: new URL("./vendor/pyodide/", import.meta.url).href });
  const base = new URL("../py/", import.meta.url);
  const manifest = await (await fetch(new URL("manifest.json", base))).json();
  pyodide.FS.mkdirTree("/home/pyodide/follow_me");
  for (const name of manifest.files) {
    const response = await fetch(new URL(`follow_me/${name}`, base));
    if (!response.ok) throw new Error(`could not load ${name}`);
    pyodide.FS.writeFile(`/home/pyodide/follow_me/${name}`, await response.text());
  }
  pyodide.runPython("import sys\nsys.path.insert(0, '/home/pyodide')\nimport follow_me.recording");
  return pyodide;
}

self.addEventListener("message", async (event) => {
  const { id, text } = event.data;
  try {
    ready = ready || start();
    const pyodide = await ready;
    self.postMessage({ id, status: "running" });
    pyodide.globals.set("gpx_text", text);
    const trace = pyodide.runPython(
      "import json\nfrom follow_me.recording import run_gpx\ntry:\n    out = json.dumps(run_gpx(gpx_text))\nfinally:\n    del gpx_text\nout",
    );
    self.postMessage({ id, trace });
  } catch (error) {
    // A Python error carries its type; anything else means Pyodide did not load, so retry next time.
    if (!(error && error.type)) ready = null;
    const last = String((error && error.message) || error).trim().split("\n").pop();
    self.postMessage({ id, error: last.replace(/^ValueError: /, "") });
  }
});
