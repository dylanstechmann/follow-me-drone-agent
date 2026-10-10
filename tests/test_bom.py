import json

import pytest

from follow_me.bom import (
    DEFAULT_CATALOG,
    DEFAULT_MATERIALS,
    DEFAULT_PASSES,
    Material,
    catalog_markdown,
    companion_tiers,
    dependency,
    load_catalog,
    load_materials,
    load_passes,
    main,
    made_share,
    passes_markdown,
    report,
    resolve,
    supplier_hosts,
    totals,
    unit_cost,
)

MATS = {
    "pla": Material("pla", "kg", 10.0, 20.0, "snapshot"),
    "fr4": Material("fr4", "cm2", 0.01, 0.1, "snapshot"),
    "steel": Material("steel", "each", 0.0, 0.0, "unpriced"),
    "guess": Material("guess", "each", 1.0, 2.0, "placeholder"),
}


def write_json(tmp_path, name, data):
    path = tmp_path / name
    path.write_text(json.dumps(data), encoding="utf-8")
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
        "path": "buy_retail",
    }
    base.update(overrides)
    return base


def make_item(**overrides):
    base = raw_item(
        id="m",
        low=0,
        high=0,
        status="estimate",
        path="make",
        make={"inputs": {"pla": 0.1}, "waste_high": 1.2},
    )
    base.update(overrides)
    return base


def small_catalog(tmp_path, extra=()):
    items = [
        raw_item(id="a", low=10, high=20),
        raw_item(id="b", low=5, high=5, qty=2, status="estimate", path="buy_bulk"),
        raw_item(id="c", low=3, high=8, status="placeholder"),
        raw_item(id="d", low=0, high=0, status="unpriced", path="buy_bulk"),
        raw_item(id="opt", low=50, high=60, optional=True),
        *extra,
    ]
    return load_catalog(write_json(tmp_path, "catalog.json", {"items": items}), MATS)


# ---- shipped data -----------------------------------------------------------

def test_shipped_materials_load_with_valid_statuses():
    materials = load_materials(DEFAULT_MATERIALS)
    assert materials["pla_per_kg"].low == pytest.approx(8.55)
    assert {m.status for m in materials.values()} <= {
        "snapshot", "official", "estimate", "placeholder", "owned", "purchased", "unpriced",
    }


def test_shipped_catalog_loads_and_every_make_input_exists():
    materials = load_materials(DEFAULT_MATERIALS)
    catalog = load_catalog(DEFAULT_CATALOG, materials)
    assert "fc_pix32_v6" in catalog
    assert catalog["frame_printed_petg"].path == "make"


def test_shipped_passes_resolve_in_order():
    materials = load_materials(DEFAULT_MATERIALS)
    catalog = load_catalog(DEFAULT_CATALOG, materials)
    _, raw = load_passes(DEFAULT_PASSES)
    assert [p.id for p in resolve(catalog, raw)] == [
        "pass0_retail_autopilot",
        "pass1_shop_smart",
        "pass2_print_structure",
        "pass3_bench_first",
        "pass4_pixel_onboard",
        "pass5_made_tag",
        "pass6_diy_motor_rnd",
        "pass7_owned_pipeline",
        "pass8_own_most",
        "pass9_own_most_target_motors",
    ]


def test_each_shipped_pass_points_at_its_base():
    materials = load_materials(DEFAULT_MATERIALS)
    catalog = load_catalog(DEFAULT_CATALOG, materials)
    _, raw = load_passes(DEFAULT_PASSES)
    passes = {p.id: p for p in resolve(catalog, raw)}
    assert passes["pass0_retail_autopilot"].based_on is None
    assert passes["pass4_pixel_onboard"].based_on == "pass2_print_structure"
    assert passes["pass5_made_tag"].based_on == "pass3_bench_first"
    assert passes["pass7_owned_pipeline"].based_on == "pass6_diy_motor_rnd"


def shipped_totals():
    materials = load_materials(DEFAULT_MATERIALS)
    catalog = load_catalog(DEFAULT_CATALOG, materials)
    budget, raw = load_passes(DEFAULT_PASSES)
    passes = {p.id: p for p in resolve(catalog, raw)}
    return {
        pid: totals(catalog, p.items, materials) for pid, p in passes.items()
    }, budget


def test_costs_fall_from_retail_to_the_bench_kit():
    t, _ = shipped_totals()
    assert t["pass0_retail_autopilot"].core_low > t["pass1_shop_smart"].core_low
    assert t["pass1_shop_smart"].core_low > t["pass2_print_structure"].core_low
    assert t["pass2_print_structure"].core_low > t["pass3_bench_first"].core_low


def test_bench_kit_fits_the_budget_at_low_prices():
    t, budget = shipped_totals()
    assert t["pass3_bench_first"].core_low <= budget


def test_made_tag_pass_fits_the_budget_at_both_ends():
    t, budget = shipped_totals()
    assert t["pass5_made_tag"].core_high <= budget


def test_made_tag_saves_little_because_gnss_and_antenna_dominate():
    t, _ = shipped_totals()
    saving = t["pass3_bench_first"].core_low - t["pass5_made_tag"].core_low
    assert 0 < saving < 5


def test_pixel_pass_costs_more_than_the_pi_and_camera_it_replaces():
    t, _ = shipped_totals()
    assert t["pass4_pixel_onboard"].core_low > t["pass2_print_structure"].core_low + 150


def test_a_flying_drone_is_far_over_budget():
    t, budget = shipped_totals()
    assert t["pass0_retail_autopilot"].core_low > 5 * budget


def test_optional_tello_is_kept_out_of_core_totals():
    t, _ = shipped_totals()
    assert t["pass3_bench_first"].optional_low == pytest.approx(79.0)
    assert t["pass3_bench_first"].core_low < 100


def test_bulk_esp32_chip_is_cheaper_than_the_retail_module_it_replaces():
    catalog = load_catalog(DEFAULT_CATALOG, load_materials(DEFAULT_MATERIALS))
    assert catalog["chip_esp32c3_mini1"].high < catalog["tag_ht_ct62"].low


def test_diy_motor_pass_counts_the_laser_cut_placeholder():
    t, _ = shipped_totals()
    assert t["pass6_diy_motor_rnd"].unpriced == 0  # the steel core is priced now
    assert t["pass6_diy_motor_rnd"].placeholders >= 1  # laser cutting is still a guess


def test_pass8_replaces_bought_control_hardware_with_made_designs():
    materials = load_materials(DEFAULT_MATERIALS)
    catalog = load_catalog(DEFAULT_CATALOG, materials)
    _, raw = load_passes(DEFAULT_PASSES)
    p8 = {p.id: p for p in resolve(catalog, raw)}["pass8_own_most"]
    for made in ("autopilot_board_own", "esc_4in1_own", "transmitter_own", "tag_battery_own"):
        assert made in p8.items
    for bought in ("fc_pix32_v5_used", "esc_4in1", "elrs_tx_radio", "tag_battery_board"):
        assert bought not in p8.items


def test_pass9_motor_target_is_cheaper_than_pass8():
    t, _ = shipped_totals()
    assert t["pass9_own_most_target_motors"].core_low < t["pass8_own_most"].core_low


def test_made_autopilot_board_is_far_cheaper_than_the_bought_one():
    materials = load_materials(DEFAULT_MATERIALS)
    catalog = load_catalog(DEFAULT_CATALOG, materials)
    low, high = unit_cost(catalog["autopilot_board_own"], materials)
    assert 0 < low < high < 149  # the used Pix32 v5 price in the catalog


# ---- made items and materials -----------------------------------------------

def test_unit_cost_sums_materials_and_applies_waste_to_high_only(tmp_path):
    catalog = small_catalog(tmp_path, extra=[make_item()])
    low, high = unit_cost(catalog["m"], MATS)
    assert low == pytest.approx(0.1 * 10.0)  # 0.1 kg at $10 per kg
    assert high == pytest.approx(0.1 * 20.0 * 1.2)  # waste allowance on the high end


def test_made_item_needs_inputs(tmp_path):
    path = write_json(tmp_path, "c.json", {"items": [make_item(make={"inputs": {}})]})
    with pytest.raises(ValueError, match="needs make.inputs"):
        load_catalog(path, MATS)


def test_made_item_cannot_carry_a_price(tmp_path):
    path = write_json(tmp_path, "c.json", {"items": [make_item(low=5, high=5)]})
    with pytest.raises(ValueError, match="costed from materials"):
        load_catalog(path, MATS)


def test_bought_item_cannot_carry_make_inputs(tmp_path):
    path = write_json(
        tmp_path,
        "c.json",
        {"items": [raw_item(make={"inputs": {"pla": 1}})]},
    )
    with pytest.raises(ValueError, match="only made items"):
        load_catalog(path, MATS)


def test_unknown_material_in_a_made_item_is_rejected(tmp_path):
    path = write_json(
        tmp_path,
        "c.json",
        {"items": [make_item(make={"inputs": {"gold": 1}})]},
    )
    with pytest.raises(ValueError, match="unknown material gold"):
        load_catalog(path, MATS)


def test_waste_below_one_is_rejected(tmp_path):
    path = write_json(
        tmp_path, "c.json", {"items": [make_item(make={"inputs": {"pla": 1}, "waste_high": 0.5})]}
    )
    with pytest.raises(ValueError, match="waste_high"):
        load_catalog(path, MATS)


def test_unknown_path_is_rejected(tmp_path):
    path = write_json(tmp_path, "c.json", {"items": [raw_item(path="borrow")]})
    with pytest.raises(ValueError, match="unknown path"):
        load_catalog(path, MATS)


def test_unknown_item_status_is_rejected(tmp_path):
    path = write_json(tmp_path, "c.json", {"items": [raw_item(status="guess")]})
    with pytest.raises(ValueError, match="unknown status"):
        load_catalog(path, MATS)


def test_unpriced_bought_item_with_a_price_is_rejected(tmp_path):
    path = write_json(tmp_path, "c.json", {"items": [raw_item(status="unpriced", low=5, high=5)]})
    with pytest.raises(ValueError, match="zero prices"):
        load_catalog(path, MATS)


def test_high_below_low_is_rejected(tmp_path):
    path = write_json(tmp_path, "c.json", {"items": [raw_item(low=20, high=10)]})
    with pytest.raises(ValueError, match="low <= high"):
        load_catalog(path, MATS)


def test_zero_quantity_is_rejected(tmp_path):
    path = write_json(tmp_path, "c.json", {"items": [raw_item(qty=0)]})
    with pytest.raises(ValueError, match="qty"):
        load_catalog(path, MATS)


def test_duplicate_item_ids_are_rejected(tmp_path):
    path = write_json(tmp_path, "c.json", {"items": [raw_item(id="x"), raw_item(id="x")]})
    with pytest.raises(ValueError, match="duplicate item"):
        load_catalog(path, MATS)


def test_unknown_fields_are_rejected(tmp_path):
    path = write_json(tmp_path, "c.json", {"items": [raw_item(colour="red")]})
    with pytest.raises(TypeError):
        load_catalog(path, MATS)


def test_material_status_and_price_rules(tmp_path):
    bad_status = write_json(tmp_path, "m1.json", {"materials": {"x": {"unit": "kg", "low": 1, "high": 2, "status": "guess"}}})
    with pytest.raises(ValueError, match="unknown status"):
        load_materials(bad_status)
    bad_range = write_json(tmp_path, "m2.json", {"materials": {"x": {"unit": "kg", "low": 3, "high": 2, "status": "snapshot"}}})
    with pytest.raises(ValueError, match="low <= high"):
        load_materials(bad_range)
    bad_unpriced = write_json(tmp_path, "m3.json", {"materials": {"x": {"unit": "kg", "low": 1, "high": 1, "status": "unpriced"}}})
    with pytest.raises(ValueError, match="zero prices"):
        load_materials(bad_unpriced)


def test_unpriced_material_makes_the_item_unpriced_and_placeholder_material_counts(tmp_path):
    catalog = small_catalog(
        tmp_path,
        extra=[
            make_item(id="u", make={"inputs": {"steel": 1}}),
            make_item(id="g", make={"inputs": {"guess": 1}}),
        ],
    )
    t = totals(catalog, ["u", "g"], MATS)
    assert t.unpriced == 1
    assert t.placeholders == 1


# ---- totals, shares, dependency -----------------------------------------------

def test_totals_split_core_optional_and_flags(tmp_path):
    catalog = small_catalog(tmp_path)
    t = totals(catalog, ["a", "b", "c", "d", "opt"], MATS)
    assert t.core_low == pytest.approx(10 + 2 * 5 + 3)
    assert t.core_high == pytest.approx(20 + 2 * 5 + 8)
    assert t.optional_low == pytest.approx(50)
    assert t.optional_high == pytest.approx(60)
    assert t.placeholders == 1
    assert t.unpriced == 1


def test_made_share_counts_only_made_and_salvaged_parts(tmp_path):
    made = make_item(id="m", make={"inputs": {"pla": 1}, "waste_high": 1.2})
    catalog = small_catalog(tmp_path, extra=[made])
    t = totals(catalog, ["a", "m"], MATS)
    # Midpoints: bought a = (10 + 20) / 2 = 15. Made m is 10 to 24 with waste on the high end, midpoint 17.
    assert made_share(t) == pytest.approx(17 / (17 + 15))


def test_dependency_flags_single_supplier_and_no_supplier(tmp_path):
    catalog = small_catalog(
        tmp_path,
        extra=[
            raw_item(id="single", path="buy_bulk", source="https://only-one.example/x"),
            raw_item(id="double", path="buy_bulk", source="https://a.example/x; https://b.example/y"),
            make_item(id="made"),
        ],
    )
    single, none = dependency(catalog, ["a", "b", "c", "d", "opt", "single", "double", "made"])
    assert "single" in single
    assert "b" in none  # bought with no source at all
    assert "a" in none  # retail item with no source listed
    assert "double" not in single and "double" not in none
    assert "made" not in single and "made" not in none
    assert "opt" not in single and "opt" not in none  # optional items are skipped


def test_supplier_hosts_ignores_text_that_is_not_a_url():
    assert supplier_hosts("Owner's purchase on Swappa (used marketplace)") == set()
    assert supplier_hosts("https://www.lcsc.com/a; https://lcsc.com/b") == {"lcsc.com"}


def test_companion_tiers_scale_with_the_tag_cost(tmp_path):
    items = [
        raw_item(id="tag1", category="companion_tag", low=10, high=20),
        raw_item(id="tag2", category="companion_tag", low=5, high=5, qty=2),
        raw_item(id="other", low=99, high=99),
    ]
    catalog = load_catalog(write_json(tmp_path, "c.json", {"items": items}), MATS)
    tiers = {t.name: t for t in companion_tiers(catalog, ["tag1", "tag2", "other"], MATS)}
    assert tiers["phone only"].high == 0
    assert tiers["phone + 1 tag"].low == pytest.approx(20)
    assert tiers["phone + 1 tag"].high == pytest.approx(30)
    assert tiers["phone + 2 tags"].low == pytest.approx(40)


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


# ---- reports -----------------------------------------------------------------

def test_report_names_each_pass_and_its_budget_status(tmp_path):
    catalog = small_catalog(tmp_path)
    raw = [
        {"id": "p0", "title": "first", "based_on": None, "add": ["a", "b"], "remove": []},
        {"id": "p1", "title": "second", "based_on": "p0", "add": [], "remove": ["b"]},
    ]
    text = report(catalog, resolve(catalog, raw), budget=15, materials=MATS)
    # p0: a (10 to 20) plus b twice (5 each): core 20 to 30, over a 15 budget.
    assert "core $20.00 to $30.00" in text
    assert "over budget" in text
    # p1 drops b: core 10 to 20. The low end fits 15, the high end does not.
    assert "core $10.00 to $20.00" in text
    assert "fits budget at low prices only" in text
    assert "change vs p0: -10.00 to -10.00" in text


def test_passes_markdown_has_one_row_per_pass(tmp_path):
    catalog = small_catalog(tmp_path)
    raw = [
        {"id": "p0", "title": "first", "based_on": None, "add": ["a"], "remove": []},
        {"id": "p1", "title": "second", "based_on": "p0", "add": ["b"], "remove": []},
    ]
    md = passes_markdown(catalog, resolve(catalog, raw), budget=100, materials=MATS)
    rows = [line for line in md.splitlines() if line.startswith("| p")]
    assert len(rows) == 2
    assert "none (starting point)" in md


def test_markdown_lists_every_item_with_path_and_links(tmp_path):
    items = [raw_item(id="x", source="https://example.com/a; https://shop.example.org/b")]
    catalog = load_catalog(write_json(tmp_path, "c.json", {"items": items}), MATS)
    md = catalog_markdown(catalog, MATS)
    assert "| A | misc | buy_retail | 1 | 10.00 to 20.00 | snapshot |" in md
    assert "[example.com](https://example.com/a)" in md
    assert "[shop.example.org](https://shop.example.org/b)" in md


def test_cli_prints_every_pass_and_the_dependency_check(capsys):
    assert main([]) == 0
    out = capsys.readouterr().out
    assert "pass0_retail_autopilot" in out and "pass7_owned_pipeline" in out
    assert "Dependency check" in out
    assert "Companion tiers" in out


def test_cli_markdown_modes(capsys):
    assert main(["--markdown"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("| Item | Category | Path")
    assert "Holybro Pix32 v6" in out
    assert main(["--passes-markdown"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("| Pass | Based on")
    assert "pass7_owned_pipeline" in out


# ---- price dates ------------------------------------------------------------

def test_freshness_rules_use_month_precision_and_a_12_month_window():
    from follow_me.bom import freshness

    assert freshness("") == "undated"
    assert freshness("2026") == "year only"
    assert freshness("2026-10") == "fresh"
    assert freshness("2026-10-10") == "fresh"
    assert freshness("2025-11") == "fresh"  # 343 days before the cutoff
    assert freshness("2025-09") == "stale"  # more than a year before the cutoff
    assert freshness("2027-01") == "future"


def test_bad_date_formats_are_rejected(tmp_path):
    path = write_json(tmp_path, "m.json", {"materials": {"x": {"unit": "kg", "low": 1, "high": 2, "status": "snapshot", "checked": "10/2026"}}})
    with pytest.raises(ValueError, match="checked date"):
        load_materials(path)


def test_esp32_price_is_dated_today_and_fresh():
    from follow_me.bom import freshness

    materials = load_materials(DEFAULT_MATERIALS)
    catalog = load_catalog(DEFAULT_CATALOG, materials)
    assert catalog["chip_esp32c3_mini1"].checked == "2026-10-10"
    assert freshness(catalog["chip_esp32c3_mini1"].checked) == "fresh"


def test_audit_lists_each_bought_item_and_each_material_once():
    from follow_me.bom import price_rows

    materials = load_materials(DEFAULT_MATERIALS)
    catalog = load_catalog(DEFAULT_CATALOG, materials)
    rows = price_rows(catalog, materials)
    keys = [(r.kind, r.key) for r in rows]
    assert len(keys) == len(set(keys))
    assert ("material", "esp32c3_mini1_each") in keys
    assert ("item", "fc_pix32_v5_used") in keys
    assert ("item", "pixel_8a_purchased") not in keys  # owner's purchase, not a quote


def test_date_summary_counts_sourced_fresh_and_placeholders(tmp_path):
    from follow_me.bom import PriceRow, date_summary

    rows = [
        PriceRow("item", "a", "a", "snapshot", 1, 2, "2026-10-10", "fresh"),
        PriceRow("item", "b", "b", "snapshot", 1, 2, "", "undated"),
        PriceRow("item", "c", "c", "placeholder", 1, 2, "", "undated"),
        PriceRow("material", "d", "a", "estimate", 1, 2, "", "undated"),
    ]
    assert date_summary(rows) == (1, 2, 1)


def test_cli_audit_mode_prints_the_summary(capsys):
    assert main(["--audit"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("| Kind | Key")
    assert "Sourced prices dated in the last 12 months" in out
