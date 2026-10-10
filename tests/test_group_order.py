import json
import re
from pathlib import Path

import pytest

from follow_me.bom import Item, Material
from follow_me.group_order import (
    DEFAULT_GROUP_ORDER,
    drones_supported,
    group_order_markdown,
    line_total,
    load_group_order,
    main,
    per_member,
    state_counts,
    sum_lines,
)

REPO = Path(__file__).resolve().parents[1]

MATS = {
    "magnet": Material("magnet", "each", 0.02, 0.10, "snapshot", moq=1000),
    "guess": Material("guess", "each", 1.0, 2.0, "placeholder"),
    "est": Material("est", "each", 1.0, 2.0, "estimate"),
}
CAT = {
    "board": Item("board", "Board", "x", 1, 5.0, 10.0, "estimate", "buy_service", moq=5, checked="2026-09"),
}


def write_plan(tmp_path, lines, **top):
    data = {
        "status": "draft",
        "last_updated": "2026-10-10",
        "member_counts": [5, 10],
        "waves": {"1": "One", "2": "Two"},
        "facts": [],
        "open_decisions": [],
        "lines": lines,
    }
    data.update(top)
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def line(**over):
    base = {
        "id": "a", "name": "A", "wave": 1, "supplier_type": "factory", "unit": "disc",
        "order_qty": 1000, "state": "needs quote", "material": "magnet",
    }
    base.update(over)
    return base


def load(tmp_path, lines, **top):
    return load_group_order(write_plan(tmp_path, lines, **top), CAT, MATS)


# ---- price sources ------------------------------------------------------------

def test_material_line_takes_price_and_minimum_from_the_material(tmp_path):
    plan = load(tmp_path, [line()])
    p = plan.lines[0].price
    assert (p.low, p.high, p.moq, p.basis) == (0.02, 0.10, 1000.0, "listing")


def test_placeholder_and_estimate_materials_keep_their_basis(tmp_path):
    plan = load(tmp_path, [line(id="a", material="guess", order_qty=1), line(id="b", material="est", order_qty=1)])
    assert [ln.price.basis for ln in plan.lines] == ["placeholder", "estimate"]


def test_bom_item_line_takes_cost_and_date_from_the_model(tmp_path):
    raw = line(id="b", supplier_type="fab", unit="board", order_qty=10)
    del raw["material"]
    raw["bom_item"] = "board"
    p = load(tmp_path, [raw]).lines[0].price
    assert (p.low, p.high, p.moq, p.basis, p.checked) == (5.0, 10.0, 5.0, "estimate", "2026-09")


def test_explicit_price_line(tmp_path):
    raw = line(order_qty=25)
    del raw["material"]
    raw["price"] = {"low": 0.78, "high": 0.78, "moq": 25, "basis": "listing", "checked": "2026-08"}
    p = load(tmp_path, [raw]).lines[0].price
    assert (p.low, p.moq, p.checked) == (0.78, 25.0, "2026-08")


def test_exactly_one_price_source_is_required(tmp_path):
    both = line()
    both["price"] = {"low": 1, "high": 1}
    with pytest.raises(ValueError, match="exactly one"):
        load(tmp_path, [both])
    neither = line()
    del neither["material"]
    with pytest.raises(ValueError, match="exactly one"):
        load(tmp_path, [neither])


def test_unknown_material_and_item_are_rejected(tmp_path):
    with pytest.raises(ValueError, match="unknown material"):
        load(tmp_path, [line(material="nope")])
    raw = line()
    del raw["material"]
    raw["bom_item"] = "nope"
    with pytest.raises(ValueError, match="unknown catalog item"):
        load(tmp_path, [raw])


def test_a_quote_cannot_use_the_quote_basis_as_a_listing_price(tmp_path):
    raw = line(order_qty=25)
    del raw["material"]
    raw["price"] = {"low": 1, "high": 1, "basis": "quote"}
    with pytest.raises(ValueError, match="basis"):
        load(tmp_path, [raw])


# ---- minimums, quotes and states ---------------------------------------------

def test_order_below_the_minimum_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="below the minimum order"):
        load(tmp_path, [line(order_qty=500)])


def test_quote_overrides_the_price_and_needs_a_quoted_state(tmp_path):
    ok = line(state="quoted", quote={"low": 0.05, "high": 0.05, "checked": "2026-11-02", "ref": "quote 1, delivered"})
    p = load(tmp_path, [ok]).lines[0].price
    assert (p.low, p.high, p.basis, p.checked, p.source) == (0.05, 0.05, "quote", "2026-11-02", "quote 1, delivered")
    assert p.moq == 1000.0  # the minimum still comes from the underlying listing

    wrong_state = line(quote={"low": 0.05, "high": 0.05, "checked": "2026-11-02", "ref": "x"})
    with pytest.raises(ValueError, match="with a quote must be"):
        load(tmp_path, [wrong_state])


def test_a_quoted_state_needs_a_quote(tmp_path):
    with pytest.raises(ValueError, match="needs a quote"):
        load(tmp_path, [line(state="ordered")])


def test_a_quote_needs_all_its_fields(tmp_path):
    with pytest.raises(ValueError, match="needs ref"):
        load(tmp_path, [line(state="quoted", quote={"low": 1, "high": 1, "checked": "2026-11-02"})])


def test_a_blocked_line_needs_a_reason(tmp_path):
    with pytest.raises(ValueError, match="blocked_by"):
        load(tmp_path, [line(state="blocked")])
    assert load(tmp_path, [line(state="blocked", blocked_by="no design yet")]).lines[0].state == "blocked"


# ---- structure ----------------------------------------------------------------

def test_unknown_and_missing_fields_are_rejected(tmp_path):
    with pytest.raises(ValueError, match="unknown fields"):
        load(tmp_path, [line(colour="red")])
    raw = line()
    del raw["unit"]
    with pytest.raises(ValueError, match="missing unit"):
        load(tmp_path, [raw])


def test_duplicate_ids_bad_enums_and_waves_are_rejected(tmp_path):
    with pytest.raises(ValueError, match="duplicate line"):
        load(tmp_path, [line(), line()])
    with pytest.raises(ValueError, match="supplier_type"):
        load(tmp_path, [line(supplier_type="friend")])
    with pytest.raises(ValueError, match="unknown state"):
        load(tmp_path, [line(state="maybe")])
    with pytest.raises(ValueError, match="wave 3"):
        load(tmp_path, [line(wave=3)])


def test_plan_level_checks(tmp_path):
    with pytest.raises(ValueError, match="plan status"):
        load(tmp_path, [line()], status="wishful")
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        load(tmp_path, [line()], last_updated="2026-10")
    with pytest.raises(ValueError, match="member_counts"):
        load(tmp_path, [line()], member_counts=[0])


# ---- arithmetic ---------------------------------------------------------------

def test_line_total_and_drones_supported(tmp_path):
    ln = load(tmp_path, [line(units_per_drone=56)]).lines[0]
    assert line_total(ln) == (20.0, 100.0)
    assert drones_supported(ln) == 17  # 1000 // 56, rounded down
    assert drones_supported(load(tmp_path, [line()]).lines[0]) is None


def test_sum_per_member_and_state_counts(tmp_path):
    plan = load(
        tmp_path,
        [
            line(id="a"),
            line(id="b", state="blocked", blocked_by="design", wave=2),
        ],
    )
    total = sum_lines(plan.lines)
    assert total == (40.0, 200.0)
    assert per_member(total, 10) == (4.0, 20.0)
    counts = state_counts(plan)
    assert counts["needs quote"] == 1 and counts["blocked"] == 1 and counts["quoted"] == 0


def test_markdown_has_totals_lines_blocked_decisions_and_facts(tmp_path):
    plan = load(
        tmp_path,
        [line(id="a", inspection="Pull-test ten."), line(id="b", state="blocked", blocked_by="design", wave=2)],
        open_decisions=[
            {"id": "x", "question": "Who coordinates?", "status": "open", "decision": ""},
            {"id": "y", "question": "Where do parts ship?", "status": "decided", "decision": "club address"},
        ],
        facts=[{"fact": "The club can order.", "source": "owner", "confirmed": False}],
    )
    md = group_order_markdown(plan)
    assert "**Plan status:** draft." in md
    assert "Wave 1: One" in md and "All lines" in md and "Per member at 5 (USD)" in md
    assert "### Blocked lines" in md and "design" in md
    assert "- [ ] Who coordinates?" in md and "- [x] Where do parts ship? Decision: club address" in md
    assert "| The club can order. | owner | no |" in md
    assert "Pull-test ten." in md


# ---- the shipped plan -----------------------------------------------------------

def test_shipped_plan_loads_and_waves_make_sense():
    plan = load_group_order(DEFAULT_GROUP_ORDER)
    by_wave = {}
    for ln in plan.lines:
        by_wave.setdefault(ln.wave, []).append(ln)
    assert all(ln.state == "needs quote" for ln in by_wave[1])
    assert all(ln.state == "blocked" for ln in by_wave[2] if ln.supplier_type == "fab")
    assert all(ln.state == "blocked" for ln in by_wave[3])
    assert sum_lines(by_wave[1])[1] < sum_lines(by_wave[2])[1] < sum_lines(by_wave[3])[1]


def test_shipped_plan_has_no_quotes_yet_and_says_so():
    plan = load_group_order(DEFAULT_GROUP_ORDER)
    assert all(ln.price.basis != "quote" for ln in plan.lines)
    assert plan.status == "draft"
    club = [f for f in plan.facts if "IEEE club can run group orders" in f["fact"]]
    assert club and club[0]["confirmed"] is False


def test_shipped_plan_lines_meet_the_factory_minimums():
    plan = {ln.id: ln for ln in load_group_order(DEFAULT_GROUP_ORDER).lines}
    assert plan["magnets_factory"].order_qty >= 1000
    assert plan["bearings_factory"].order_qty >= 100
    assert plan["stator_cores_factory"].order_qty >= 1000


def test_cli_prints_the_generated_markdown(capsys):
    assert main([]) == 0
    assert "### Totals" in capsys.readouterr().out


# ---- privacy: the repository is public ------------------------------------------

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE = re.compile(r"\(?\b\d{3}\)?[-. ]\d{3}[-. ]\d{4}\b")


@pytest.mark.parametrize(
    "path",
    ["bom/group_order.json", "docs/group-order.md", "docs/supply-side.md"],
)
def test_public_files_hold_no_emails_or_phone_numbers(path):
    text = (REPO / path).read_text(encoding="utf-8")
    assert not EMAIL.search(text), f"email-like text in {path}"
    assert not PHONE.search(text), f"phone-like text in {path}"
