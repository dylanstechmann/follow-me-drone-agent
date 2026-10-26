"""Keep generated blocks in the docs equal to what the data files produce.

A generated block sits between two marker lines:

  <!-- generated:NAME:start -->
  ...generated text...
  <!-- generated:NAME:end -->

Edit the data under bom/, then run the sync to rewrite every block:

  PYTHONPATH=src python3 -m follow_me.docs_sync           # rewrite stale blocks
  PYTHONPATH=src python3 -m follow_me.docs_sync --check   # exit 1 if any block is stale

The test suite runs the check, so a doc cannot fall behind its data.
"""

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from follow_me import bom
from follow_me.group_order import group_order_markdown, load_group_order

ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Block:
    file: str  # path relative to the repo root
    name: str
    render: Callable[[], str]


def _pattern(name: str) -> re.Pattern:
    tag = re.escape(name)
    return re.compile(
        rf"(<!-- generated:{tag}:start -->\n)(.*?)(\n<!-- generated:{tag}:end -->)", re.S
    )


def render_into(text: str, name: str, content: str) -> str:
    """Return text with the named block's body replaced by content."""
    match = _pattern(name).search(text)
    if match is None:
        raise ValueError(f"missing generated markers for block {name!r}")
    return text[: match.start(2)] + content.rstrip("\n") + text[match.end(2) :]


def _data():
    materials = bom.load_materials()
    catalog = bom.load_catalog(bom.DEFAULT_CATALOG, materials)
    budget, raw = bom.load_passes()
    passes = bom.resolve(catalog, raw)
    return materials, catalog, budget, passes


def default_blocks() -> list[Block]:
    def catalog() -> str:
        materials, cat, _, _ = _data()
        return bom.catalog_markdown(cat, materials)

    def audit() -> str:
        materials, cat, _, _ = _data()
        return bom.audit_markdown(cat, materials)

    def passes() -> str:
        materials, cat, budget, ps = _data()
        return bom.passes_markdown(cat, ps, budget, materials)

    def drones() -> str:
        materials, cat, _, ps = _data()
        return bom.drones_markdown(cat, ps, materials)

    def group_order() -> str:
        return group_order_markdown(load_group_order())

    return [
        Block("docs/parts-catalog.md", "catalog", catalog),
        Block("docs/price-audit.md", "audit", audit),
        Block("docs/cost-reduction.md", "passes", passes),
        Block("docs/cost-reduction.md", "drones", drones),
        Block("docs/group-order.md", "group_order", group_order),
    ]


def sync(root: Path, blocks: list[Block], write: bool) -> list[tuple[str, str]]:
    """Return the (file, block) pairs that were stale. With write, fix them."""
    stale: list[tuple[str, str]] = []
    texts: dict[str, str] = {}
    for block in blocks:
        path = root / block.file
        text = texts.get(block.file)
        if text is None:
            text = path.read_text(encoding="utf-8")
        new = render_into(text, block.name, block.render())
        if new != text:
            stale.append((block.file, block.name))
        texts[block.file] = new
    if write:
        for file, text in texts.items():
            (root / file).write_text(text, encoding="utf-8")
    return stale


def main(argv: list[str]) -> int:
    check = "--check" in argv
    stale = sync(ROOT, default_blocks(), write=not check)
    if check:
        for file, name in stale:
            print(f"stale: {file} block {name}")
        return 1 if stale else 0
    for file, name in stale:
        print(f"updated: {file} block {name}")
    if not stale:
        print("all generated blocks are up to date")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
