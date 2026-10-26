// OpenSCAD in the browser and in tools/render_parts.mjs, plus STL measurements.
// Uses OpenSCAD's WebAssembly build (2025.01.19) with the Manifold geometry backend,
// which renders these parts in well under a second instead of 10 to 20 seconds.

// OpenSCAD's -D flag for one parameter: numbers and true/false as they are, text quoted.
export function defineFlag(name, value) {
  const text = typeof value === "string" ? JSON.stringify(value) : String(value);
  return ["-D", `${name}=${text}`];
}

// Render one source to a binary STL. A fresh instance per call: one cannot render twice.
export async function renderStl(createOpenSCAD, source, overrides = {}) {
  const messages = [];
  const openscad = await createOpenSCAD({ print: (s) => messages.push(s), printErr: (s) => messages.push(s) });
  const module = openscad.getInstance();
  module.FS.writeFile("/part.scad", source);
  const args = ["/part.scad", "-o", "/part.stl", "--backend=manifold", "--export-format=binstl"];
  for (const [name, value] of Object.entries(overrides)) args.push(...defineFlag(name, value));
  const code = module.callMain(args);
  const problems = messages.filter((m) => /ERROR|WARNING/.test(m));
  if (code !== 0) throw new Error(problems.join(" ") || `OpenSCAD exited with ${code}`);
  return { bytes: module.FS.readFile("/part.stl"), warnings: problems };
}

// Size, triangle count and solid volume (mm^3) of a binary STL.
export function meshStats(bytes) {
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const triangles = view.getUint32(80, true);
  if (84 + triangles * 50 !== bytes.byteLength) throw new Error("not a binary STL");
  const min = [Infinity, Infinity, Infinity];
  const max = [-Infinity, -Infinity, -Infinity];
  let volume = 0;
  for (let t = 0; t < triangles; t += 1) {
    const p = [];
    for (let k = 0; k < 9; k += 1) p.push(view.getFloat32(84 + t * 50 + 12 + k * 4, true));
    for (let k = 0; k < 9; k += 1) {
      min[k % 3] = Math.min(min[k % 3], p[k]);
      max[k % 3] = Math.max(max[k % 3], p[k]);
    }
    const [ax, ay, az, bx, by, bz, cx, cy, cz] = p;
    volume += (ax * (by * cz - bz * cy) - ay * (bx * cz - bz * cx) + az * (bx * cy - by * cx)) / 6;
  }
  return { triangles, size: [0, 1, 2].map((d) => max[d] - min[d]), volume: Math.abs(volume) };
}
