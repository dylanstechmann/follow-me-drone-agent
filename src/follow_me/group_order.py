"""Group order plan for the IEEE club: lines, quotes, totals and per-member shares.

The plan lives in bom/group_order.json. Prices come from the cost model
(bom/materials.json or bom/catalog.json) until a supplier quote replaces them,
so a change to a material price moves the plan.

This file is public. It uses roles only. Never put names, email addresses, phone
numbers, delivery addresses, payment records or order screenshots in it.

Usage:
  python -m follow_me.group_order   # print the generated markdown
"""

import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path

from follow_me.bom import (
    DEFAULT_CATALOG,
    DEFAULT_MATERIALS,
    Item,
    Material,
    check_date_format,
    load_catalog,
    load_materials,
    unit_cost,
)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GROUP_ORDER = ROOT / "bom" / "group_order.json"

PLAN_STATUSES = ("draft", "collecting interest", "quotes requested", "quotes in", "ordered", "closed")
LINE_STATES = ("blocked", "needs quote", "quoted", "ordered", "received", "inspected")
QUOTED_STATES = ("quoted", "ordered", "received", "inspected")
SUPPLIER_TYPES = ("factory", "distributor", "fab", "retail", "shared")
BASES = ("quote", "listing", "estimate", "placeholder")

_LINE_KEYS = {
    "id", "name", "wave", "supplier_type", "unit", "order_qty", "state",
    "material", "bom_item", "price", "quote",
    "ships_from", "units_per_drone", "blocked_by", "candidates", "inspection", "note",
}
_REQUIRED_LINE_KEYS = {"id", "name", "wave", "supplier_type", "unit", "order_qty", "state"}


@dataclass(frozen=True)
class Price:
    low: float
    high: float
    moq: float
    basis: str  # quote, listing, estimate or placeholder
    checked: str
    source: str


@dataclass(frozen=True)
class Line:
    id: str
    name: str
    wave: int
    supplier_type: str
    unit: str
    order_qty: float
    state: str
    price: Price
    ships_from: str = ""
    units_per_drone: float | None = None
    blocked_by: str = ""
    candidates: tuple[str, ...] = ()
    inspection: str = ""
    note: str = ""


@dataclass(frozen=True)
class Plan:
    status: str
    last_updated: str
    member_counts: tuple[int, ...]
    waves: dict
    facts: tuple[dict, ...]
    open_decisions: tuple[dict, ...]
    lines: tuple[Line, ...]


def _check_range(where: str, low: float, high: float) -> None:
    if low < 0 or high < low:
        raise ValueError(f"{where}: need 0 <= low <= high")


def _resolve_price(
    raw: dict,
    catalog: dict[str, Item],
    materials: dict[str, Material],
) -> Price:
    lid = raw["id"]
    given = [k for k in ("material", "bom_item", "price") if k in raw]
    if len(given) != 1:
        raise ValueError(f"{lid}: give exactly one of material, bom_item or price")

    if "material" in raw:
        key = raw["material"]
        if key not in materials:
            raise ValueError(f"{lid}: unknown material {key}")
        m = materials[key]
        basis = m.status if m.status in ("placeholder", "estimate") else "listing"
        base = Price(m.low, m.high, float(m.moq), basis, m.checked, m.source)
    elif "bom_item" in raw:
        key = raw["bom_item"]
        if key not in catalog:
            raise ValueError(f"{lid}: unknown catalog item {key}")
        item = catalog[key]
        low, high = unit_cost(item, materials)
        base = Price(low, high, float(item.moq), "estimate", item.checked, item.source)
    else:
        p = raw["price"]
        base = Price(
            float(p["low"]), float(p["high"]), float(p.get("moq", 1)),
            p.get("basis", "listing"), p.get("checked", ""), p.get("source", ""),
        )
        if base.basis not in BASES or base.basis == "quote":
            raise ValueError(f"{lid}: price basis must be listing, estimate or placeholder")
    _check_range(lid, base.low, base.high)
    check_date_format(base.checked)

    if "quote" not in raw:
        return base
    q = raw["quote"]
    for key in ("low", "high", "checked", "ref"):
        if key not in q:
            raise ValueError(f"{lid}: a quote needs {key}")
    low, high = float(q["low"]), float(q["high"])
    _check_range(lid, low, high)
    check_date_format(q["checked"])
    return Price(low, high, float(q.get("moq", base.moq)), "quote", q["checked"], q["ref"])


def _build_line(raw: dict, catalog: dict[str, Item], materials: dict[str, Material]) -> Line:
    missing = _REQUIRED_LINE_KEYS - raw.keys()
    if missing:
        raise ValueError(f"line {raw.get('id', '?')}: missing {', '.join(sorted(missing))}")
    unknown = raw.keys() - _LINE_KEYS
    if unknown:
        raise ValueError(f"{raw['id']}: unknown fields {', '.join(sorted(unknown))}")
    lid = raw["id"]
    if raw["supplier_type"] not in SUPPLIER_TYPES:
        raise ValueError(f"{lid}: unknown supplier_type {raw['supplier_type']!r}")
    if raw["state"] not in LINE_STATES:
        raise ValueError(f"{lid}: unknown state {raw['state']!r}")
    price = _resolve_price(raw, catalog, materials)
    qty = float(raw["order_qty"])
    if qty <= 0:
        raise ValueError(f"{lid}: order_qty must be positive")
    if qty < price.moq:
        raise ValueError(f"{lid}: order_qty {qty:g} is below the minimum order {price.moq:g}")
    has_quote = "quote" in raw
    if raw["state"] in QUOTED_STATES and not has_quote:
        raise ValueError(f"{lid}: state {raw['state']!r} needs a quote")
    if has_quote and raw["state"] not in QUOTED_STATES:
        raise ValueError(f"{lid}: a line with a quote must be quoted, ordered, received or inspected")
    if raw["state"] == "blocked" and not raw.get("blocked_by"):
        raise ValueError(f"{lid}: a blocked line needs blocked_by")
    upd = raw.get("units_per_drone")
    if upd is not None and upd <= 0:
        raise ValueError(f"{lid}: units_per_drone must be positive")
    return Line(
        id=lid,
        name=raw["name"],
        wave=int(raw["wave"]),
        supplier_type=raw["supplier_type"],
        unit=raw["unit"],
        order_qty=qty,
        state=raw["state"],
        price=price,
        ships_from=raw.get("ships_from", ""),
        units_per_drone=float(upd) if upd is not None else None,
        blocked_by=raw.get("blocked_by", ""),
        candidates=tuple(raw.get("candidates", ())),
        inspection=raw.get("inspection", ""),
        note=raw.get("note", ""),
    )


def load_group_order(
    path: Path | str = DEFAULT_GROUP_ORDER,
    catalog: dict[str, Item] | None = None,
    materials: dict[str, Material] | None = None,
) -> Plan:
    materials = materials if materials is not None else load_materials(DEFAULT_MATERIALS)
    catalog = catalog if catalog is not None else load_catalog(DEFAULT_CATALOG, materials)
    data = json.loads(Path(path).read_text(encoding="utf-8"))

    if data["status"] not in PLAN_STATUSES:
        raise ValueError(f"unknown plan status {data['status']!r}")
    updated = data["last_updated"]
    if len(updated) != 10:
        raise ValueError("last_updated must be YYYY-MM-DD")
    check_date_format(updated)
    counts = tuple(int(n) for n in data["member_counts"])
    if not counts or any(n < 1 for n in counts):
        raise ValueError("member_counts must be positive")

    lines: list[Line] = []
    seen: set[str] = set()
    for raw in data["lines"]:
        line = _build_line(raw, catalog, materials)
        if line.id in seen:
            raise ValueError(f"duplicate line id {line.id}")
        seen.add(line.id)
        if str(line.wave) not in data["waves"]:
            raise ValueError(f"{line.id}: wave {line.wave} has no name in waves")
        lines.append(line)

    return Plan(
        status=data["status"],
        last_updated=updated,
        member_counts=counts,
        waves=dict(data["waves"]),
        facts=tuple(data.get("facts", ())),
        open_decisions=tuple(data.get("open_decisions", ())),
        lines=tuple(lines),
    )


def line_total(line: Line) -> tuple[float, float]:
    return round(line.order_qty * line.price.low, 2), round(line.order_qty * line.price.high, 2)


def drones_supported(line: Line) -> int | None:
    """How many drones the ordered quantity covers, rounded down."""
    if line.units_per_drone is None:
        return None
    return math.floor(line.order_qty / line.units_per_drone + 1e-9)


def sum_lines(lines) -> tuple[float, float]:
    lo = hi = 0.0
    for line in lines:
        a, b = line_total(line)
        lo += a
        hi += b
    return round(lo, 2), round(hi, 2)


def state_counts(plan: Plan) -> dict[str, int]:
    counts = {state: 0 for state in LINE_STATES}
    for line in plan.lines:
        counts[line.state] += 1
    return counts


def per_member(total: tuple[float, float], members: int) -> tuple[float, float]:
    return round(total[0] / members, 2), round(total[1] / members, 2)


def _money(x: float) -> str:
    return f"{x:,.3f}" if x < 0.1 else f"{x:,.2f}"


def _range(lo: float, hi: float) -> str:
    return _money(lo) if lo == hi else f"{_money(lo)} to {_money(hi)}"


def group_order_markdown(plan: Plan) -> str:
    out: list[str] = []
    counts = state_counts(plan)
    states = ", ".join(f"{n} {s}" for s, n in counts.items() if n)
    quotes = sum(1 for line in plan.lines if line.price.basis == "quote")
    out.append(
        f"**Plan status:** {plan.status}. **Last updated:** {plan.last_updated}. "
        f"**Lines:** {len(plan.lines)} ({states}). "
        f"**Supplier quotes in hand:** {quotes} of {len(plan.lines)}."
    )
    out.append("")

    out.append("### Totals")
    out.append("")
    header = "| Scope | Cash low (USD) | Cash high (USD) |"
    divider = "|---|---|---|"
    for n in plan.member_counts:
        header += f" Per member at {n} (USD) |"
        divider += "---|"
    out.append(header)
    out.append(divider)
    scopes = [
        (f"Wave {w}: {name}", [line for line in plan.lines if str(line.wave) == w])
        for w, name in plan.waves.items()
    ]
    scopes.append(("All lines", list(plan.lines)))
    for label, lines in scopes:
        lo, hi = sum_lines(lines)
        row = f"| {label} | {lo:,.2f} | {hi:,.2f} |"
        for n in plan.member_counts:
            a, b = per_member((lo, hi), n)
            row += f" {a:,.2f} to {b:,.2f} |"
        out.append(row)
    out.append("")

    out.append("### Lines")
    out.append("")
    out.append("| Wave | Line | Supplier type | Order qty (minimum) | Unit price (USD) | Line total (USD) | Price basis | State | Drones covered |")
    out.append("|---|---|---|---|---|---|---|---|---|")
    for line in plan.lines:
        lo, hi = line_total(line)
        covered = drones_supported(line)
        out.append(
            f"| {line.wave} | {line.name} | {line.supplier_type} | "
            f"{line.order_qty:g} {line.unit} ({line.price.moq:g}) | "
            f"{_range(line.price.low, line.price.high)} | {_range(lo, hi)} | "
            f"{line.price.basis}, {line.price.checked or 'undated'} | {line.state} | "
            f"{covered if covered is not None else 'n/a'} |"
        )
    out.append("")

    blocked = [line for line in plan.lines if line.state == "blocked"]
    if blocked:
        out.append("### Blocked lines")
        out.append("")
        for line in blocked:
            out.append(f"- **{line.name}:** {line.blocked_by}")
        out.append("")

    out.append("### Inspection on arrival")
    out.append("")
    for line in plan.lines:
        if line.inspection:
            out.append(f"- **{line.name}:** {line.inspection}")
    out.append("")

    out.append("### Open decisions")
    out.append("")
    for d in plan.open_decisions:
        if d["status"] == "decided":
            out.append(f"- [x] {d['question']} Decision: {d['decision']}")
        else:
            out.append(f"- [ ] {d['question']}")
    out.append("")

    out.append("### Facts and where they came from")
    out.append("")
    out.append("| Fact | Source | Confirmed |")
    out.append("|---|---|---|")
    for f in plan.facts:
        out.append(f"| {f['fact']} | {f['source']} | {'yes' if f['confirmed'] else 'no'} |")
    return "\n".join(out)


def main(argv: list[str]) -> int:
    print(group_order_markdown(load_group_order()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
