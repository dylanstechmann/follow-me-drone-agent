// Loads Pyodide from this site, and the package's modules into it, for the workers that
// run the repo's own Python in the browser (replay-worker.js, follow-worker.js). Only
// this site is contacted.
export async function loadPython() {
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
  pyodide.runPython("import sys\nsys.path.insert(0, '/home/pyodide')");
  return pyodide;
}

// The last line of an error, without Python's exception name for the common ValueError.
export function errorText(error) {
  const last = String((error && error.message) || error).trim().split("\n").pop();
  return last.replace(/^ValueError: /, "");
}
