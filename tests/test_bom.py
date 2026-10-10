import json

import pytest

from follow_me.bom import (
    DEFAULT_CATALOG,
    DEFAULT_PASSES,
    Item,
    catalog_markdown,
    companion_tiers,
    load_catalog,
    load_passes,
    main,
    report,
    resolve,
    totals,
)


def write_catalog(tmp_path, items):
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps({"items": items}), encoding="utf-8")
    return path


def raw_item(**overrides):
    base = {
        "id": "a",
        "name": "A",
        "category": "misc",
        "qty": 1,
        "low": 10,
        "high": 20,
        "status": "snapshot",
    }
    base.update(overrides)
    return base


def small_catalog(tmp_path):
    items = [
        raw_item(id="a", low=10, high=20),
        raw_item(id="b", low=5, high=5, qty=2, status="estimate"),
        raw_item(id="c", low=3, high=8, status="placeholder"),
        raw_item(id="d", low=0, high=0, status="unpriced"),
        raw_item(id="opt", low=50, high=60, optional=True),
    ]
    return load_catalog(write_catalog(tmp_path, items))


# ---- shipped data -----------------------------------------------------------

def test_shipped_catalog_loads_and_validates():
    catalog = load_catalog(DEFAULT_CATALOG)
    assert "fc_pix32_v6" in catalog
    assert all(item.high >= item.low for item in catalog.values())


def test_shipped_passes_resolve_in_order():
    catalog = load_catalog(DEFAULT_CATALOG)
    _, raw = load_passes(DEFAULT_PASSES)
    passes = resolve(catalog, raw)
    assert [p.id for p in passes] == [
        "pass0_retail_autopilot",
        "pass1_shop_smart",
        "pass2_print_structure",
        "pass3_bench_first",
        "pass4_repurpose_phone",
    ]


def test_each_shipped_pass_points_at_its_base():
    catalog = load_catalog(DEFAULT_CATALOG)
    _, raw = load_passes(DEFAULT_PASSES)
    passes = {p.id: p for p in resolve(catalog, raw)}
    assert passes["pass0_retail_autopilot"].based_on is None
    assert passes["pass1_shop_smart"].based_on == "pass0_retail_autopilot"
    assert passes["pass4_repurpose_phone"].based_on == "pass2_print_structure"


def test_costs_fall_from_retail_to_the_bench_kit():
    catalog = load_catalog(DEFAULT_CATALOG)
    _, raw = load_passes(DEFAULT_PASSES)
    passes = {p.id: p for p in resolve(catalog, raw)}
    low = {pid: totals(catalog, p.items).core_low for pid, p in passes.items()}
    assert low["pass0_retail_autopilot"] > low["pass1_shop_smart"] > low["pass2_print_structure"]
    assert low["pass2_print_structure"] > low["pass3_bench_first"]


def test_bench_kit_fits_the_budget_at_low_prices():
    catalog = load_catalog(DEFAULT_CATALOG)
    budget, raw = load_passes(DEFAULT_PASSES)
    bench = {p.id: p for p in resolve(catalog, raw)}["pass3_bench_first"]
    t = totals(catalog, bench.items)
    assert t.core_low <= budget


def test_a_flying_drone_is_far_over_budget():
    catalog = load_catalog(DEFAULT_CATALOG)
    budget, raw = load_passes(DEFAULT_PASSES)
    retail = resolve(catalog, raw)[0]
    assert totals(catalog, retail.items).core_low > 5 * budget


def test_optional_tello_is_kept_out_of_core_totals():
    catalog = load_catalog(DEFAULT_CATALOG)
    _, raw = load_passes(DEFAULT_PASSES)
    bench = {p.id: p for p in resolve(catalog, raw)}["pass3_bench_first"]
    with_tello = totals(catalog, bench.items)
    without = totals(catalog, [i for i in bench.items if i != "tello_refurb"])
    assert with_tello.core_low == without.core_low
    assert with_tello.optional_low == pytest.approx(79.0)


def test_shipped_placeholders_are_counted_not_hidden():
    catalog = load_catalog(DEFAULT_CATALOG)
    _, raw = load_passes(DEFAULT_PASSES)
    retail = resolve(catalog, raw)[0]
    assert totals(catalog, retail.items).placeholders >= 5


# ---- validation -------------------------------------------------------------

def test_unknown_status_is_rejected(tmp_path):
    path = write_catalog(tmp_path, [raw_item(status="guess")])
    with pytest.raises(ValueError, match="unknown status"):
        load_catalog(path)


def test_unpriced_item_with_a_price_is_rejected(tmp_path):
    path = write_catalog(tmp_path, [raw_item(status="unpriced", low=5, high=5)])
    with pytest.raises(ValueError, match="zero prices"):
        load_catalog(path)


def test_high_below_low_is_rejected(tmp_path):
    path = write_catalog(tmp_path, [raw_item(low=20, high=10)])
    with pytest.raises(ValueError, match="low <= high"):
        load_catalog(path)


def test_zero_quantity_is_rejected(tmp_path):
    path = write_catalog(tmp_path, [raw_item(qty=0)])
    with pytest.raises(ValueError, match="qty"):
        load_catalog(path)


def test_duplicate_item_ids_are_rejected(tmp_path):
    path = write_catalog(tmp_path, [raw_item(id="x"), raw_item(id="x")])
    with pytest.raises(ValueError, match="duplicate item"):
        load_catalog(path)


def test_unknown_fields_are_rejected(tmp_path):
    path = write_catalog(tmp_path, [raw_item(colour="red")])
    with pytest.raises(TypeError):
        load_catalog(path)


# ---- pass resolution --------------------------------------------------------

def test_pass_adds_and_removes_relative_to_its_base(tmp_path):
    catalog = small_catalog(tmp_path)
    raw = [
        {"id": "p0", "title": "t", "based_on": None, "add": ["a", "b"], "remove": []},
        {"id": "p1", "title": "t", "based_on": "p0", "add": ["c"], "remove": ["a"]},
    ]
    p0, p1 = resolve(catalog, raw)
    assert p0.items == ("a", "b")
    assert p1.items == ("b", "c")
    assert p1.removed == ("a",)
    assert p1.added == ("c",)


def test_removing_an_item_not_in_the_base_is_an_error(tmp_path):
    catalog = small_catalog(tmp_path)
    raw = [
        {"id": "p0", "title": "t", "based_on": None, "add": ["a"], "remove": []},
        {"id": "p1", "title": "t", "based_on": "p0", "add": [], "remove": ["c"]},
    ]
    with pytest.raises(ValueError, match="not in the base"):
        resolve(catalog, raw)


def test_adding_an_item_already_present_is_an_error(tmp_path):
    catalog = small_catalog(tmp_path)
    raw = [
        {"id": "p0", "title": "t", "based_on": None, "add": ["a"], "remove": []},
        {"id": "p1", "title": "t", "based_on": "p0", "add": ["a"], "remove": []},
    ]
    with pytest.raises(ValueError, match="already present"):
        resolve(catalog, raw)


def test_unknown_item_in_a_pass_is_an_error(tmp_path):
    catalog = small_catalog(tmp_path)
    raw = [{"id": "p0", "title": "t", "based_on": None, "add": ["nope"], "remove": []}]
    with pytest.raises(ValueError, match="unknown item"):
        resolve(catalog, raw)


def test_first_pass_must_have_no_base(tmp_path):
    catalog = small_catalog(tmp_path)
    raw = [{"id": "p0", "title": "t", "based_on": "ghost", "add": ["a"], "remove": []}]
    with pytest.raises(ValueError, match="no base"):
        resolve(catalog, raw)


def test_later_pass_needs_an_existing_base(tmp_path):
    catalog = small_catalog(tmp_path)
    raw = [
        {"id": "p0", "title": "t", "based_on": None, "add": ["a"], "remove": []},
        {"id": "p1", "title": "t", "based_on": "ghost", "add": [], "remove": []},
    ]
    with pytest.raises(ValueError, match="earlier pass"):
        resolve(catalog, raw)


def test_duplicate_pass_ids_are_rejected(tmp_path):
    catalog = small_catalog(tmp_path)
    raw = [
        {"id": "p0", "title": "t", "based_on": None, "add": ["a"], "remove": []},
        {"id": "p0", "title": "t", "based_on": "p0", "add": [], "remove": []},
    ]
    with pytest.raises(ValueError, match="duplicate pass"):
        resolve(catalog, raw)


# ---- totals, tiers, reports ---------------------------------------------------

def test_totals_split_core_optional_and_flags(tmp_path):
    catalog = small_catalog(tmp_path)
    t = totals(catalog, ["a", "b", "c", "d", "opt"])
    assert t.core_low == pytest.approx(10 + 2 * 5 + 3)  # a + two of b + c + d(0)
    assert t.core_high == pytest.approx(20 + 2 * 5 + 8)
    assert t.optional_low == pytest.approx(50)
    assert t.optional_high == pytest.approx(60)
    assert t.placeholders == 1
    assert t.unpriced == 1


def test_companion_tiers_scale_with_the_tag_cost(tmp_path):
    items = [
        raw_item(id="tag1", category="companion_tag", low=10, high=20),
        raw_item(id="tag2", category="companion_tag", low=5, high=5, qty=2),
        raw_item(id="other", low=99, high=99),
    ]
    catalog = load_catalog(write_catalog(tmp_path, items))
    tiers = {t.name: t for t in companion_tiers(catalog, ["tag1", "tag2", "other"])}
    assert tiers["phone only"].high == 0
    assert tiers["phone + 1 tag"].low == pytest.approx(20)  # 10 + 2*5
    assert tiers["phone + 1 tag"].high == pytest.approx(30)  # 20 + 2*5
    assert tiers["phone + 2 tags"].low == pytest.approx(40)


def test_report_names_each_pass_and_its_budget_status(tmp_path):
    catalog = small_catalog(tmp_path)
    raw = [
        {"id": "p0", "title": "first", "based_on": None, "add": ["a", "b"], "remove": []},
        {"id": "p1", "title": "second", "based_on": "p0", "add": [], "remove": ["b"]},
    ]
    passes = resolve(catalog, raw)
    text = report(catalog, passes, budget=15)
    # p0 is a (10 to 20) plus b twice (5 each): core 20 to 30, over a 15 budget.
    assert "core $20.00 to $30.00" in text
    assert "over budget" in text
    # p1 drops b: core 10 to 20. The low end fits 15, the high end does not.
    assert "core $10.00 to $20.00" in text
    assert "fits budget at low prices only" in text
    assert "change vs p0: -10.00 to -10.00" in text


def test_markdown_lists_every_item_with_a_link_for_each_source(tmp_path):
    items = [raw_item(id="x", source="https://example.com/a; https://shop.example.org/b")]
    catalog = load_catalog(write_catalog(tmp_path, items))
    md = catalog_markdown(catalog)
    assert "| A | misc | 1 | 10.00 to 20.00 | snapshot |" in md
    assert "[example.com](https://example.com/a)" in md
    assert "[shop.example.org](https://shop.example.org/b)" in md


def test_cli_prints_every_pass(capsys):
    assert main([]) == 0
    out = capsys.readouterr().out
    assert "pass0_retail_autopilot" in out and "pass4_repurpose_phone" in out
    assert "Companion tiers" in out


def test_cli_markdown_mode(capsys):
    assert main(["--markdown"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("| Item | Category")
    assert "fc_pix32_v6" not in out  # the id is not shown, the name is
    assert "Holybro Pix32 v6" in out
