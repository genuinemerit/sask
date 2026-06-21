#!/usr/bin/env python3
"""SPEC-018 Layer 2 — HTTP timing harness against a live, single-worker gunicorn.

Standard library only. Targets an already-running gunicorn instance (see
tools/run_perf.sh for the launch line) and times the four interactive pages
plus the full ephemeris grid (preview and, for the worst case, download).
Writes a dated JSON result file under tests/results/perf/ and prints a
pass/fail summary against the REQ-OPS-010 budgets.

Usage:
    PYTHONPATH=src .venv/bin/python3 tools/perf_http.py [--base-url URL]
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
import urllib.request
from datetime import date
from pathlib import Path

from perf_config import BUDGETS, EPHEMERIS_GRID, PROFILES, WORST_CASE

from sask.config_loader import load_config

PROJECT_ROOT = Path(__file__).parent.parent
REAL_CONFIG = PROJECT_ROOT / "config"
RESULTS_DIR = PROJECT_ROOT / "tests" / "results" / "perf"

INTERACTIVE_PAGES = ("/", "/sky", "/moons", "/planets")


def _timed_get(url: str) -> tuple[float, int, int]:
    """Return (elapsed_seconds, status_code, payload_bytes) for one GET."""
    start = time.perf_counter()
    with urllib.request.urlopen(url) as resp:
        status = resp.status
        body = resp.read()
    elapsed = time.perf_counter() - start
    return elapsed, status, len(body)


def _measure(label: str, url: str, *, warmup: int, repeats: int) -> dict:
    for _ in range(warmup):
        _timed_get(url)

    timings: list[float] = []
    status = 0
    payload_bytes = 0
    for _ in range(repeats):
        elapsed, status, payload_bytes = _timed_get(url)
        timings.append(elapsed)

    return {
        "label": label,
        "url": url,
        "status": status,
        "repeats": repeats,
        "median_s": statistics.median(timings),
        "min_s": min(timings),
        "max_s": max(timings),
        "payload_bytes": payload_bytes,
    }


def _run_sweep(base_url: str, story_now: int, *, warmup: int, repeats: int) -> dict:
    interactive = [
        _measure(
            f"interactive_{page.strip('/') or 'index'}",
            f"{base_url}{page}?pulse={story_now}",
            warmup=warmup,
            repeats=repeats,
        )
        for page in INTERACTIVE_PAGES
    ]

    ephemeris_preview = [
        _measure(
            f"ephemeris_preview_{gp.range_label}_{gp.step_label}_{profile}",
            f"{base_url}/ephemeris?start_pulse={story_now}"
            f"&end_pulse={story_now + gp.range_pulses}"
            f"&step_minutes={gp.step_pulses // 60}&profile={profile}",
            warmup=warmup,
            repeats=repeats,
        )
        for gp in EPHEMERIS_GRID
        for profile in PROFILES
    ]

    ephemeris_download_worst_case = [
        _measure(
            f"ephemeris_download_worst_case_{profile}",
            f"{base_url}/ephemeris/download?start={story_now}"
            f"&end={story_now + WORST_CASE.range_pulses}"
            f"&step={WORST_CASE.step_pulses}&profile={profile}",
            warmup=warmup,
            repeats=repeats,
        )
        for profile in PROFILES
    ]

    return {
        "interactive": interactive,
        "ephemeris_preview": ephemeris_preview,
        "ephemeris_download_worst_case": ephemeris_download_worst_case,
    }


def _check_budgets(results: dict) -> list[dict]:
    checks = []
    interactive_budget_ms = BUDGETS["interactive_ms"]
    for entry in results["interactive"]:
        median_ms = entry["median_s"] * 1000
        checks.append(
            {
                "label": entry["label"],
                "median_ms": round(median_ms, 1),
                "budget_ms": interactive_budget_ms,
                "pass": median_ms <= interactive_budget_ms,
            }
        )

    lower_s, upper_s = BUDGETS["ephemeris_worst_case_s"]
    for entry in results["ephemeris_download_worst_case"]:
        checks.append(
            {
                "label": entry["label"],
                "median_s": round(entry["median_s"], 3),
                "budget_s": [lower_s, upper_s],
                "pass": entry["median_s"] <= upper_s,
            }
        )

    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    config = load_config(REAL_CONFIG)
    story_now = config.timeline.story_now_pulse

    print(f"Targeting {args.base_url} (story_now pulse={story_now})")
    sweep = _run_sweep(
        args.base_url, story_now, warmup=args.warmup, repeats=args.repeats
    )
    budget_checks = _check_budgets(sweep)

    out = {
        "timestamp": date.today().isoformat(),
        "base_url": args.base_url,
        "warmup": args.warmup,
        "repeats": args.repeats,
        **sweep,
        "budget_checks": budget_checks,
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = (
        Path(args.out) if args.out else RESULTS_DIR / f"{out['timestamp']}_http.json"
    )
    out_path.write_text(json.dumps(out, indent=2))

    print(f"\nWrote results to {out_path}\n")
    print(f"{'label':45s} {'median_ms':>10s} {'min_ms':>10s} {'max_ms':>10s}")
    for entry in sweep["interactive"] + sweep["ephemeris_preview"]:
        print(
            f"{entry['label']:45s} {entry['median_s'] * 1000:10.1f} "
            f"{entry['min_s'] * 1000:10.1f} {entry['max_s'] * 1000:10.1f}"
        )
    for entry in sweep["ephemeris_download_worst_case"]:
        print(
            f"{entry['label']:45s} {entry['median_s'] * 1000:10.1f} "
            f"{entry['min_s'] * 1000:10.1f} {entry['max_s'] * 1000:10.1f} "
            f"({entry['payload_bytes']:,} bytes)"
        )

    print("\nBudget checks:")
    all_pass = True
    for check in budget_checks:
        status = "PASS" if check["pass"] else "FAIL"
        all_pass &= check["pass"]
        budget = check.get("budget_ms", check.get("budget_s"))
        measured = check.get("median_ms", check.get("median_s"))
        print(f"  [{status}] {check['label']}: {measured} (budget {budget})")

    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
