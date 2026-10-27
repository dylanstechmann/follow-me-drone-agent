# The camera

The camera is one of the council's sources. A person detector finds people in a frame and draws a box around each. `sources.camera_estimate` turns the rider's box into a position relative to the drone. Like the rest of the repo, this was written by AI coding agents at the owner's direction. No camera has flown, and no detector has been measured on a real ride.

## What exists (2026-10-27)

- **A simulated camera.** `sim.Camera` sees the rider in view, misses 10% of the time, and passes its boxes through `camera_estimate`. It is idealised, with no other people and no wrong detections. See [simulation.md](simulation.md).
- **A person detector that runs in the browser and in Node.js.** YOLOX-Nano runs in onnxruntime-web, and `site/assets/detector.js` prepares the frame and decodes the model's output. Its decoding is tested with Node's test runner (`tests/js/detector.test.mjs`), also in CI.
- **A timing tool.** `node tools/detect_bench.mjs [VENDOR_DIR]` times the detector on whatever machine runs it, for example a Raspberry Pi.
- **The website's camera page** (`site/camera.html`), described below.
- **A measurement of how far it can see**, on 500 COCO photos (below), and a tool to repeat it.
- **Not yet:** a camera on a drone, detection measured on real rides, and cropping around the expected rider.

## The detector

| | |
|---|---|
| Model | YOLOX-Nano, the authors' own ONNX export from release 0.1.1rc0 (3.7 MB) |
| Licence | Apache-2.0 |
| Input | 416 x 416 pixels: the frame scaled to fit, pinned to the top left, the rest filled with grey (114), passed as raw BGR values |
| Published quality | 25.8 mAP on COCO, with 0.91 million parameters and 1.08 GFLOPs (the YOLOX README) |
| Runtime | onnxruntime-web 1.30.0 (MIT), WebAssembly, one thread |

Why this model:
- **The licence.** YOLOv5, YOLOv8 and YOLO11 (Ultralytics) are AGPL-3.0, and YOLOv7 and YOLOv9 are GPL-3.0. Either would bind the project's code to those terms. Yolo-FastestV2 has no licence, so it cannot be used. NanoDet (Apache-2.0) is the other good candidate. These licences are as GitHub reports them, read on 2026-10-27.
- **The size.** It is small enough for a Pi-class computer and a browser tab.

The build downloads the model from the YOLOX release, checked against a sha512 hash taken when it was first downloaded, because GitHub publishes none. Neither the model nor the runtime is kept in git.

## Speed

| Where | Time per frame | Source |
|---|---|---|
| This machine (Intel i9-11980HK), Node.js, one thread | About 70 ms | `tools/detect_bench.mjs`, 2026-10-27 |
| The same machine, headless Chromium | 71 to 119 ms | The check below |
| Raspberry Pi Zero 2 W, ncnn, 4 threads | About 250 ms, about 4 frames a second, **an estimate** | ncnn's published benchmark on that board has NanoDet-m at 166 ms for 0.72 GFLOPs. YOLOX-Nano needs 1.08 GFLOPs, so scaling by compute gives about 250 ms. |

onnxruntime or WebAssembly on the Pi would be slower than ncnn. A few frames a second is enough to correct the GPS fixes, with the Kalman filter carrying the estimate between frames. It needs measuring: run the timing tool on a Pi. On a Pi it measures WebAssembly, which gives an upper bound.

## How far it can see (iteration 35)

`tools/detector_recall.py` ran the detector on a seeded sample of 500 COCO validation photos with people (1,950 people; crowd regions do not count). It matched each detection to the hand-drawn boxes, needing an IoU of 0.5 or more. The share found depends on a person's height in the detector's 416-pixel input. For a 1.75 m person in a 4:3 frame from a 70 degree camera, that height is 520 divided by the distance in meters.

At the camera page's score threshold of 0.35, with 0.33 wrong detections per photo:

| Height in the input | Distance, 70 degree camera | All people | Clearly visible |
|---|---|---|---|
| 128 px and up | Under 4 m | 89% of 497 | 92% of 355 |
| 96 to 128 px | 4 to 5 m | 82% of 165 | 91% of 115 |
| 64 to 96 px | 5 to 8 m | 69% of 270 | 80% of 157 |
| 48 to 64 px | 8 to 11 m | 66% of 163 | 80% of 75 |
| 32 to 48 px | 11 to 16 m | 47% of 231 | 59% of 49 |
| 24 to 32 px | 16 to 22 m | 31% of 131 | Too few |
| 16 to 24 px | 22 to 32 m | 12% of 183 | Too few |
| 12 to 16 px | 32 to 43 m | 5% of 118 | Too few |
| Under 12 px | Over 43 m | 1% of 192 | Too few |

"Clearly visible" means 10 or more of COCO's 17 body points marked, a proxy for a person not hidden behind something.

Limits of this measurement:
- COCO photos are not a drone's view of a skater from behind.
- Small people in COCO are often partly hidden, so the all-people figures are cautious for a rider in clear view.
- A score threshold of 0.25 finds a few points more, with 0.51 wrong detections per photo. A threshold of 0.5 finds fewer, with 0.15.

What it means:
- The simulated camera's first numbers (seen 90% of the time out to 30 m) were far too optimistic. The simulation now uses the all-people column ([simulation.md](simulation.md)).
- At phone accuracy, the safety margin keeps the drone 15 to 40 m back, where the rider is seldom found, so the estimate stays uncertain. That is a trap.
- Running the detector on a crop around the rider breaks the trap, measured below.
- A narrower lens did worse in the simulation. That result is confounded: the controller sets its distance from how much of the frame the rider fills, so a narrower lens also moves the follow distance out.

To repeat the measurement, see the steps at the top of `tools/detector_recall.py`. The photos stay on the machine that runs it.

### Cropping around the rider (iteration 37)

The same 500 photos were run once per drawn person, on a square crop around them: three times their height, at least 160 pixels, inside the photo. Each crop was enlarged to the detector's input. No camera detail is added, which is what a 640 x 480 webcam can do.

At a score of 0.35:

| Height in the whole-photo input | Whole photo | Crop |
|---|---|---|
| 128 px and up | 89% | 89% |
| 96 to 128 px | 84% | 84% |
| 64 to 96 px | 68% | 79% |
| 48 to 64 px | 64% | 73% |
| 32 to 48 px | 46% | 70% |
| 24 to 32 px | 31% | 66% |
| 16 to 24 px | 12% | 57% |
| 12 to 16 px | 5% | 47% |
| 8 to 12 px | 1% | 53% |
| Under 8 px | 1% | 22% |

The whole-photo column differs from the table above by up to 2 points, because the tool now draws both modes through one function.

How to read it:
- **Small people gain most.** At the detector's coarsest grid, 8 pixels, a small person covers one or two cells, and enlarging gives it more to see.
- **It is an upper bound.** The crops were centred on the drawn box. On the drone, a crop would centre on the council's estimate. The simulation applies the gain only when the rider falls inside such a crop.
- **More pixels would help more.** A camera with spare pixels, cropping from a 1080p or larger frame, would add real detail as well.

In the simulation (iteration 38), cropping took a 4 m/s follow at phone accuracy from 36.8 m behind with 4% tracking to 15.7 m with 65% tracking. See [simulation.md](simulation.md).

## A check on real photos

In a headless browser, the detector ran on three photos from COCO's validation set, the set its published score comes from:
- It found 1, 11 and 4 people, with the boxes where the people were. One photo was a crowded group of 11.
- That confirms the input format: raw BGR values, padded at the top left.

The photos were used only on the agent's machine and are not in the repo.

## The camera page

On the website, the visitor starts their camera or chooses a photo:
1. A worker runs the detector on each frame (`site/assets/camera-worker.js`).
2. js-aruco2 (MIT) looks for the printed marker: ArUco marker 0 from the `ARUCO_MIP_36h12` dictionary, which the page draws for printing.
3. The rider is the person whose box holds the marker's centre (`site/assets/rider.js`). If the marker is hidden, the same person is kept for one second by box overlap, then let go. Without the marker, nobody is followed.
4. The picture is drawn blurred, by shrinking and enlarging it, and only the rider's box is drawn sharp on top. A person the detector missed stays blurred.
5. The rider's box, as shares of the frame, goes to the repo's own Python, run in the tab by Pyodide. `follow_me.camera_view.CameraView` keeps one council between frames, so a hidden marker walks down the modes in seconds, as on the drone. The page shows the estimate, the safety margin, the mode and the command.

The first start downloads about 15 MB from the site: the runtime, the model and Python. The field of view defaults to 70 degrees across, a guess for laptop cameras that the page lets the visitor change. The distance assumes a 1.75 m person, so it is rough.

Checked in a headless browser on 2026-10-27, with a COCO photo of 11 people and the marker pasted onto one of them:
- **Photo mode:** it found all 11, followed only the marked person, and blurred the rest. A bystander's region fell from 12.5 to 1.9 on a sharpness measure, and the rider's stayed at 14.5 of 15.1.
- **Live camera mode:** Chromium's fake camera played the same image. It ran at 73 ms a frame, followed the marked person, and stopped cleanly.
- **Layout:** no errors or sideways scrolling, at desktop width in the light theme and phone width in the dark theme.

## Privacy

The detector runs where the frames are: in the visitor's browser on the website, or on the drone later. Frames are never uploaded. The camera page (iteration 33) follows only the person who shows a printed marker, and blurs everyone else before anything is drawn. Do not point it at people who have not agreed. See [privacy-and-rules.md](privacy-and-rules.md).
