// Render each part in cad/parts.json at its default parameters to a binary STL,
// with the same OpenSCAD WebAssembly build the website runs in the browser.
//
//   node tools/render_parts.mjs OPENSCAD_JS CAD_DIR OUT_DIR
//
// The website builder runs this with --render-parts after fetching OpenSCAD.
// It prints one JSON line per part and exits 1 if any part fails.
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { join, resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { meshStats, renderStl } from "../site/assets/stl.js";

const [, , openscadJs, cadDir, outDir] = process.argv;
if (!openscadJs || !cadDir || !outDir) {
  console.error("usage: node tools/render_parts.mjs OPENSCAD_JS CAD_DIR OUT_DIR");
  process.exit(2);
}
const { createOpenSCAD } = await import(pathToFileURL(resolve(openscadJs)).href);
const manifest = JSON.parse(readFileSync(join(cadDir, "parts.json"), "utf8"));
mkdirSync(outDir, { recursive: true });

let failed = 0;
for (const part of manifest.parts) {
  const started = Date.now();
  try {
    const { bytes, warnings } = await renderStl(createOpenSCAD, readFileSync(join(cadDir, part.file), "utf8"));
    writeFileSync(join(outDir, `${part.id}.stl`), bytes);
    const stats = meshStats(bytes);
    console.log(JSON.stringify({
      id: part.id,
      triangles: stats.triangles,
      size_mm: stats.size.map((s) => Math.round(s * 100) / 100),
      volume_cm3: Math.round(stats.volume / 10) / 100,
      ms: Date.now() - started,
      warnings,
    }));
    if (warnings.length) failed += 1;
  } catch (error) {
    failed += 1;
    console.log(JSON.stringify({ id: part.id, error: String((error && error.message) || error) }));
  }
}
process.exit(failed ? 1 : 0);
