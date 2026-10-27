"""Measure how often the person detector finds people, by their height on screen.

COCO's validation photos come with a box drawn around every person. The detector runs
in a browser on a seeded sample of them, and this script matches its detections to
the drawn boxes. Recall by box height says how far away a camera can find a person,
because a person's height on screen shrinks with distance.

  1. Build the site with the libraries:   PYTHONPATH=src python3 -m follow_me.website --vendor
  2. Download a sample into the build:    python3 tools/detector_recall.py prepare _site/recall-check
     (COCO's annotations, 241 MB, are cached under ~/.cache/follow-me-site; the photos
     go into the build folder, which git ignores and the next build replaces)
  3. Serve it and open the page:          python3 -m http.server -d _site 8000
                                          http://localhost:8000/recall-check/index.html
     When it finishes, save predictions.json into _site/recall-check.
  4. Read the result:                     python3 tools/detector_recall.py analyse _site/recall-check

The photos are COCO's, under their owners' Flickr licences, and stay on the machine
that runs this: never commit or publish them. COCO's annotations are CC BY 4.0.
"""

import json
import math
import random
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

ANNOTATIONS_URL = "http://images.cocodataset.org/annotations/annotations_trainval2017.zip"
INPUT = 416
BINS = [0, 8, 12, 16, 24, 32, 48, 64, 96, 128, 10_000]
CLEAR = 10  # of COCO's 17 body points marked: a proxy for a clearly visible person
THRESHOLDS = (0.25, 0.35, 0.5)  # 0.35 is what the camera page uses


def cache_dir() -> Path:
    return Path.home() / ".cache" / "follow-me-site"


def prepare(out: Path, count: int = 500, seed: int = 2026) -> None:
    archive = cache_dir() / "annotations_trainval2017.zip"
    if not archive.is_file():
        archive.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(ANNOTATIONS_URL, timeout=600) as r, archive.open("wb") as f:
            shutil.copyfileobj(r, f)
    data = json.loads(zipfile.ZipFile(archive).read("annotations/person_keypoints_val2017.json"))
    images = {im["id"]: im for im in data["images"]}
    by_image: dict[int, list] = {}
    for a in data["annotations"]:
        by_image.setdefault(a["image_id"], []).append(a)
    candidates = sorted(i for i, anns in by_image.items() if any(not a["iscrowd"] for a in anns))
    random.Random(seed).shuffle(candidates)
    (out / "images").mkdir(parents=True, exist_ok=True)
    manifest = []
    for image_id in candidates[:count]:
        im = images[image_id]
        target = out / "images" / im["file_name"]
        if not target.exists():
            with urllib.request.urlopen(im["coco_url"], timeout=60) as r:
                target.write_bytes(r.read())
        anns = by_image[image_id]
        manifest.append({
            "file": f"images/{im['file_name']}", "width": im["width"], "height": im["height"],
            "people": [[*a["bbox"], a["num_keypoints"]] for a in anns if not a["iscrowd"]],
            "crowd": [a["bbox"] for a in anns if a["iscrowd"]],
        })
    (out / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    shutil.copy2(Path(__file__).with_name("detector_recall.html"), out / "index.html")
    people = sum(len(m["people"]) for m in manifest)
    print(f"{len(manifest)} photos with {people} people in {out}; open index.html from there")


def iou(a, b) -> float:
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[0] + a[2], b[0] + b[2]), min(a[1] + a[3], b[1] + b[3])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    return inter / (a[2] * a[3] + b[2] * b[3] - inter) if inter else 0.0


def inside_share(a, b) -> float:
    """The share of box a that lies inside box b."""
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[0] + a[2], b[0] + b[2]), min(a[1] + a[3], b[1] + b[3])
    return max(0.0, x2 - x1) * max(0.0, y2 - y1) / (a[2] * a[3])


def recall_by_height(manifest: list, predictions: dict, threshold: float) -> tuple[dict, float]:
    """Found and total people per height bin, for all people and clearly visible ones,
    and wrong detections per photo. A detection matches the best unmatched drawn box
    it overlaps by an IoU of 0.5 or more; one inside a crowd region is not counted."""
    cells: dict[tuple[str, int], list[int]] = {}
    wrong = 0
    for item in manifest:
        scale = INPUT / max(item["width"], item["height"])
        people = item["people"]
        matched = [False] * len(people)
        for p in sorted((b for b in predictions[item["file"]] if b[4] >= threshold), key=lambda b: -b[4]):
            best, best_iou = None, 0.5
            for i, g in enumerate(people):
                if not matched[i] and iou(p, g) >= best_iou:
                    best, best_iou = i, iou(p, g)
            if best is not None:
                matched[best] = True
            elif not any(inside_share(p, c) >= 0.5 for c in item["crowd"]):
                wrong += 1
        for g, m in zip(people, matched):
            h = g[3] * scale
            b = next(i for i in range(len(BINS) - 1) if BINS[i] <= h < BINS[i + 1])
            for group in ("all", "clear") if g[4] >= CLEAR else ("all",):
                cell = cells.setdefault((group, b), [0, 0])
                cell[0] += int(m)
                cell[1] += 1
    return cells, wrong / len(manifest)


def analyse(folder: Path, hfov_deg: float = 70.0) -> None:
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    run = json.loads((folder / "predictions.json").read_text(encoding="utf-8"))
    predictions = {p["file"]: p["boxes"] for p in run["predictions"]}
    vfov = 2 * math.atan(math.tan(math.radians(hfov_deg) / 2) * 3 / 4)
    k = INPUT * 3 / 4 * 1.75 / (2 * math.tan(vfov / 2))  # input pixels x meters, for a 4:3 frame
    print(f"{len(manifest)} photos, median {run.get('median_ms', 0):.0f} ms a photo. A 1.75 m person in a "
          f"4:3 frame from a {hfov_deg:g} degree camera is {k:.0f} / distance pixels tall in the input.")
    for threshold in THRESHOLDS:
        cells, wrong = recall_by_height(manifest, predictions, threshold)
        print(f"\nscore >= {threshold}: {wrong:.2f} wrong detections per photo")
        print(f"{'height px':>11} {'distance m':>11} {'all people':>14} {'clearly visible':>16}")
        for b in range(len(BINS) - 1):
            lo, hi = BINS[b], BINS[b + 1]
            span = f"under {k / lo:.0f}" if hi > 1000 else (f"over {k / hi:.0f}" if lo == 0 else f"{k / hi:.0f}-{k / lo:.0f}")
            shown = [f"{c[0] / c[1]:.0%} of {c[1]}" if c[1] else "-"
                     for c in (cells.get(("all", b), [0, 0]), cells.get(("clear", b), [0, 0]))]
            print(f"{lo:>5}-{hi if hi < 1000 else '':<5} {span:>11} {shown[0]:>14} {shown[1]:>16}")


def main(argv: list[str]) -> int:
    if len(argv) == 3 and argv[1] == "prepare":
        prepare(Path(argv[2]))
        return 0
    if len(argv) == 3 and argv[1] == "analyse":
        analyse(Path(argv[2]))
        return 0
    print("usage: python3 tools/detector_recall.py prepare|analyse FOLDER", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
