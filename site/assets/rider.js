// Which person is the rider. Only someone who shows the printed marker starts a follow.
// After that, the same person is followed by box overlap from frame to frame, even when
// the marker is too small to read. The follow stops if the person is lost for HOLD_MS,
// or if two people overlap the rider's last box: it never guesses between people.
// Plain functions, so Node's test runner checks them (tests/js/rider.test.mjs).
import { iou } from "./detector.js";

export const MARKER_DICTIONARY = "ARUCO_MIP_36h12";
export const MARKER_ID = 0; // the marker the camera page offers to print
export const HOLD_MS = 1000; // how long a lost rider is waited for before the follow stops

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

// The rider this frame, or null when nobody should be followed:
//   {box, seenAt, byMarker, found}
// `found` is false while a lost rider is waited for: `box` is then their last box, which
// must not be drawn sharp or sent to the follow logic, since someone else may stand there.
export function pickRider(people, markers, previous, now, { markerId = MARKER_ID, holdMs = HOLD_MS, minOverlap = 0.3 } = {}) {
  const marker = markers.find((m) => m.id === markerId);
  if (marker) {
    const box = holder(people, center(marker.corners));
    if (box) return { box, seenAt: now, byMarker: true, found: true };
  }
  if (!previous) return null;
  const overlapping = people.filter((box) => iou(box, previous.box) >= minOverlap);
  if (overlapping.length > 1) return null; // two people where the rider was: do not guess
  if (overlapping.length === 1) return { box: overlapping[0], seenAt: now, byMarker: false, found: true };
  if (now - previous.seenAt <= holdMs) return { ...previous, byMarker: false, found: false };
  return null;
}

// The rider's box as shares of the frame, the way the follow logic takes a detection.
export function shareBox(box, width, height) {
  return { cx: (box.x + box.w / 2) / width, cy: (box.y + box.h / 2) / height, height: box.h / height };
}

// A square crop around the rider's box: CROP_TIMES their height, at least CROP_MIN pixels,
// inside the frame. Enlarged to the detector's input, it lets a small rider be found.
export const CROP_TIMES = 3;
export const CROP_MIN = 160;
export function cropAround(box, width, height) {
  const side = Math.min(Math.max(CROP_TIMES * box.h, CROP_MIN), width, height);
  const x = Math.min(Math.max(box.x + box.w / 2 - side / 2, 0), width - side);
  const y = Math.min(Math.max(box.y + box.h / 2 - side / 2, 0), height - side);
  return { x, y, side };
}
