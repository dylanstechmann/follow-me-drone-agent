// Time the person detector on this machine, for example a Raspberry Pi:
//   node tools/detect_bench.mjs [VENDOR_DIR]
// VENDOR_DIR is a website build's assets/vendor (built with --vendor); the default is
// _site/assets/vendor. It runs YOLOX-Nano at 416 x 416 on a grey frame with
// onnxruntime-web's WebAssembly backend, on one thread (this build cannot use threads
// in Node.js), and prints the median time per frame. A native
// runtime (onnxruntime for ARM, or ncnn) would be faster than WebAssembly on a Pi, so
// treat the result as an upper bound there.
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

import { INPUT, PAD, detectPeople, fitScale } from "../site/assets/detector.js";

const vendor = resolve(process.argv[2] || "_site/assets/vendor");
const ort = await import(pathToFileURL(`${vendor}/onnxruntime/ort.wasm.min.mjs`).href);
ort.env.wasm.wasmPaths = pathToFileURL(`${vendor}/onnxruntime/`).href;
ort.env.wasm.numThreads = 1;
const session = await ort.InferenceSession.create(readFileSync(`${vendor}/yolox/yolox_nano.onnx`), {
  executionProviders: ["wasm"],
});

const rgba = new Uint8ClampedArray(INPUT * INPUT * 4).fill(PAD);
const scale = fitScale(640, 480);
await detectPeople(ort, session, rgba, scale); // the first run sets things up
const times = [];
for (let i = 0; i < 20; i++) {
  const start = performance.now();
  await detectPeople(ort, session, rgba, scale);
  times.push(performance.now() - start);
}
times.sort((a, b) => a - b);
const median = times[times.length >> 1];
console.log(`YOLOX-Nano ${INPUT} x ${INPUT}, one thread: median ${median.toFixed(1)} ms per frame, about ${(1000 / median).toFixed(1)} frames a second`);
