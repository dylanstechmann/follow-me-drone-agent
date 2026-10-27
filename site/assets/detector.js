// Person detection with YOLOX-Nano (Apache-2.0), run by onnxruntime-web in the browser
// or in Node.js. The page letterboxes a frame onto a 416 x 416 canvas; these functions
// turn its pixels into the model's input, decode the model's 3,549 candidate boxes,
// keep the people and remove overlaps. They are plain functions, so Node's test
// runner checks them without a model (tests/js/detector.test.mjs).

export const INPUT = 416;
export const STRIDES = [8, 16, 32];
export const CLASSES = 80; // COCO
export const PERSON = 0;
export const PAD = 114; // the grey YOLOX pads with

// The scale that fits a width x height frame inside the square input, keeping its shape.
export function fitScale(width, height, size = INPUT) {
  return Math.min(size / width, size / height);
}

// The candidate rows the model gives for an input size: one per grid cell per stride.
export function rowCount(size = INPUT, strides = STRIDES) {
  return strides.reduce((n, s) => n + (size / s) ** 2, 0);
}

// RGBA pixels of the letterboxed square to the model's input: BGR planes, values 0 to 255.
// The 0.1.1 YOLOX exports take raw pixels, with no normalization.
export function toInput(rgba, size = INPUT) {
  const plane = size * size;
  const out = new Float32Array(3 * plane);
  for (let i = 0; i < plane; i++) {
    out[i] = rgba[4 * i + 2];
    out[plane + i] = rgba[4 * i + 1];
    out[2 * plane + i] = rgba[4 * i];
  }
  return out;
}

// Raw rows (x and y offsets, log width and height, objectness, class scores) to boxes in
// input pixels, keeping one class above a score threshold. Score = objectness x class score.
export function decode(rows, { size = INPUT, strides = STRIDES, classes = CLASSES, cls = PERSON, threshold = 0.35 } = {}) {
  const width = 5 + classes;
  const boxes = [];
  let row = 0;
  for (const stride of strides) {
    const n = size / stride;
    for (let gy = 0; gy < n; gy++) {
      for (let gx = 0; gx < n; gx++, row++) {
        const o = row * width;
        const score = rows[o + 4] * rows[o + 5 + cls];
        if (score < threshold) continue;
        const cx = (rows[o] + gx) * stride;
        const cy = (rows[o + 1] + gy) * stride;
        const w = Math.exp(rows[o + 2]) * stride;
        const h = Math.exp(rows[o + 3]) * stride;
        boxes.push({ x: cx - w / 2, y: cy - h / 2, w, h, score });
      }
    }
  }
  return boxes;
}

export function iou(a, b) {
  const x1 = Math.max(a.x, b.x);
  const y1 = Math.max(a.y, b.y);
  const x2 = Math.min(a.x + a.w, b.x + b.w);
  const y2 = Math.min(a.y + a.h, b.y + b.h);
  const inter = Math.max(0, x2 - x1) * Math.max(0, y2 - y1);
  const union = a.w * a.h + b.w * b.h - inter;
  return union > 0 ? inter / union : 0;
}

// Keep the best-scoring box of each overlapping group.
export function nms(boxes, threshold = 0.45) {
  const kept = [];
  for (const box of [...boxes].sort((a, b) => b.score - a.score)) {
    if (kept.every((k) => iou(k, box) < threshold)) kept.push(box);
  }
  return kept;
}

// Boxes in input pixels back to the frame's pixels.
export function unscale(boxes, scale) {
  return boxes.map((b) => ({ ...b, x: b.x / scale, y: b.y / scale, w: b.w / scale, h: b.h / scale }));
}

// Run the model on a letterboxed square's RGBA pixels; returns people in frame pixels.
export async function detectPeople(ort, session, rgba, scale, options = {}) {
  const size = options.size || INPUT;
  const input = new ort.Tensor("float32", toInput(rgba, size), [1, 3, size, size]);
  const output = await session.run({ [session.inputNames[0]]: input });
  const rows = output[session.outputNames[0]].data;
  return unscale(nms(decode(rows, options), options.iou), scale);
}
