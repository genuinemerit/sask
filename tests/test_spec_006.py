"""SPEC-006 tests — frozen orbital initial conditions.

Covers:
  - All 15 bodies present and fully populated in body_data.toml
  - All required fields from body_template.toml are present on each body
  - Dynamical field ranges: epoch_offset and node in [0.0, 1.0),
    inclination_deg in [1.0, 8.0] degrees for randomly-drawn bodies
  - Lore overrides: Lethra offset = (Aesthra offset + 0.5) mod 1.0,
    Zehembra inclination <= 1.5 degrees
  - Dramond sidereal_period_days == 500
  - Reproducibility: re-drawing with the recorded seed gives identical values
  - observation_data.toml carries obliquity 23.44, observer lat 35.47,
    Gavor epoch_offset 0.0, Gavor semi_major_axis 1.0
  - generate_orbital_conditions has no Flask import (tool layer purity)
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from generate_orbital_conditions import SEED, draw_dynamical_fields

CONFIG_DIR = Path(__file__).parent.parent / "config"
BODY_DATA = CONFIG_DIR / "body_data.toml"
BODY_TEMPLATE = CONFIG_DIR / "body_template.toml"
OBS_DATA = CONFIG_DIR / "observation_data.toml"
GENERATOR_SRC = (
    Path(__file__).parent.parent / "tools" / "generate_orbital_conditions.py"
)

EXPECTED_BODY_COUNT = 15
REQUIRED_FIELDS = frozenset(
    {
        "name",
        "type",
        "sidereal_period_days",
        "epoch_offset",
        "inclination_deg",
        "node",
        "diameter_km",
        "albedo",
        "apparent_color",
    }
)


def _load_bodies() -> list[dict]:
    with BODY_DATA.open("rb") as fh:
        return tomllib.load(fh)["body"]


def _body_map() -> dict[str, dict]:
    return {b["name"]: b for b in _load_bodies()}


# ── Schema completeness ────────────────────────────────────────────────────────


def test_all_fifteen_bodies_present():
    assert len(_load_bodies()) == EXPECTED_BODY_COUNT


def test_body_names_are_unique():
    names = [b["name"] for b in _load_bodies()]
    assert len(names) == len(set(names))


@pytest.mark.parametrize("field", sorted(REQUIRED_FIELDS))
def test_all_bodies_have_required_field(field):
    for body in _load_bodies():
        assert field in body, f"{body['name']} missing required field '{field}'"


def test_planets_have_semi_major_axis():
    for body in _load_bodies():
        if body["type"] == "planet":
            assert "semi_major_axis" in body, (
                f"planet {body['name']} missing semi_major_axis"
            )


def test_types_are_moon_or_planet():
    for body in _load_bodies():
        assert body["type"] in {"moon", "planet"}, (
            f"{body['name']} has invalid type {body['type']!r}"
        )


# ── Field ranges ───────────────────────────────────────────────────────────────


def test_epoch_offsets_in_unit_interval():
    for body in _load_bodies():
        v = body["epoch_offset"]
        assert 0.0 <= v < 1.0, f"{body['name']} epoch_offset {v} out of [0.0, 1.0)"


def test_nodes_in_unit_interval():
    for body in _load_bodies():
        v = body["node"]
        assert 0.0 <= v < 1.0, f"{body['name']} node {v} out of [0.0, 1.0)"


def test_random_inclinations_in_draw_range():
    bodies = _load_bodies()
    excluded = {"Zehembra"}  # hand-set override
    for body in bodies:
        if body["name"] in excluded:
            continue
        v = body["inclination_deg"]
        assert 1.0 <= v <= 8.0, f"{body['name']} inclination_deg {v} outside [1.0, 8.0]"


# ── Lore overrides ─────────────────────────────────────────────────────────────


def test_zehembra_inclination_is_low():
    bm = _body_map()
    assert bm["Zehembra"]["inclination_deg"] <= 1.5, (
        "Zehembra inclination should be <= 1.5 degrees"
    )


def test_lethra_offset_is_aesthra_plus_half():
    bm = _body_map()
    expected = (bm["Aesthra"]["epoch_offset"] + 0.5) % 1.0
    actual = bm["Lethra"]["epoch_offset"]
    assert abs(actual - expected) < 1e-9, (
        f"Lethra offset {actual} != Aesthra offset + 0.5 mod 1.0 ({expected})"
    )


def test_dramond_period_is_500_days():
    bm = _body_map()
    assert bm["Dramond"]["sidereal_period_days"] == 500


# ── Reproducibility ────────────────────────────────────────────────────────────


def test_redraw_with_recorded_seed_matches_frozen_values():
    """Re-running draw_dynamical_fields with the provenance seed yields
    the same epoch_offset, inclination_deg, and node for every body.

    Values are stored rounded to 6 decimal places, so the comparison
    rounds the redrawn value to the same precision before comparing.
    """
    bodies = _load_bodies()
    redrawn = draw_dynamical_fields(bodies, SEED)
    for body in bodies:
        name = body["name"]
        for field in ("epoch_offset", "inclination_deg", "node"):
            assert round(redrawn[name][field], 6) == pytest.approx(
                body[field], abs=1e-9
            ), f"{name}.{field}: frozen {body[field]} != redrawn {redrawn[name][field]}"


def test_provenance_seed_matches_generator_constant():
    with BODY_DATA.open("rb") as fh:
        raw = tomllib.load(fh)
    assert "provenance" in raw, "body_data.toml missing [provenance] block"
    assert raw["provenance"]["seed"] == SEED


# ── Observation data ───────────────────────────────────────────────────────────


def test_obliquity_is_23_44():
    with OBS_DATA.open("rb") as fh:
        obs = tomllib.load(fh)
    assert obs["observation"]["obliquity_deg"] == pytest.approx(23.44)


def test_observer_latitude_is_35_47():
    with OBS_DATA.open("rb") as fh:
        obs = tomllib.load(fh)
    assert obs["observation"]["observer_latitude_deg"] == pytest.approx(35.47)


def test_gavor_epoch_offset_is_zero():
    with OBS_DATA.open("rb") as fh:
        obs = tomllib.load(fh)
    assert obs["gavor"]["epoch_offset"] == pytest.approx(0.0)


def test_gavor_semi_major_axis_is_unit():
    with OBS_DATA.open("rb") as fh:
        obs = tomllib.load(fh)
    assert obs["gavor"]["semi_major_axis"] == pytest.approx(1.0)


# ── Layer purity ───────────────────────────────────────────────────────────────


def test_generator_has_no_flask_import():
    src = GENERATOR_SRC.read_text(encoding="utf-8")
    assert "flask" not in src.lower(), (
        "generate_orbital_conditions.py must not import Flask"
    )
