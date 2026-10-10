"""Parts catalog, raw materials, cost passes and price dates.

Four files drive the numbers:
  bom/materials.json  raw inputs and components: filament, board area, wire, chips, cells
  bom/catalog.json    every item and how it is obtained (its path)
  bom/passes.json     build passes as deltas on the pass before, each with its reason and risk
  price dates         every price carries a checked date, judged against AS_OF

A made item (path "make") has no price of its own. Its cost is the sum of its
material inputs. Every number keeps its status and date, so a guess or an old
price is never mistaken for a current quote.

Usage:
  python -m follow_me.bom                    # cost report for every pass
  python -m follow_me.bom --passes-markdown  # pass summary as a markdown table
  python -m follow_me.bom --markdown         # parts catalog as a markdown table
  python -m follow_me.bom --audit            # price-date audit as a markdown table
"""

import json
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

STATUSES = ("snapshot", "official", "estimate", "placeholder", "owned", "purchased", "unpriced")
PATHS = ("buy_retail", "buy_bulk", "buy_used", "buy_service", "make", "owned", "salvage")
# Paths where the owner makes the part, or reclaims it. These count toward in-house share.
MADE_PATHS = ("make", "salvage")
SOURCED_STATUSES = ("snapshot", "official")

AS_OF = date(2026, 10, 10)
MAX_PRICE_AGE_DAYS = 365
_DATE_RE = re.compile(r"^\d{4}(-\d{2}(-\d{2})?)?$")

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MATERIALS = ROOT / "bom" / "materials.json"
DEFAULT_CATALOG = ROOT / "bom" / "catalog.json"
DEFAULT_PASSES = ROOT / "bom" / "passes.json"


@dataclass(frozen=True)
class Material:
    key: str
    unit: str
    low: float
    high: float
    status: str
    checked: str = ""  # YYYY, YYYY-MM or YYYY-MM-DD; empty when the source shows no date
    source: str = ""
    note: str = ""


@dataclass(frozen=True)
class Item:
    id: str
    name: str
    category: str
    qty: int
    low: float  # USD per unit for bought items; made items are computed
    high: float
    status: str
    path: str
    source: str = ""  # URLs separated by "; "
    note: str = ""
    optional: bool = False
    make: dict | None = None  # {"inputs": {material_key: quantity}, "waste_high": 1.2}
    checked: str = ""


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
    by_path: dict  # core items only: path -> (low, high)


@dataclass(frozen=True)
class Tier:
    name: str
    tags: int
    low: float
    high: float


@dataclass(frozen=True)
class PriceRow:
    kind: str  # "item" or "material"
    key: str
    used_by: str
    status: str
    low: float
    high: float
    checked: str
    freshness: str


def check_date_format(value: str) -> None:
    if value and not _DATE_RE.match(value):
        raise ValueError(f"checked date must be YYYY, YYYY-MM or YYYY-MM-DD, got {value!r}")


def freshness(checked: str, as_of: date = AS_OF) -> str:
    """fresh: month precision and seen within the last 12 months. Otherwise stale, year only, or undated."""
    if not checked:
        return "undated"
    if len(checked) == 4:
        return "year only"
    parts = [int(p) for p in checked.split("-")]
    seen = date(parts[0], parts[1], parts[2] if len(parts) == 3 else 1)
    age = (as_of - seen).days
    if age < 0:
        return "future"
    return "fresh" if age <= MAX_PRICE_AGE_DAYS else "stale"


def _validate_material(m: Material) -> None:
    if m.status not in STATUSES:
        raise ValueError(f"material {m.key}: unknown status {m.status!r}")
    if m.low < 0 or m.high < m.low:
        raise ValueError(f"material {m.key}: need 0 <= low <= high")
    if m.status == "unpriced" and (m.low or m.high):
        raise ValueError(f"material {m.key}: unpriced materials must have zero prices")
    check_date_format(m.checked)


def load_materials(path: Path | str = DEFAULT_MATERIALS) -> dict[str, Material]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    materials: dict[str, Material] = {}
    for key, raw in data["materials"].items():
        m = Material(key=key, **raw)  # unknown keys raise TypeError
        _validate_material(m)
        materials[key] = m
    return materials


def _validate_item(item: Item) -> None:
    if item.status not in STATUSES:
        raise ValueError(f"{item.id}: unknown status {item.status!r}")
    if item.path not in PATHS:
        raise ValueError(f"{item.id}: unknown path {item.path!r}")
    if item.qty < 1:
        raise ValueError(f"{item.id}: qty must be at least 1")
    check_date_format(item.checked)
    if item.path == "make":
        if not item.make or not item.make.get("inputs"):
            raise ValueError(f"{item.id}: a made item needs make.inputs")
        if item.low or item.high:
            raise ValueError(f"{item.id}: made items are costed from materials, not prices")
        if item.make.get("waste_high", 1.0) < 1.0:
            raise ValueError(f"{item.id}: waste_high must be at least 1")
        return
    if item.make is not None:
        raise ValueError(f"{item.id}: only made items may have make inputs")
    if item.low < 0 or item.high < item.low:
        raise ValueError(f"{item.id}: need 0 <= low <= high")
    if item.status == "unpriced" and (item.low or item.high):
        raise ValueError(f"{item.id}: unpriced items must have zero prices")


def load_catalog(
    path: Path | str = DEFAULT_CATALOG,
    materials: dict[str, Material] | None = None,
) -> dict[str, Item]:
    """Load items. With materials given, also check every make input names a real material."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    items: dict[str, Item] = {}
    for raw in data["items"]:
        item = Item(**raw)  # unknown keys raise TypeError, which is what we want
        _validate_item(item)
        if item.id in items:
            raise ValueError(f"duplicate item id {item.id}")
        if item.make and materials is not None:
            for key in item.make["inputs"]:
                if key not in materials:
                    raise ValueError(f"{item.id}: unknown material {key}")
        items[item.id] = item
    return items


def load_passes(path: Path | str = DEFAULT_PASSES) -> tuple[float, list[dict]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return float(data["budget_usd"]), data["passes"]


def unit_cost(item: Item, materials: dict[str, Material]) -> tuple[float, float]:
    """Cost of one unit. Made items sum their material inputs; the high end allows waste."""
    if item.make is None:
        return item.low, item.high
    low = high = 0.0
    for key, quantity in item.make["inputs"].items():
        m = materials[key]
        low += quantity * m.low
        high += quantity * m.high
    high *= item.make.get("waste_high", 1.0)
    return round(low, 2), round(high, 2)


def _input_statuses(item: Item, materials: dict[str, Material]) -> set[str]:
    if item.make is None:
        return set()
    return {materials[key].status for key in item.make["inputs"]}


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


def totals(
    catalog: dict[str, Item],
    ids: tuple[str, ...] | list[str],
    materials: dict[str, Material],
) -> Totals:
    core_low = core_high = opt_low = opt_high = 0.0
    placeholders = unpriced = 0
    by_path: dict[str, list[float]] = {}
    for iid in ids:
        item = catalog[iid]
        unit_lo, unit_hi = unit_cost(item, materials)
        lo, hi = unit_lo * item.qty, unit_hi * item.qty
        if item.optional:
            opt_low += lo
            opt_high += hi
        else:
            core_low += lo
            core_high += hi
            acc = by_path.setdefault(item.path, [0.0, 0.0])
            acc[0] += lo
            acc[1] += hi
        input_statuses = _input_statuses(item, materials)
        if item.status == "placeholder" or "placeholder" in input_statuses:
            placeholders += 1
        if item.status == "unpriced" or "unpriced" in input_statuses:
            unpriced += 1
    return Totals(
        round(core_low, 2),
        round(core_high, 2),
        round(opt_low, 2),
        round(opt_high, 2),
        placeholders,
        unpriced,
        {path: (round(lo, 2), round(hi, 2)) for path, (lo, hi) in by_path.items()},
    )


def made_share(t: Totals) -> float:
    """Share of core cost, at midpoints, that the owner makes or salvages in-house."""
    mids = {path: (lo + hi) / 2 for path, (lo, hi) in t.by_path.items()}
    total = sum(mids.values())
    made = sum(mids.get(path, 0.0) for path in MADE_PATHS)
    return made / total if total else 0.0


def price_rows(
    catalog: dict[str, Item],
    materials: dict[str, Material],
    ids: tuple[str, ...] | list[str] | None = None,
) -> list[PriceRow]:
    """One row per priced input: each bought item, and each material used by a made item."""
    rows: list[PriceRow] = []
    users: dict[str, list[str]] = {}
    for iid in ids if ids is not None else catalog:
        item = catalog[iid]
        if item.make:
            for key in item.make["inputs"]:
                users.setdefault(key, []).append(item.id)
        elif item.status not in ("owned", "purchased"):
            rows.append(
                PriceRow("item", item.id, item.id, item.status, item.low, item.high,
                         item.checked, freshness(item.checked))
            )
    for key, who in users.items():
        m = materials[key]
        rows.append(
            PriceRow("material", key, ", ".join(sorted(set(who))), m.status, m.low, m.high,
                     m.checked, freshness(m.checked))
        )
    return rows


def date_summary(rows: list[PriceRow]) -> tuple[int, int, int]:
    """(fresh, sourced, placeholders). Sourced means snapshot or official prices."""
    sourced = [r for r in rows if r.status in SOURCED_STATUSES]
    fresh = sum(1 for r in sourced if r.freshness == "fresh")
    placeholders = sum(1 for r in rows if r.status == "placeholder")
    return fresh, len(sourced), placeholders


def supplier_hosts(source: str) -> set[str]:
    hosts = set()
    for url in (s.strip() for s in source.split(";")):
        host = urlparse(url).netloc.removeprefix("www.")
        if host:
            hosts.add(host)
    return hosts


def dependency(catalog: dict[str, Item], ids: tuple[str, ...] | list[str]) -> tuple[list[str], list[str]]:
    """Core bought items with one listed supplier, or none. Made and owned items are skipped."""
    single, none = [], []
    for iid in ids:
        item = catalog[iid]
        if item.optional or not item.path.startswith("buy_"):
            continue
        hosts = supplier_hosts(item.source)
        if not hosts:
            none.append(iid)
        elif len(hosts) == 1:
            single.append(iid)
    return single, none


def companion_tiers(
    catalog: dict[str, Item],
    ids: tuple[str, ...] | list[str],
    materials: dict[str, Material],
) -> list[Tier]:
    """Cost of the companion setups, using the tag cost in the given pass."""
    tag_ids = [i for i in ids if catalog[i].category == "companion_tag" and not catalog[i].optional]
    tag = totals(catalog, tag_ids, materials)
    return [
        Tier("phone only", 0, 0.0, 0.0),
        Tier("phone + 1 tag", 1, tag.core_low, tag.core_high),
        Tier("phone + 2 tags", 2, round(2 * tag.core_low, 2), round(2 * tag.core_high, 2)),
    ]


def _budget_status(t: Totals, budget: float) -> str:
    if t.core_high <= budget:
        return "fits budget at low and high prices"
    if t.core_low <= budget:
        return "fits budget at low prices only"
    return "over budget"


def _change(p: Pass, t: Totals, by_id: dict[str, Totals]) -> str:
    if p.based_on is None:
        return ""
    base = by_id[p.based_on]
    return (
        f"change vs {p.based_on}: {t.core_low - base.core_low:+,.2f}"
        f" to {t.core_high - base.core_high:+,.2f}"
    )


def report(
    catalog: dict[str, Item],
    passes: list[Pass],
    budget: float,
    materials: dict[str, Material],
) -> str:
    lines = []
    by_id: dict[str, Totals] = {}
    for p in passes:
        t = totals(catalog, p.items, materials)
        by_id[p.id] = t
        mids = {path: (lo + hi) / 2 for path, (lo, hi) in t.by_path.items()}
        fresh, sourced, _ = date_summary(price_rows(catalog, materials, p.items))
        lines.append(f"{p.id}  {p.title}")
        lines.append(
            f"    core ${t.core_low:,.2f} to ${t.core_high:,.2f}"
            f"   optional ${t.optional_low:,.2f} to ${t.optional_high:,.2f}"
            f"   {_budget_status(t, budget)}"
        )
        lines.append(
            f"    made in house {made_share(t):.0%} of core (midpoints)"
            f"   already owned ${mids.get('owned', 0):,.2f}"
            f"   retail ${mids.get('buy_retail', 0):,.2f}"
            f"   bulk and service ${mids.get('buy_bulk', 0) + mids.get('buy_service', 0):,.2f}"
            f"   used ${mids.get('buy_used', 0):,.2f}"
        )
        change = _change(p, t, by_id)
        lines.append(
            f"    placeholders {t.placeholders}   unpriced {t.unpriced}"
            f"   sourced prices dated in the last 12 months {fresh} of {sourced}"
            + (f"   {change}" if change else "")
        )
    return "\n".join(lines)


def passes_markdown(
    catalog: dict[str, Item],
    passes: list[Pass],
    budget: float,
    materials: dict[str, Material],
) -> str:
    rows = [
        "| Pass | Based on | Core low | Core high | Change vs base (low to high) | Made in house (midpoint) | Budget | Placeholders | Sourced prices dated in last 12 months |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    by_id: dict[str, Totals] = {}
    for p in passes:
        t = totals(catalog, p.items, materials)
        by_id[p.id] = t
        change = "none (starting point)"
        if p.based_on is not None:
            base = by_id[p.based_on]
            change = (
                f"{t.core_low - base.core_low:+,.2f} to {t.core_high - base.core_high:+,.2f}"
            )
        fresh, sourced, _ = date_summary(price_rows(catalog, materials, p.items))
        rows.append(
            f"| {p.id} {p.title} | {p.based_on or 'none'} | {t.core_low:,.2f} | {t.core_high:,.2f} | "
            f"{change} | {made_share(t):.0%} | {_budget_status(t, budget)} | {t.placeholders} | "
            f"{fresh} of {sourced} |"
        )
    return "\n".join(rows)


def _links(source: str) -> str:
    links = []
    for url in filter(None, (s.strip() for s in source.split(";"))):
        if urlparse(url).netloc:
            host = urlparse(url).netloc.removeprefix("www.")
            links.append(f"[{host}]({url})")
        else:
            links.append(url)
    return " · ".join(links) if links else "none"


def catalog_markdown(catalog: dict[str, Item], materials: dict[str, Material]) -> str:
    rows = [
        "| Item | Category | Path | Qty | USD each (low to high) | Status | Checked | Sources | Note |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for item in catalog.values():
        lo, hi = unit_cost(item, materials)
        price = f"{lo:,.2f} to {hi:,.2f}" if hi != lo else f"{lo:,.2f}"
        name = item.name + (" (optional)" if item.optional else "")
        checked = item.checked or ("from materials" if item.make else "undated")
        rows.append(
            f"| {name} | {item.category} | {item.path} | {item.qty} | {price} | {item.status} | "
            f"{checked} | {_links(item.source)} | {item.note} |"
        )
    return "\n".join(rows)


def audit_markdown(catalog: dict[str, Item], materials: dict[str, Material]) -> str:
    rows = price_rows(catalog, materials)
    lines = [
        "| Kind | Key | Used by | Status | USD low | USD high | Checked | Freshness |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in sorted(rows, key=lambda r: (r.freshness != "fresh", r.kind, r.key)):
        lines.append(
            f"| {r.kind} | {r.key} | {r.used_by} | {r.status} | {r.low:,.3f} | {r.high:,.3f} | "
            f"{r.checked or 'undated'} | {r.freshness} |"
        )
    fresh, sourced, placeholders = date_summary(rows)
    lines.append("")
    lines.append(
        f"Sourced prices dated in the last 12 months: {fresh} of {sourced}. "
        f"Placeholders (guesses): {placeholders}. Cutoff: {AS_OF.isoformat()}."
    )
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    materials = load_materials()
    catalog = load_catalog(DEFAULT_CATALOG, materials)
    if "--markdown" in argv:
        print(catalog_markdown(catalog, materials))
        return 0
    if "--audit" in argv:
        print(audit_markdown(catalog, materials))
        return 0
    budget, raw = load_passes()
    passes = resolve(catalog, raw)
    if "--passes-markdown" in argv:
        print(passes_markdown(catalog, passes, budget, materials))
        return 0
    print(report(catalog, passes, budget, materials))
    last = passes[-1]
    single, none = dependency(catalog, last.items)
    print()
    print(f"Dependency check, {last.id}:")
    print(f"    bought from one listed supplier: {', '.join(single) or 'none'}")
    print(f"    bought with no supplier listed:  {', '.join(none) or 'none'}")
    print()
    print(f"Companion tiers (tag cost from {passes[0].id}):")
    for tier in companion_tiers(catalog, passes[0].items, materials):
        print(f"    {tier.name:<16} ${tier.low:,.2f} to ${tier.high:,.2f}")
    print("    phone + wearable IMUs: unpriced (see bom/catalog.json, imu_wearable)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
