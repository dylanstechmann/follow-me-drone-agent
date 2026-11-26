// Custom sandbox settings are evaluated by the repo's Python in this tab. The worker
// fetches only the site's pinned Pyodide and package modules; nothing is uploaded.
import { errorText, loadPython } from "./python.js";

let ready = null;

async function start() {
  const pyodide = await loadPython();
  pyodide.runPython("import follow_me.scenario");
  return pyodide;
}

self.addEventListener("message", async (event) => {
  const { id, config } = event.data;
  try {
    ready = ready || start();
    self.postMessage({ id, status: "loading" });
    const pyodide = await ready;
    self.postMessage({ id, status: "running" });
    pyodide.globals.set("scenario_json", JSON.stringify(config));
    const trace = pyodide.runPython(
      "import json\nfrom follow_me.scenario import sandbox_config, trace_scenario\ntry:\n    options = json.loads(scenario_json)\n    result = trace_scenario(sandbox_config(**options))\n    out = json.dumps(result, allow_nan=False, separators=(',', ':'))\nfinally:\n    del scenario_json\nout",
    );
    self.postMessage({ id, trace });
  } catch (error) {
    // Python exceptions can be retried with the loaded runtime; import/load failures cannot.
    if (!(error && error.type)) ready = null;
    self.postMessage({ id, error: errorText(error) });
  }
});
