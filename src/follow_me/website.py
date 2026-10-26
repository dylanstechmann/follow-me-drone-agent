"""Build the project website: the pages in site/ plus data generated from the repo.

  PYTHONPATH=src python3 -m follow_me.website          # build into _site/
  PYTHONPATH=src python3 -m follow_me.website OUT_DIR  # build somewhere else
  python3 -m http.server -d _site 8000                 # preview at http://localhost:8000

The data under data/ is written from the cost model and the replay tool at each
build, and a GitHub Actions workflow builds and publishes the site on every push
to main, so the published site cannot fall behind the repo. Standard library
only. The pages have no backend, analytics or cookies, and a file a visitor
opens in the replay viewer stays in their browser.
"""

import html
import json
import re
import shutil
import subprocess
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from follow_me import bom
from follow_me.replay import trace

ROOT = Path(__file__).resolve().parents[2]
REPO_URL = "https://github.com/dylanstechmann/follow-me-drone-agent"
MARKER = ".follow-me-site"  # marks a directory this builder made, so a rebuild may replace it

# Placeholders in site/index.html, filled from README sections so the two cannot disagree.
README_BLOCKS = {
    "<!-- build:readme-status -->": "Status",
    "<!-- build:readme-built -->": "How this was built",
}


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


def build(out: Path, root: Path = ROOT) -> list[str]:
    """Write the site into out and return the files written, relative to out."""
    out = Path(out)
    _prepare(out)
    shutil.copytree(root / "site", out, dirs_exist_ok=True)
    _write_json(out / "data" / "costs.json", costs_data(root))
    _write_json(out / "data" / "replay-example.json", replay_data(root))
    shutil.copy2(root / "examples" / "replay.example.json", out / "data" / "replay.example.json")
    commit = _commit(root)
    built = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    _write_json(out / "data" / "build.json", {"commit": commit, "built": built})

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
    out = Path(argv[1]) if len(argv) > 1 else ROOT / "_site"
    files = build(out)
    print(f"built {len(files)} files into {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
