# The camera

The camera is one of the council's sources. A person detector finds people in a frame and draws a box around each. `sources.camera_estimate` turns the rider's box into a position relative to the drone. Like the rest of the repo, this was written by AI coding agents at the owner's direction. No camera has flown, and no detector has been measured on a real ride.

## What exists (2026-10-27)

- **A simulated camera.** `sim.Camera` sees the rider in view, misses 10% of the time, and passes its boxes through `camera_estimate`. It is idealised, with no other people and no wrong detections. See [simulation.md](simulation.md).
- **A person detector that runs in the browser and in Node.js.** YOLOX-Nano runs in onnxruntime-web, and `site/assets/detector.js` prepares the frame and decodes the model's output. Its decoding is tested with Node's test runner (`tests/js/detector.test.mjs`), also in CI.
- **A timing tool.** `node tools/detect_bench.mjs [VENDOR_DIR]` times the detector on whatever machine runs it, for example a Raspberry Pi.
- **Not yet:**
  - the website's camera page with the rider marker (iteration 33);
  - a camera on a drone;
  - detection quality measured on rides.

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

## A check on real photos

In a headless browser, the detector ran on three photos from COCO's validation set, the set its published score comes from:
- It found 1, 11 and 4 people, with the boxes where the people were. One photo was a crowded group of 11.
- That confirms the input format: raw BGR values, padded at the top left.

The photos were used only on the agent's machine and are not in the repo.

## Privacy

The detector runs where the frames are: in the visitor's browser on the website, or on the drone later. Frames are never uploaded. The camera page (iteration 33) follows only the person who shows a printed marker, and blurs everyone else before anything is drawn. Do not point it at people who have not agreed. See [privacy-and-rules.md](privacy-and-rules.md).
