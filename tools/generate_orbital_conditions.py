"""One-time generator: freeze orbital initial conditions into config/body_data.toml.

Draws epoch_offset, inclination_deg, and node for all fifteen celestial bodies
from a single recorded seed and writes them into body_data.toml in place.

This script is run ONCE on the VM; the engine reads the frozen config and never
invokes this generator. Re-running with the same SEED produces identical output.

Usage:
    python3 tools/generate_orbital_conditions.py
"""

from __future__ import annotations

import random
import sys
import tomllib
from datetime import date
from pathlib import Path

# ── Constants ──────────────────────────────────────────────────────────────────

SEED = 20260604  # recorded seed; never change; written to provenance block
GENERATOR_VERSION = "1.0"

INCLINATION_MIN = 1.0  # degrees; lower bound for random draw
INCLINATION_MAX = 8.0  # degrees; upper bound for random draw
ZEHEMBRA_INCLINATION = 1.0  # hand-set low; eclipses more often (lore requirement)

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
BODY_DATA = CONFIG_DIR / "body_data.toml"


# ── Draw logic (importable for reproducibility tests) ─────────────────────────


def draw_dynamical_fields(bodies: list[dict], seed: int) -> dict[str, dict]:
    """Draw epoch_offset, inclination_deg, node for each body in file order.

    Uses a local Random instance (no global state mutation). The draw order is
    load-bearing for reproducibility: one call per field per body, in file order.

    Overrides applied after the full draw so the RNG sequence is unchanged:
      - Lethra: epoch_offset = (Aesthra epoch_offset + 0.5) % 1.0
      - Zehembra: inclination_deg = ZEHEMBRA_INCLINATION (~1 degree)

    Returns {body_name: {field_name: value}}.
    """
    rng = random.Random(seed)
    result: dict[str, dict] = {}
    for body in bodies:
        name = body["name"]
        result[name] = {
            "epoch_offset": rng.random(),
            "inclination_deg": rng.uniform(INCLINATION_MIN, INCLINATION_MAX),
            "node": rng.random(),
        }
    result["Lethra"]["epoch_offset"] = (result["Aesthra"]["epoch_offset"] + 0.5) % 1.0
    result["Zehembra"]["inclination_deg"] = ZEHEMBRA_INCLINATION
    return result


# ── TOML serialiser ───────────────────────────────────────────────────────────

# Field output order per body type; absent optional fields are silently skipped.
_MOON_FIELDS = (
    "name",
    "type",
    "sidereal_period_days",
    "epoch_offset",
    "inclination_deg",
    "node",
    "diameter_km",
    "albedo",
    "apparent_color",
    "rotation_type",
    "rotation_period_days",
    "distance_km",
    "notes",
)

_PLANET_FIELDS = (
    "name",
    "type",
    "sidereal_period_days",
    "semi_major_axis",
    "epoch_offset",
    "inclination_deg",
    "node",
    "diameter_km",
    "albedo",
    "apparent_color",
    "rings",
    "visible_moons",
    "notes",
)


def _toml_value(v: object) -> str:
    """Serialise a Python scalar to a TOML literal."""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        r = repr(round(v, 6))
        if "." not in r and "e" not in r:
            r += ".0"
        return r
    if isinstance(v, str):
        escaped = v.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    raise TypeError(f"Cannot serialise {type(v).__name__!r} to TOML")


def _write_body_data(
    bodies: list[dict],
    dynamical: dict[str, dict],
    out_path: Path,
) -> None:
    """Write the completed body_data.toml with provenance block."""
    lines: list[str] = []

    lines.append("[provenance]")
    lines.append(f"seed              = {SEED}")
    lines.append(f'generator_version = "{GENERATOR_VERSION}"')
    lines.append(f'generated_date    = "{date.today()}"')
    lines.append("")

    for body in bodies:
        merged = {**body, **dynamical[body["name"]]}
        field_order = _MOON_FIELDS if body["type"] == "moon" else _PLANET_FIELDS
        lines.append("[[body]]")
        for field in field_order:
            if field in merged:
                lines.append(f"{field} = {_toml_value(merged[field])}")
        lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")


# ── Entry point ────────────────────────────────────────────────────────────────


def main() -> int:
    if not BODY_DATA.exists():
        print(f"ERROR: {BODY_DATA} not found", file=sys.stderr)
        return 1

    with BODY_DATA.open("rb") as fh:
        raw = tomllib.load(fh)

    bodies: list[dict] = raw.get("body", [])
    if len(bodies) != 15:
        print(f"ERROR: expected 15 bodies, found {len(bodies)}", file=sys.stderr)
        return 1

    dynamical = draw_dynamical_fields(bodies, SEED)
    _write_body_data(bodies, dynamical, BODY_DATA)

    print(f"Wrote {BODY_DATA}")
    print(f"Seed: {SEED}   Bodies: {len(bodies)}")
    print()
    for name, fields in dynamical.items():
        print(
            f"  {name:12s}  offset={fields['epoch_offset']:.6f}"
            f"  incl={fields['inclination_deg']:.4f}°"
            f"  node={fields['node']:.6f}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
