// Which person is the rider: the one holding the printed marker. Nobody else is
// followed. After the marker is hidden, the same person is kept for a moment by box
// overlap, then let go. Plain functions, so Node's test runner checks them
// (tests/js/rider.test.mjs).
import { iou } from "./detector.js";

export const MARKER_DICTIONARY = "ARUCO_MIP_36h12";
export const MARKER_ID = 0; // the marker the camera page offers to print
export const HOLD_MS = 1000; // how long a hidden marker's holder is still followed

export function center(corners) {
  const n = corners.length;
  return {
    x: corners.reduce((sum, c) => sum + c.x, 0) / n,
    y: corners.reduce((sum, c) => sum + c.y, 0) / n,
  };
}

export function contains(box, p) {
  return p.x >= box.x && p.x <= box.x + box.w && p.y >= box.y && p.y <= box.y + box.h;
}

// The person holding the marker: the smallest person box around the marker's centre,
// so a person in front is chosen over a larger box behind them.
export function holder(people, point) {
  let best = null;
  for (const box of people) {
    if (contains(box, point) && (!best || box.w * box.h < best.w * best.h)) best = box;
  }
  return best;
}

// The rider this frame: {box, seenAt, byMarker}, or null when nobody should be followed.
export function pickRider(people, markers, previous, now, { markerId = MARKER_ID, holdMs = HOLD_MS, minOverlap = 0.3 } = {}) {
  const marker = markers.find((m) => m.id === markerId);
  if (marker) {
    const box = holder(people, center(marker.corners));
    if (box) return { box, seenAt: now, byMarker: true };
  }
  if (previous && now - previous.seenAt <= holdMs) {
    let best = null;
    let bestOverlap = minOverlap;
    for (const box of people) {
      const overlap = iou(box, previous.box);
      if (overlap >= bestOverlap) {
        best = box;
        bestOverlap = overlap;
      }
    }
    if (best) return { box: best, seenAt: previous.seenAt, byMarker: false };
  }
  return null;
}

// The rider's box as shares of the frame, the way the follow logic takes a detection.
export function shareBox(box, width, height) {
  return { cx: (box.x + box.w / 2) / width, cy: (box.y + box.h / 2) / height, height: box.h / height };
}
