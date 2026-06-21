"""Shared performance-test grid and budgets (REQ-OPS-010, SPEC-018).

Single source of truth for the ephemeris sweep grid and the provisional
performance budgets, read by both the Layer 1 pytest-benchmark suite
(tests/perf/) and the Layer 2 HTTP harness (tools/perf_http.py).
"""

from __future__ import annotations

from dataclasses import dataclass

ONE_DAY_PULSES = 86_400


@dataclass(frozen=True)
class GridPoint:
    """One (range, step) point in the ephemeris sweep grid."""

    range_label: str
    step_label: str
    range_pulses: int
    step_pulses: int


PROFILES: tuple[str, ...] = ("scribal", "kinematic")

FIVE_MIN_PULSES = 300
ONE_HOUR_PULSES = 3_600

EPHEMERIS_GRID: tuple[GridPoint, ...] = tuple(
    GridPoint(
        range_label=range_label,
        step_label=step_label,
        range_pulses=range_days * ONE_DAY_PULSES,
        step_pulses=step_pulses,
    )
    for range_days, range_label in ((1, "1day"), (7, "7day"), (30, "30day"))
    for step_pulses, step_label in (
        (FIVE_MIN_PULSES, "5min"),
        (ONE_HOUR_PULSES, "1hour"),
    )
)

WORST_CASE: GridPoint = next(
    gp for gp in EPHEMERIS_GRID if gp.range_label == "30day" and gp.step_label == "5min"
)

# Provisional budgets from REQ-OPS-010, re-validated once a local baseline
# is recorded (and again on the deployment target).
BUDGETS = {
    "interactive_ms": 500.0,
    "ephemeris_worst_case_s": (3.0, 5.0),
}
