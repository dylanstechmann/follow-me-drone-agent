"""Parts catalog and cost passes.

Items live in bom/catalog.json. Each pass in bom/passes.json is a delta on the
pass before it, so every reduction is recorded with its reason. Totals keep core
parts apart from optional ones, and count placeholders and unpriced items, so a
guessed number is never mistaken for a quote.

Usage:
  python -m follow_me.bom            # cost report for every pass
  python -m follow_me.bom --markdown # parts catalog as a markdown table
"""

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

STATUSES = ("snapshot", "official", "estimate", "placeholder", "owned", "unpriced")

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CATALOG = ROOT / "bom" / "catalog.json"
DEFAULT_PASSES = ROOT / "bom" / "passes.json"


@dataclass(frozen=True)
class Item:
    id: str
    name: str
    category: str
    qty: int
    low: float  # USD per unit
    high: float  # USD per unit
    status: str
    source: str = ""  # URLs separated by "; "
    note: str = ""
    optional: bool = False


@dataclass(frozen=True)
class Pass:
    id: str
    title: str
    note: str
    based_on: str | None
    items: tuple[str, ...]  # resolved item ids
    added: tuple[str, ...]
    removed: tuple[str, ...]


@dataclass(frozen=True)
class Totals:
    core_low: float
    core_high: float
    optional_low: float
    optional_high: float
    placeholders: int
    unpriced: int


@dataclass(frozen=True)
class Tier:
    name: str
    tags: int
    low: float
    high: float


def _validate(item: Item) -> None:
    if item.status not in STATUSES:
        raise ValueError(f"{item.id}: unknown status {item.status!r}")
    if item.qty < 1:
        raise ValueError(f"{item.id}: qty must be at least 1")
    if item.low < 0 or item.high < item.low:
        raise ValueError(f"{item.id}: need 0 <= low <= high")
    if item.status == "unpriced" and (item.low or item.high):
        raise ValueError(f"{item.id}: unpriced items must have zero prices")


def load_catalog(path: Path | str = DEFAULT_CATALOG) -> dict[str, Item]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    items: dict[str, Item] = {}
    for raw in data["items"]:
        item = Item(**raw)  # unknown keys raise TypeError, which is what we want
        _validate(item)
        if item.id in items:
            raise ValueError(f"duplicate item id {item.id}")
        items[item.id] = item
    return items


def load_passes(path: Path | str = DEFAULT_PASSES) -> tuple[float, list[dict]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return float(data["budget_usd"]), data["passes"]


def resolve(catalog: dict[str, Item], raw_passes: list[dict]) -> list[Pass]:
    """Turn the pass deltas into full item lists, checking every change."""
    resolved: dict[str, tuple[str, ...]] = {}
    out: list[Pass] = []
    for index, raw in enumerate(raw_passes):
        pid = raw["id"]
        if pid in resolved:
            raise ValueError(f"duplicate pass {pid}")
        base = raw.get("based_on")
        if index == 0:
            if base is not None:
                raise ValueError(f"{pid}: the first pass must have no base")
            current: list[str] = []
        else:
            if base is None:
                raise ValueError(f"{pid}: only the first pass may have no base")
            if base not in resolved:
                raise ValueError(f"{pid}: based_on {base} must be an earlier pass")
            current = list(resolved[base])

        removed = tuple(raw.get("remove", []))
        added = tuple(raw.get("add", []))
        for rid in removed:
            if rid not in current:
                raise ValueError(f"{pid}: cannot remove {rid}, it is not in the base")
            current.remove(rid)
        for aid in added:
            if aid not in catalog:
                raise ValueError(f"{pid}: unknown item {aid}")
            if aid in current:
                raise ValueError(f"{pid}: {aid} is already present")
            current.append(aid)

        resolved[pid] = tuple(current)
        out.append(
            Pass(pid, raw["title"], raw.get("note", ""), base, tuple(current), added, removed)
        )
    return out


def totals(catalog: dict[str, Item], ids: tuple[str, ...] | list[str]) -> Totals:
    core_low = core_high = opt_low = opt_high = 0.0
    placeholders = unpriced = 0
    for iid in ids:
        item = catalog[iid]
        lo, hi = item.low * item.qty, item.high * item.qty
        if item.optional:
            opt_low += lo
            opt_high += hi
        else:
            core_low += lo
            core_high += hi
        if item.status == "placeholder":
            placeholders += 1
        if item.status == "unpriced":
            unpriced += 1
    return Totals(
        round(core_low, 2),
        round(core_high, 2),
        round(opt_low, 2),
        round(opt_high, 2),
        placeholders,
        unpriced,
    )


def companion_tiers(catalog: dict[str, Item], ids: tuple[str, ...] | list[str]) -> list[Tier]:
    """Cost of the companion setups, using the tag cost in the given pass."""
    tags = [catalog[i] for i in ids if catalog[i].category == "companion_tag"]
    tag_low = round(sum(t.low * t.qty for t in tags), 2)
    tag_high = round(sum(t.high * t.qty for t in tags), 2)
    return [
        Tier("phone only", 0, 0.0, 0.0),
        Tier("phone + 1 tag", 1, tag_low, tag_high),
        Tier("phone + 2 tags", 2, round(2 * tag_low, 2), round(2 * tag_high, 2)),
    ]


def _budget_status(t: Totals, budget: float) -> str:
    if t.core_high <= budget:
        return "fits budget at low and high prices"
    if t.core_low <= budget:
        return "fits budget at low prices only"
    return "over budget"


def report(catalog: dict[str, Item], passes: list[Pass], budget: float) -> str:
    lines = []
    by_id: dict[str, Totals] = {}
    for p in passes:
        t = totals(catalog, p.items)
        by_id[p.id] = t
        lines.append(f"{p.id}  {p.title}")
        lines.append(
            f"    core ${t.core_low:,.2f} to ${t.core_high:,.2f}"
            f"   optional ${t.optional_low:,.2f} to ${t.optional_high:,.2f}"
            f"   {_budget_status(t, budget)}"
        )
        change = ""
        if p.based_on is not None:
            base = by_id[p.based_on]  # change is measured against the base pass
            change = (
                f"   change vs {p.based_on}: {t.core_low - base.core_low:+,.2f}"
                f" to {t.core_high - base.core_high:+,.2f}"
            )
        lines.append(f"    placeholders: {t.placeholders}   unpriced: {t.unpriced}{change}")
    return "\n".join(lines)


def _links(source: str) -> str:
    links = []
    for url in filter(None, (s.strip() for s in source.split(";"))):
        host = urlparse(url).netloc.removeprefix("www.")
        links.append(f"[{host}]({url})")
    return " · ".join(links) if links else "none"


def catalog_markdown(catalog: dict[str, Item]) -> str:
    rows = [
        "| Item | Category | Qty | USD each (low to high) | Status | Sources | Note |",
        "|---|---|---|---|---|---|---|",
    ]
    for item in catalog.values():
        price = (
            f"{item.low:,.2f} to {item.high:,.2f}"
            if item.high != item.low
            else f"{item.low:,.2f}"
        )
        name = item.name + (" (optional)" if item.optional else "")
        rows.append(
            f"| {name} | {item.category} | {item.qty} | {price} | {item.status} | "
            f"{_links(item.source)} | {item.note} |"
        )
    return "\n".join(rows)


def main(argv: list[str]) -> int:
    catalog = load_catalog()
    if "--markdown" in argv:
        print(catalog_markdown(catalog))
        return 0
    budget, raw = load_passes()
    passes = resolve(catalog, raw)
    print(report(catalog, passes, budget))
    print()
    print(f"Companion tiers (tag cost from {passes[0].id}):")
    for tier in companion_tiers(catalog, passes[0].items):
        print(f"    {tier.name:<16} ${tier.low:,.2f} to ${tier.high:,.2f}")
    print("    phone + wearable IMUs: unpriced (see bom/catalog.json, imu_wearable)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
