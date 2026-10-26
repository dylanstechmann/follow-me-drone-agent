"""Printable parts: OpenSCAD sources in cad/ and their print cards in cad/parts.json.

Each .scad file starts with its adjustable parameters in OpenSCAD's Customizer
format, which the website turns into sliders:

  /* [Group] */
  // Label shown next to the slider
  name = 10; // [min:step:max]

The parameters end at a /* [Hidden] */ group or at the first module. Every part
is unprinted and untested until it is printed and measured; then its card
records the measured grams and minutes, which replace the catalog's estimate.

  PYTHONPATH=src python3 -m follow_me.parts     # list the parts and their parameters
"""

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CAD = ROOT / "cad"
STATUSES = ("unprinted", "printed", "tested")
CARD_FIELDS = (
    "id", "file", "title", "purpose", "gate", "material", "layer_mm", "walls", "infill",
    "orientation", "supports", "test", "safety", "catalog_item", "status",
)
MEASURED_FIELDS = ("grams", "minutes", "material", "date")
# Typical filament densities in g/cm3, for the solid-volume mass on the website.
DENSITY = {"PLA": 1.24, "PETG": 1.27}

_GROUP = re.compile(r"^/\*\s*\[(.+?)\]\s*\*/$")
_PARAM = re.compile(r"^([A-Za-z_]\w*)\s*=\s*([^;]+?)\s*;\s*//\s*\[([^\]]*)\]$")
_COMMENT = re.compile(r"^//\s?(.*)$")
_NUMBER = re.compile(r"^-?\d+(\.\d+)?$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass(frozen=True)
class Param:
    name: str
    label: str
    group: str
    default: float | int | bool | str
    min: float | None = None
    max: float | None = None
    step: float | None = None
    choices: tuple[str, ...] = ()


@dataclass(frozen=True)
class Part:
    id: str
    file: str
    title: str
    purpose: str
    gate: str
    material: str
    layer_mm: float
    walls: int
    infill: str
    orientation: str
    supports: str
    test: str
    safety: str
    catalog_item: str | None
    status: str
    params: tuple[Param, ...]
    measured: dict | None = None


def _value(text: str) -> float | int | bool | str:
    if text in ("true", "false"):
        return text == "true"
    if text.startswith('"'):
        return json.loads(text)
    if not _NUMBER.match(text):
        raise ValueError(f"default {text!r} is not a number, true, false or a quoted string")
    return float(text) if "." in text else int(text)


def _param(name: str, label: str, group: str, value: str, spec: str) -> Param:
    default = _value(value.strip())
    pieces = [p.strip() for p in spec.split(":")]
    if len(pieces) in (2, 3) and all(_NUMBER.match(p) for p in pieces):
        numbers = [float(p) for p in pieces]
        step = numbers[1] if len(numbers) == 3 else 1.0
        return Param(name, label, group, default, numbers[0], numbers[-1], step)
    return Param(name, label, group, default, choices=tuple(c.strip() for c in spec.split(",")))


def parse_params(source: str) -> list[Param]:
    """The Customizer parameters at the top of an OpenSCAD file, in order."""
    params: list[Param] = []
    group = "Parameters"
    label = ""
    for raw in source.splitlines():
        line = raw.strip()
        if line.startswith(("module ", "function ")):
            break
        group_match = _GROUP.match(line)
        if group_match:
            if group_match.group(1).strip().lower() == "hidden":
                break
            group, label = group_match.group(1).strip(), ""
            continue
        param_match = _PARAM.match(line)
        if param_match:
            name, value, spec = param_match.groups()
            params.append(_param(name, label or name, group, value, spec))
            label = ""
            continue
        comment = _COMMENT.match(line)
        label = comment.group(1).strip() if comment else ""  # a comment right above a parameter labels it
    return params


def _check_param(part_id: str, p: Param) -> None:
    where = f"{part_id}: parameter {p.name}"
    if p.choices:
        if str(p.default) not in p.choices:
            raise ValueError(f"{where}: default is not one of its choices")
        return
    if isinstance(p.default, bool) or not isinstance(p.default, (int, float)):
        raise ValueError(f"{where}: a slider needs a number")
    if not (p.step and p.step > 0 and p.min < p.max):
        raise ValueError(f"{where}: needs min < max and a positive step")
    if not p.min <= p.default <= p.max:
        raise ValueError(f"{where}: default {p.default} is outside [{p.min}, {p.max}]")
    steps = (p.default - p.min) / p.step
    if abs(steps - round(steps)) > 1e-6:
        raise ValueError(f"{where}: default {p.default} is not on the slider's {p.step} steps")


def _check_measured(part_id: str, measured: dict | None) -> None:
    if not isinstance(measured, dict) or set(measured) < set(MEASURED_FIELDS):
        raise ValueError(f"{part_id}: a printed part needs measured {', '.join(MEASURED_FIELDS)}")
    if not _DATE.match(str(measured["date"])):
        raise ValueError(f"{part_id}: measured date must be YYYY-MM-DD")
    for key in ("grams", "minutes"):
        if isinstance(measured[key], bool) or not isinstance(measured[key], (int, float)) or measured[key] <= 0:
            raise ValueError(f"{part_id}: measured {key} must be a positive number")


def load_parts(cad: Path = CAD, catalog: dict | None = None) -> list[Part]:
    """Load and check the print cards and each part's parameters."""
    data = json.loads((cad / "parts.json").read_text(encoding="utf-8"))
    parts: list[Part] = []
    for raw in data["parts"]:
        unknown = set(raw) - set(CARD_FIELDS) - {"measured"}
        missing = set(CARD_FIELDS) - set(raw)
        if unknown or missing:
            raise ValueError(f"part {raw.get('id')}: unknown {sorted(unknown)}, missing {sorted(missing)}")
        part_id = raw["id"]
        if any(p.id == part_id for p in parts):
            raise ValueError(f"duplicate part {part_id}")
        if raw["status"] not in STATUSES:
            raise ValueError(f"{part_id}: status must be one of {STATUSES}")
        if raw["status"] != "unprinted":
            _check_measured(part_id, raw.get("measured"))
        if catalog is not None and raw["catalog_item"] and raw["catalog_item"] not in catalog:
            raise ValueError(f"{part_id}: unknown catalog item {raw['catalog_item']}")
        source = cad / raw["file"]
        if not source.is_file() or source.suffix != ".scad":
            raise ValueError(f"{part_id}: missing OpenSCAD file {raw['file']}")
        params = tuple(parse_params(source.read_text(encoding="utf-8")))
        if not params:
            raise ValueError(f"{part_id}: no Customizer parameters found")
        for p in params:
            _check_param(part_id, p)
        parts.append(Part(**{k: raw[k] for k in CARD_FIELDS}, params=params, measured=raw.get("measured")))
    return parts


def main(argv: list[str]) -> int:
    for part in load_parts():
        print(f"{part.id}  {part.title}  [{part.status}]  {part.file}")
        for p in part.params:
            limits = f"{p.min:g} to {p.max:g}" if p.choices == () else ", ".join(p.choices)
            print(f"    {p.name} = {p.default}  ({limits})  {p.label}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
