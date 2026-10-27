"""The website builds from the repo data, matches the model, and keeps the repo's rules."""

import base64
import hashlib
import io
import json
import re
import tarfile
from html.parser import HTMLParser
from pathlib import Path

import pytest

from follow_me import bom
from follow_me.replay import trace
from follow_me.council import Council
from follow_me.sim import EXAMPLE_NOTE, Camera, example_track, trace_track
from follow_me.website import (
    MARKER, PY_MODULES, VENDOR, build, check_integrity, costs_data, fetch_vendor, main, markdown_section,
    replay_data, sim_example_data,
)

REPO = Path(__file__).resolve().parents[1]
PAGES = ("index.html", "replay.html", "camera.html", "costs.html", "parts.html")
# Stricter than the group-order check: a package@version string is not an email.
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)*\.[A-Za-z]{2,}\b")
PHONE = re.compile(r"\(?\b\d{3}\)?[-. ]\d{3}[-. ]\d{4}\b")


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    out = tmp_path_factory.mktemp("site") / "out"
    build(out)
    return out


class _Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if name in ("href", "src") and value:
                self.links.append(value)


def test_site_builds_every_page_and_its_data(site):
    for name in (*PAGES, "assets/style.css", "assets/common.js", "data/costs.json",
                 "data/replay-example.json", "data/replay.example.json", "data/sim-example.json",
                 "data/build.json", "assets/replay-worker.js", "py/manifest.json", ".nojekyll"):
        assert (site / name).is_file(), name
    index = (site / "index.html").read_text(encoding="utf-8")
    assert "<!-- build:" not in index
    assert "Built and tested" in index  # the README status section was filled in


def test_cost_data_matches_the_cost_model():
    data = costs_data()
    materials = bom.load_materials()
    catalog = bom.load_catalog(bom.DEFAULT_CATALOG, materials)
    _, raw = bom.load_passes()
    passes = {p.id: p for p in bom.resolve(catalog, raw)}
    assert data["drone_counts"] == list(bom.DRONE_COUNTS)
    assert [p["id"] for p in data["passes"]] == list(passes)
    for row in data["passes"]:
        t = bom.totals(catalog, passes[row["id"]].items, materials)
        assert row["core"] == [t.core_low, t.core_high]
        assert row["cash_min_orders"] == list(bom.cash_outlay(catalog, passes[row["id"]].items, materials))
        assert row["per_drone"][0] == row["cash"][0]  # one drone: the cash is the cost per drone
    flying = {p["id"]: p["flying"] for p in data["passes"]}
    assert flying["pass3_bench_first"] is False and flying["pass5_made_tag"] is False
    assert flying["pass0_retail_autopilot"] is True and flying["pass10_factory_and_lab"] is True


def test_replay_data_is_the_trace_of_the_example_log():
    log = json.loads((REPO / "examples" / "replay.example.json").read_text(encoding="utf-8"))
    assert replay_data() == trace(log)


def test_sim_example_is_the_made_up_ride_followed_by_the_simulated_drone(site):
    assert sim_example_data() == trace_track(example_track(), note=EXAMPLE_NOTE)
    data = json.loads((site / "data" / "sim-example.json").read_text(encoding="utf-8"))
    assert data["kind"] == "simulation" and data["note"] == EXAMPLE_NOTE
    assert len(data["ticks"]) == 291
    modes = {t["mode"] for t in data["ticks"]}
    assert modes == {"tracking", "degraded", "dead_reckoning", "hold"}  # the example shows each step
    before = json.loads((site / "data" / "sim-example-before.json").read_text(encoding="utf-8"))
    assert before == trace_track(example_track(), council=Council(feed_forward=False, margin_sigmas=0.0), note=before["note"])
    assert data["summary"]["median_distance_m"] < before["summary"]["median_distance_m"]
    assert "motion" in data["ticks"][-1]
    camera = json.loads((site / "data" / "sim-example-camera.json").read_text(encoding="utf-8"))
    assert camera == trace_track(example_track(), note=camera["note"], camera=Camera())
    assert camera["summary"]["camera_share"] > 0.3  # the measured recall at these distances
    assert camera["summary"]["median_distance_m"] < data["summary"]["median_distance_m"]


def test_browser_python_is_the_repo_code_and_imports_only_itself(site):
    manifest = json.loads((site / "py" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["files"] == [f"{name}.py" for name in PY_MODULES]
    for name in PY_MODULES:
        source = (REPO / "src" / "follow_me" / f"{name}.py").read_text(encoding="utf-8")
        assert (site / "py" / "follow_me" / f"{name}.py").read_text(encoding="utf-8") == source
        for module in re.findall(r"^\s*(?:from|import) follow_me\.(\w+)", source, re.M):
            assert module in PY_MODULES, f"{name}.py needs follow_me.{module} in the browser"
        for module in re.findall(r"^from follow_me import ([\w, ]+)$", source, re.M):
            for part in module.split(","):
                assert part.strip() in PY_MODULES, f"{name}.py needs follow_me.{part.strip()} in the browser"


def test_build_says_whether_the_browser_has_python(site):
    build_info = json.loads((site / "data" / "build.json").read_text(encoding="utf-8"))
    assert build_info["python"] is False  # Pyodide comes only with --vendor
    assert build_info["camera"] is False  # and so do the detector and the marker library


def test_every_local_link_and_import_resolves(site):
    for page in PAGES:
        parser = _Links()
        parser.feed((site / page).read_text(encoding="utf-8"))
        for link in parser.links:
            if re.match(r"[a-z]+:", link) or link.startswith("#") or link.startswith("assets/vendor/"):
                continue  # vendor files exist only in builds made with --vendor
            target = site / link.split("#")[0].split("?")[0]
            assert target.is_file(), f"{page} links to missing {link}"
    for script in (site / "assets").glob("*.js"):
        for name in re.findall(r'from "\./([\w.-]+)"', script.read_text(encoding="utf-8")):
            assert (site / "assets" / name).is_file(), f"{script.name} imports missing {name}"


def test_site_has_no_email_or_phone_like_text(site):
    for path in site.rglob("*"):
        if path.suffix in (".html", ".js", ".json", ".css"):
            text = path.read_text(encoding="utf-8")
            assert not EMAIL.search(text), f"email-like text in {path.name}"
            assert not PHONE.search(text), f"phone-like text in {path.name}"


def _keys(value):
    if isinstance(value, dict):
        for key, inner in value.items():
            yield key
            yield from _keys(inner)
    elif isinstance(value, list):
        for inner in value:
            yield from _keys(inner)


def test_site_ships_no_place_data(site):
    names = {p.name for p in site.rglob("*")}
    assert not any(n.startswith("places") or n.endswith(".local.json") for n in names)
    for path in (site / "data").glob("*.json"):
        keys = set(_keys(json.loads(path.read_text(encoding="utf-8"))))
        assert not keys & {"lat", "lon", "latitude", "longitude"}, f"coordinates in {path.name}"


def test_pages_carry_the_honest_framing(site):
    for page in PAGES:
        text = (site / page).read_text(encoding="utf-8")
        assert "hobby and learning project" in text.lower(), page
        assert "written by AI coding agents" in text, page
        assert "No review of the code by the owner is recorded" in text, page
    assert "Nothing has flown" in (site / "index.html").read_text(encoding="utf-8")


def test_builder_replaces_only_a_directory_it_made(tmp_path):
    other = tmp_path / "other"
    other.mkdir()
    (other / "keep.txt").write_text("not a site", encoding="utf-8")
    with pytest.raises(ValueError, match="not replacing"):
        build(other)
    assert (other / "keep.txt").exists()

    out = tmp_path / "site"
    build(out)
    (out / "stale.txt").write_text("from an old build", encoding="utf-8")
    assert (out / MARKER).exists()
    build(out)
    assert not (out / "stale.txt").exists()


def test_markdown_section_converts_links_bold_code_and_lists():
    md = "# T\n\n## Status\n\n- **Built:** see [the plan](docs/plan.md) & `code`\n- [site](https://example.org)\n\nA paragraph\nover two lines.\n\n## Next\n\nignored\n"
    out = markdown_section(md, "Status")
    assert out.startswith("<ul><li><strong>Built:</strong>")
    assert 'href="https://github.com/dylanstechmann/follow-me-drone-agent/blob/main/docs/plan.md"' in out
    assert "&amp; <code>code</code>" in out
    assert 'href="https://example.org"' in out
    assert "<p>A paragraph over two lines.</p>" in out
    assert "ignored" not in out
    with pytest.raises(ValueError):
        markdown_section(md, "Missing")


def test_parts_data_lists_each_part_with_its_source(site):
    data = json.loads((site / "data" / "parts.json").read_text(encoding="utf-8"))
    ids = [p["id"] for p in data["parts"]]
    assert ids == ["flex_test_bars", "fit_gauge", "thrust_stand", "tag_enclosure"]
    for part in data["parts"]:
        assert (site / part["scad"]).is_file()
        assert part["stl"] is None  # rendering needs --render-parts
        assert part["params"] and part["status"] == "unprinted"
    stand = next(p for p in data["parts"] if p["id"] == "thrust_stand")
    assert stand["catalog"] == {"id": "thrust_stand_make", "name": stand["catalog"]["name"], "grams": 80.0, "material": "PLA"}
    assert data["viewer"] is False and data["openscad"] is False


def _fake_package(files):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for name, text in files.items():
            body = text.encode("utf-8")
            info = tarfile.TarInfo(name)
            info.size = len(body)
            tar.addfile(info, io.BytesIO(body))
    data = buffer.getvalue()
    return data, "sha512-" + base64.b64encode(hashlib.sha512(data).digest()).decode("ascii")


def test_fetch_vendor_checks_the_hash_and_copies_only_listed_files(tmp_path):
    data, integrity = _fake_package({"package/lib.js": "export const x = 1;", "package/../../evil.js": "no"})
    spec = {"lib": {"url": "https://registry.example/lib-1.0.0.tgz", "integrity": integrity,
                    "files": {"package/lib.js": "lib/lib.js"}}}
    calls = []

    def download(url):
        calls.append(url)
        return data

    written = fetch_vendor(tmp_path / "out", tmp_path / "cache", spec, download)
    assert written == ["lib/lib.js"]
    assert (tmp_path / "out" / "lib" / "lib.js").read_text(encoding="utf-8") == "export const x = 1;"
    assert not any(p.name == "evil.js" for p in tmp_path.rglob("*"))
    fetch_vendor(tmp_path / "out2", tmp_path / "cache", spec, download)
    assert len(calls) == 1  # the second build used the cached, re-checked tarball

    bad = {"lib": {**spec["lib"], "integrity": "sha512-" + base64.b64encode(b"x" * 64).decode("ascii")}}
    with pytest.raises(ValueError, match="pinned"):
        fetch_vendor(tmp_path / "out3", tmp_path / "cache", bad, download)


def test_check_integrity_needs_sha512():
    with pytest.raises(ValueError, match="unsupported"):
        check_integrity(b"data", "sha1-abc")


def test_vendor_pins_exact_versions_and_hashes():
    for spec in VENDOR.values():
        npm = re.search(r"^https://registry\.npmjs\.org/.+-\d+\.\d+\.\d+\.tgz$", spec["url"])
        release = re.search(r"^https://github\.com/[\w.-]+/[\w.-]+/releases/download/[\w.-]+/[\w.-]+$", spec["url"])
        assert npm or release, spec["url"]
        assert ("files" in spec) == bool(npm) and ("file" in spec) == bool(release)
        assert spec["integrity"].startswith("sha512-") and len(spec["integrity"]) > 80
        assert spec["license"]


def test_fetch_vendor_copies_a_single_pinned_file(tmp_path):
    data = b"model bytes"
    integrity = "sha512-" + base64.b64encode(hashlib.sha512(data).digest()).decode("ascii")
    spec = {"m": {"url": "https://github.com/o/r/releases/download/1.0/m.onnx", "integrity": integrity, "file": "m/m.onnx"}}
    assert fetch_vendor(tmp_path / "out", tmp_path / "cache", spec, lambda url: data) == ["m/m.onnx"]
    assert (tmp_path / "out" / "m" / "m.onnx").read_bytes() == data
    bad = {"m": {**spec["m"], "integrity": "sha512-" + base64.b64encode(b"y" * 64).decode("ascii")}}
    with pytest.raises(ValueError, match="pinned"):
        fetch_vendor(tmp_path / "out2", tmp_path / "cache2", bad, lambda url: data)


def test_main_rejects_unknown_flags(capsys):
    assert main(["website", "--deploy"]) == 2
    assert "usage" in capsys.readouterr().err

