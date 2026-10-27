"""Build the project website: the pages in site/ plus data generated from the repo.

  PYTHONPATH=src python3 -m follow_me.website          # build into _site/
  PYTHONPATH=src python3 -m follow_me.website OUT_DIR  # build somewhere else
  PYTHONPATH=src python3 -m follow_me.website --vendor --render-parts   # what CI runs
  python3 -m http.server -d _site 8000                 # preview at http://localhost:8000

The data under data/ is written from the cost model, the replay tool and the
parts list at each build, and a GitHub Actions workflow builds and publishes the
site on every push to main, so the published site cannot fall behind the repo.
Standard library only. The pages have no backend, analytics or cookies, and a
file a visitor opens in the replay viewer stays in their browser.

--vendor downloads the browser libraries from the npm registry, pinned to exact
versions and checked against the registry's published hashes, so no library code is
kept in git and the site makes no requests to other servers: three.js and OpenSCAD's
WebAssembly build for the parts page, and Pyodide, which runs the repo's own Python
in the replay page so a visitor's recording never leaves their browser.
--render-parts then renders each part's default STL with Node.js and that same
OpenSCAD build.
"""

import base64
import hashlib
import html
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from follow_me import bom, parts
from follow_me.council import Council
from follow_me.replay import trace
from follow_me.sim import EXAMPLE_NOTE, Camera, example_track, trace_track

ROOT = Path(__file__).resolve().parents[2]
REPO_URL = "https://github.com/dylanstechmann/follow-me-drone-agent"
MARKER = ".follow-me-site"  # marks a directory this builder made, so a rebuild may replace it

# Placeholders in site/index.html, filled from README sections so the two cannot disagree.
README_BLOCKS = {
    "<!-- build:readme-status -->": "Status",
    "<!-- build:readme-built -->": "How this was built",
}

# Browser libraries and the detector's model, pinned by version and by a sha512 hash:
# the registry's for npm tarballs, of which only the listed files are copied, and our
# own for a single file from a GitHub release. Everything lands under assets/vendor/.
VENDOR = {
    "three": {
        "version": "0.186.1",
        "license": "MIT",
        "url": "https://registry.npmjs.org/three/-/three-0.186.1.tgz",
        "integrity": "sha512-blFeqb49wRCSGUGj7gtpfnSGHy2lwDk94RhUmS1c/hTby70kvChbWpkJ4Pm1390LqzzvTmzgXKHPEafJwCb8jA==",
        "files": {
            "package/build/three.module.js": "three/three.module.js",
            "package/build/three.core.js": "three/three.core.js",
            "package/examples/jsm/controls/OrbitControls.js": "three/addons/controls/OrbitControls.js",
            "package/examples/jsm/loaders/STLLoader.js": "three/addons/loaders/STLLoader.js",
            "package/LICENSE": "three/LICENSE",
        },
    },
    "openscad": {
        "version": "openscad-wasm-prebuilt 1.2.0 (OpenSCAD 2025.01.19)",
        "license": "GPL-2.0-or-later",
        "url": "https://registry.npmjs.org/openscad-wasm-prebuilt/-/openscad-wasm-prebuilt-1.2.0.tgz",
        "integrity": "sha512-JfXJlopHVHvsYiVYUKYDXkg8yOkABm8zclo8zPrSRBeeICR+fitesO6NRwBdAzSdbtOYh6Scmuz/XLyhllbzYA==",
        "source": "https://github.com/lorenzowritescode/openscad-wasm",
        "files": {
            "package/dist/openscad.js": "openscad/openscad.js",
            "package/COPYING": "openscad/COPYING",
        },
    },
    "pyodide": {
        "version": "314.0.7 (Python 3.14)",
        "license": "MPL-2.0; the Python standard library inside it is under the PSF licence",
        "url": "https://registry.npmjs.org/pyodide/-/pyodide-314.0.7.tgz",
        "integrity": "sha512-0YvXxEhfEdpLfb/XkM2BFAeMROq0iMUX2bzzH9pOttyMcWkwq+HbE5uyuGD82LN7y2q+SNvi/6V5JEsOlD2R1A==",
        "source": "https://github.com/pyodide/pyodide",
        "files": {
            "package/pyodide.mjs": "pyodide/pyodide.mjs",
            "package/pyodide.asm.mjs": "pyodide/pyodide.asm.mjs",
            "package/pyodide.asm.wasm": "pyodide/pyodide.asm.wasm",
            "package/python_stdlib.zip": "pyodide/python_stdlib.zip",
            "package/pyodide-lock.json": "pyodide/pyodide-lock.json",
        },
    },
    "onnxruntime-web": {
        "version": "1.30.0",
        "license": "MIT",
        "url": "https://registry.npmjs.org/onnxruntime-web/-/onnxruntime-web-1.30.0.tgz",
        "integrity": "sha512-q0y+JrrtukXSzsBWEMccVfqX25LRmosXHF+CaRJmg8pZClzcV7svNc4rKY3jL02Vb7QmRMDs1SigqR4CXAfKYQ==",
        "source": "https://github.com/microsoft/onnxruntime",
        "files": {
            "package/dist/ort.wasm.min.mjs": "onnxruntime/ort.wasm.min.mjs",
            "package/dist/ort-wasm-simd-threaded.mjs": "onnxruntime/ort-wasm-simd-threaded.mjs",
            "package/dist/ort-wasm-simd-threaded.wasm": "onnxruntime/ort-wasm-simd-threaded.wasm",
        },
    },
    "yolox-nano": {
        "version": "YOLOX release 0.1.1rc0, yolox_nano.onnx (trained on COCO)",
        "license": "Apache-2.0",
        # GitHub publishes no hash for release files; this one was computed when the
        # file was first downloaded, on 2026-10-26.
        "url": "https://github.com/Megvii-BaseDetection/YOLOX/releases/download/0.1.1rc0/yolox_nano.onnx",
        "integrity": "sha512-9p7CLs2vOmfVyQ6OY1mdigX52NusRiEUopIWL7sUJm4xurLQIl3UGU9dyJ8rSrCe1mIj+ZOVEAbPK9ZTT4mKxg==",
        "source": "https://github.com/Megvii-BaseDetection/YOLOX",
        "file": "yolox/yolox_nano.onnx",
    },
}
OPENSCAD_JS = "assets/vendor/openscad/openscad.js"
PYODIDE_JS = "assets/vendor/pyodide/pyodide.mjs"

# The modules the replay page runs in the browser to simulate a recording. A test
# checks that they import nothing else from the package.
PY_MODULES = (
    "__init__", "companion", "context", "controller", "council", "fusion", "geo",
    "mode", "motion", "recording", "replay", "sim", "sources",
)


def costs_data(root: Path = ROOT) -> dict:
    """Every pass with its totals, shares, minimum-order cash and drone-count costs, plus the price audit."""
    materials = bom.load_materials(root / "bom" / "materials.json")
    catalog = bom.load_catalog(root / "bom" / "catalog.json", materials)
    budget, raw = bom.load_passes(root / "bom" / "passes.json")
    passes = bom.resolve(catalog, raw)
    out = []
    for p in passes:
        t = bom.totals(catalog, p.items, materials)
        fresh, sourced, _ = bom.date_summary(bom.price_rows(catalog, materials, p.items))
        out.append({
            "id": p.id,
            "title": p.title,
            "note": p.note,
            "based_on": p.based_on,
            "items": list(p.items),
            "added": list(p.added),
            "removed": list(p.removed),
            "core": [t.core_low, t.core_high],
            "optional": [t.optional_low, t.optional_high],
            "cash_min_orders": list(bom.cash_outlay(catalog, p.items, materials)),
            "made_share": round(bom.made_share(t), 4),
            "designed_share": round(bom.designed_share(catalog, p.items, materials), 4),
            "budget_status": bom.budget_status(t, budget),
            "placeholders": t.placeholders,
            "unpriced": t.unpriced,
            "fresh": fresh,
            "sourced": sourced,
            # A pass with motors or props is a flying drone; the bench kits have none.
            "flying": any(catalog[i].category == "propulsion" for i in p.items),
            "per_drone": [list(bom.per_drone_cost(catalog, p.items, materials, n)) for n in bom.DRONE_COUNTS],
            "cash": [list(bom.cash_outlay(catalog, p.items, materials, n)) for n in bom.DRONE_COUNTS],
        })
    items = {}
    for item in catalog.values():
        items[item.id] = {
            "name": item.name,
            "category": item.category,
            "path": item.path,
            "qty": item.qty,
            "unit": list(bom.unit_cost(item, materials)),
            "status": item.status,
            "optional": item.optional,
            "checked": item.checked or ("from materials" if item.make else ""),
        }
    rows = bom.price_rows(catalog, materials)
    fresh, sourced, placeholders = bom.date_summary(rows)
    single, none = bom.dependency(catalog, passes[-1].items)
    return {
        "as_of": bom.AS_OF.isoformat(),
        "budget_usd": budget,
        "drone_counts": list(bom.DRONE_COUNTS),
        "passes": out,
        "items": items,
        "prices": [asdict(r) for r in rows],
        "price_summary": {"fresh": fresh, "sourced": sourced, "placeholders": placeholders, "inputs": len(rows)},
        "dependency": {"pass": passes[-1].id, "single": single, "none": none},
    }


def replay_data(root: Path = ROOT) -> dict:
    log = json.loads((root / "examples" / "replay.example.json").read_text(encoding="utf-8"))
    return trace(log)


def sim_example_data(variant: str = "now") -> dict:
    """The made-up ride, followed by the simulated drone: with the controller as it is
    ("now"), with a simulated camera as well ("camera"), or with the controller as it
    was before feed-forward and the safety margin ("before")."""
    if variant == "now":
        return trace_track(example_track(), note=EXAMPLE_NOTE)
    if variant == "camera":
        note = EXAMPLE_NOTE + (" A simulated camera also sees the rider when in view and misses 10% of the"
                               " time; there are no other people. Its error model is a placeholder.")
        return trace_track(example_track(), note=note, camera=Camera())
    if variant == "before":
        note = EXAMPLE_NOTE + " Followed by the controller as it was before feed-forward and the safety margin, for comparison."
        return trace_track(example_track(), council=Council(feed_forward=False, margin_sigmas=0.0), note=note)
    raise ValueError(f"unknown example {variant!r}")


def _catalog_grams(item: bom.Item | None) -> dict | None:
    """Grams of filament a printed catalog item is costed with, from its make inputs."""
    if item is None or not item.make:
        return None
    for key, kg in item.make["inputs"].items():
        if key in ("pla_per_kg", "petg_per_kg"):
            return {"id": item.id, "name": item.name, "grams": round(kg * 1000, 1), "material": key.split("_")[0].upper()}
    return None


def parts_data(root: Path = ROOT, out: Path | None = None) -> dict:
    """The print cards and parameters, and which STL files and libraries the build has."""
    materials = bom.load_materials(root / "bom" / "materials.json")
    catalog = bom.load_catalog(root / "bom" / "catalog.json", materials)
    rows = []
    for part in parts.load_parts(root / "cad", catalog):
        row = {k: v for k, v in asdict(part).items() if k != "params"}
        row["params"] = [asdict(p) for p in part.params]
        row["scad"] = f"parts/{part.file}"
        row["stl"] = f"parts/{part.id}.stl" if out and (out / "parts" / f"{part.id}.stl").is_file() else None
        row["catalog"] = _catalog_grams(catalog.get(part.catalog_item)) if part.catalog_item else None
        rows.append(row)
    return {
        "parts": rows,
        "density": parts.DENSITY,
        "viewer": bool(out and (out / "assets/vendor/three/three.module.js").is_file()),
        "openscad": bool(out and (out / OPENSCAD_JS).is_file()),
    }


_LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
_BOLD = re.compile(r"\*\*(.+?)\*\*")
_CODE = re.compile(r"`([^`]+)`")


def _inline(text: str) -> str:
    """Escape text, then turn markdown code, bold and links into HTML. Repo paths link to GitHub."""
    out = html.escape(text, quote=False)
    out = _CODE.sub(lambda m: f"<code>{m.group(1)}</code>", out)
    out = _BOLD.sub(r"<strong>\1</strong>", out)

    def link(m: re.Match) -> str:
        url = html.unescape(m.group(2))
        if not re.match(r"https?://", url):
            url = f"{REPO_URL}/blob/main/{url}"
        return f'<a href="{html.escape(url)}">{m.group(1)}</a>'

    return _LINK.sub(link, out)


def markdown_section(markdown: str, heading: str) -> str:
    """One '## heading' section of a markdown file as HTML: paragraphs and bullet lists only."""
    match = re.search(rf"^## {re.escape(heading)}\n(.*?)(?=^## |\Z)", markdown, re.S | re.M)
    if match is None:
        raise ValueError(f"no '## {heading}' section")
    parts = []
    for block in re.split(r"\n\s*\n", match.group(1).strip()):
        lines = block.splitlines()
        if all(line.startswith("- ") for line in lines):
            parts.append("<ul>" + "".join(f"<li>{_inline(line[2:])}</li>" for line in lines) + "</ul>")
        else:
            parts.append(f"<p>{_inline(' '.join(lines))}</p>")
    return "\n".join(parts)


def _commit(root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def check_integrity(data: bytes, integrity: str) -> None:
    algorithm, _, expected = integrity.partition("-")
    if algorithm != "sha512":
        raise ValueError(f"unsupported integrity {integrity!r}")
    actual = base64.b64encode(hashlib.sha512(data).digest()).decode("ascii")
    if actual != expected:
        raise ValueError("downloaded package does not match its pinned sha512 hash")


def _download(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=120) as response:
        return response.read()


def default_cache() -> Path:
    return Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "follow-me-site"


def fetch_vendor(dest: Path, cache: Path, vendor: dict = VENDOR, download=_download) -> list[str]:
    """Copy the pinned library files into dest. Tarballs are cached and checked on every use."""
    written = []
    for spec in vendor.values():
        cached = cache / Path(urlparse(spec["url"]).path).name
        data = cached.read_bytes() if cached.is_file() else download(spec["url"])
        check_integrity(data, spec["integrity"])
        if not cached.is_file():
            cache.mkdir(parents=True, exist_ok=True)
            cached.write_bytes(data)
        if "file" in spec:  # a single file, copied as it is
            path = dest / spec["file"]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            written.append(spec["file"])
            continue
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
            for member, target in spec["files"].items():
                handle = tar.extractfile(member)  # read named members only; nothing is unpacked
                if handle is None:
                    raise ValueError(f"{member} is not a file in {spec['url']}")
                path = dest / target
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(handle.read())
                written.append(target)
    return written


def render_parts(out: Path, root: Path = ROOT) -> str:
    """Render every part's default STL into out/parts with Node.js and the fetched OpenSCAD."""
    node = shutil.which("node")
    openscad = out / OPENSCAD_JS
    if node is None or not openscad.is_file():
        raise RuntimeError("rendering parts needs Node.js on the PATH and a build made with --vendor")
    result = subprocess.run(
        [node, str(root / "tools" / "render_parts.mjs"), str(openscad), str(root / "cad"), str(out / "parts")],
        capture_output=True, text=True, timeout=600,
    )
    if result.returncode != 0:
        raise RuntimeError(f"rendering parts failed:\n{result.stdout}{result.stderr}")
    return result.stdout


def _prepare(out: Path) -> None:
    if out.exists():
        if (out / MARKER).exists():
            shutil.rmtree(out)
        elif any(out.iterdir()):
            raise ValueError(f"{out} is not empty and was not made by this builder; not replacing it")
    out.mkdir(parents=True, exist_ok=True)


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")


def build(
    out: Path,
    root: Path = ROOT,
    vendor: bool = False,
    render: bool = False,
    cache: Path | None = None,
) -> list[str]:
    """Write the site into out and return the files written, relative to out."""
    out = Path(out)
    _prepare(out)
    shutil.copytree(root / "site", out, dirs_exist_ok=True)
    (out / "parts").mkdir(exist_ok=True)
    for source in sorted((root / "cad").glob("*.scad")):
        shutil.copy2(source, out / "parts" / source.name)
    if vendor:
        fetch_vendor(out / "assets" / "vendor", cache or default_cache())
    if render:
        print(render_parts(out, root), end="")
    _write_json(out / "data" / "parts.json", parts_data(root, out))
    _write_json(out / "data" / "costs.json", costs_data(root))
    _write_json(out / "data" / "replay-example.json", replay_data(root))
    _write_json(out / "data" / "sim-example.json", sim_example_data())
    _write_json(out / "data" / "sim-example-camera.json", sim_example_data("camera"))
    _write_json(out / "data" / "sim-example-before.json", sim_example_data("before"))
    shutil.copy2(root / "examples" / "replay.example.json", out / "data" / "replay.example.json")
    package = out / "py" / "follow_me"
    package.mkdir(parents=True)
    for name in PY_MODULES:
        shutil.copy2(root / "src" / "follow_me" / f"{name}.py", package / f"{name}.py")
    _write_json(out / "py" / "manifest.json", {"files": [f"{name}.py" for name in PY_MODULES]})
    commit = _commit(root)
    built = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    _write_json(out / "data" / "build.json", {
        "commit": commit, "built": built, "python": (out / PYODIDE_JS).is_file(),
    })

    index = out / "index.html"
    text = index.read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    for placeholder, heading in README_BLOCKS.items():
        if placeholder not in text:
            raise ValueError(f"site/index.html is missing {placeholder}")
        text = text.replace(placeholder, markdown_section(readme, heading))
    index.write_text(text, encoding="utf-8")

    (out / ".nojekyll").write_text("", encoding="utf-8")  # serve files as they are
    (out / MARKER).write_text("built by follow_me.website\n", encoding="utf-8")
    return sorted(str(p.relative_to(out)) for p in out.rglob("*") if p.is_file())


def main(argv: list[str]) -> int:
    flags = {a for a in argv[1:] if a.startswith("--")}
    unknown = flags - {"--vendor", "--render-parts"}
    paths = [a for a in argv[1:] if not a.startswith("--")]
    if unknown or len(paths) > 1:
        print("usage: python -m follow_me.website [OUT_DIR] [--vendor] [--render-parts]", file=sys.stderr)
        return 2
    out = Path(paths[0]) if paths else ROOT / "_site"
    render = "--render-parts" in flags
    files = build(out, vendor="--vendor" in flags or render, render=render)
    print(f"built {len(files)} files into {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
