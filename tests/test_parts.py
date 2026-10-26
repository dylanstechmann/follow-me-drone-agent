"""Printable parts: the print cards and the OpenSCAD parameters the website turns into sliders."""

import json

import pytest

from follow_me import bom
from follow_me.parts import CAD, load_parts, parse_params

SAMPLE = """// A header comment that labels nothing.

/* [Size] */
// Length (mm)
length = 80; // [40:5:120]
count = 3; // [1:5]
// Finish
finish = "matte"; // [matte, gloss]

/* [Hidden] */
secret = 1; // [0:1:2]
"""


def test_parse_params_reads_groups_labels_ranges_and_choices():
    params = parse_params(SAMPLE)
    assert [p.name for p in params] == ["length", "count", "finish"]
    length, count, finish = params
    assert (length.group, length.label, length.default) == ("Size", "Length (mm)", 80)
    assert (length.min, length.step, length.max) == (40, 5, 120)
    assert count.label == "count" and count.step == 1  # no comment above, and [min:max] steps by 1
    assert finish.choices == ("matte", "gloss") and finish.default == "matte"


def test_parse_params_stops_at_the_first_module():
    params = parse_params("a = 1; // [0:1:5]\nmodule m() {}\nb = 2; // [0:1:5]\n")
    assert [p.name for p in params] == ["a"]


def test_shipped_parts_load_and_every_slider_default_is_valid():
    materials = bom.load_materials()
    catalog = bom.load_catalog(bom.DEFAULT_CATALOG, materials)
    parts = load_parts(CAD, catalog)
    assert {p.id for p in parts} == {"flex_test_bars", "fit_gauge", "thrust_stand", "tag_enclosure"}
    for part in parts:
        assert part.params, part.id
        assert part.status == "unprinted", "nothing has been printed yet"
        assert (CAD / part.file).is_file()
    assert {p.catalog_item for p in parts if p.catalog_item} == {"thrust_stand_make", "tag_enclosure_printed"}


def test_every_scad_file_has_a_print_card_and_says_it_is_untested():
    listed = {p.file for p in load_parts()}
    on_disk = {p.name for p in CAD.glob("*.scad")}
    assert on_disk == listed
    for name in on_disk:
        assert "Unprinted and untested" in (CAD / name).read_text(encoding="utf-8"), name


def _write(tmp_path, card_changes=None, scad="w = 2; // [1:1:5]\ncube(w);\n"):
    card = {
        "id": "p", "file": "p.scad", "title": "P", "purpose": "x", "gate": "x", "material": "PLA",
        "layer_mm": 0.2, "walls": 3, "infill": "20 percent", "orientation": "x", "supports": "None",
        "test": "x", "safety": "x", "catalog_item": None, "status": "unprinted",
    }
    card.update(card_changes or {})
    (tmp_path / "p.scad").write_text(scad, encoding="utf-8")
    (tmp_path / "parts.json").write_text(json.dumps({"parts": [card]}), encoding="utf-8")
    return tmp_path


def test_a_printed_part_needs_its_measurements(tmp_path):
    with pytest.raises(ValueError, match="measured"):
        load_parts(_write(tmp_path, {"status": "printed"}))
    measured = {"grams": 31.5, "minutes": 95, "material": "PETG", "date": "2026-11-02"}
    parts = load_parts(_write(tmp_path, {"status": "printed", "measured": measured}))
    assert parts[0].measured["grams"] == 31.5
    with pytest.raises(ValueError, match="date"):
        load_parts(_write(tmp_path, {"status": "tested", "measured": {**measured, "date": "November"}}))


@pytest.mark.parametrize("changes, scad, message", [
    ({"status": "flown"}, None, "status"),
    ({"colour": "red"}, None, "unknown"),
    ({"file": "missing.scad"}, None, "missing OpenSCAD file"),
    ({"catalog_item": "no_such_item"}, None, "unknown catalog item"),
    ({}, "w = 9; // [1:1:5]\n", "outside"),
    ({}, "w = 2.25; // [1:0.5:5]\n", "steps"),
    ({}, "cube(2);\n", "no Customizer parameters"),
])
def test_bad_cards_and_parameters_are_rejected(tmp_path, changes, scad, message):
    cad = _write(tmp_path, changes, **({"scad": scad} if scad else {}))
    with pytest.raises(ValueError, match=message):
        load_parts(cad, catalog={})
