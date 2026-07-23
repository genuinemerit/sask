"""SPEC-037 tests — civil time-of-day input: shared inverse converter and
four-endpoint wiring.

Covers:
  - offset_to_civil_time / civil_time_to_offset: representative + boundary
    values, round-trip, out-of-range rejection (CalendarRangeError).
  - format_civil_time / parse_civil_time: string boundary, malformed shapes.
  - resolve_moment: day + time -> pulse; day alone -> unchanged default
    (backward-compatibility).
  - Moons/Planets/Sky: supplying a time computes at the refined moment;
    omitting it reproduces today's result.
  - Ephemeris: start_time_of_day pins the sweep start; throttle unaffected.
  - Adapter: malformed/out-of-range time surfaces the typed error like
    existing calendar input errors (200, not 500).
  - Convention: civil clock time is midnight-based regardless of a
    culture's day-start offset (Fatunik sunrise vs. Terpin midnight) —
    the cross-culture discovery this feature enables.

UAT follows unit testing: see docs/devlog.md.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sask.calendar.pulse import (
    CalendarRangeError,
    civil_time_to_offset,
    format_civil_time,
    offset_to_civil_time,
    parse_civil_time,
    resolve_moment,
)
from sask.config_loader import load_config
from sask.web import create_app

REAL_CONFIG = Path(__file__).parent.parent / "config"
CONFIG = load_config(REAL_CONFIG)
PULSES_PER_DAY = CONFIG.time_constants.pulses_per_day  # 86_400
FC = CONFIG.fatunik  # day_start_offset = 21_600 (6 AM sunrise)
TC = CONFIG.terpin  # day_start_offset = 0 (midnight)


# ── offset_to_civil_time / civil_time_to_offset ──────────────────────────────


def test_offset_zero_is_midnight():
    assert offset_to_civil_time(0) == (0, 0, 0)


def test_offset_last_pulse_is_23_59_59():
    assert offset_to_civil_time(PULSES_PER_DAY - 1) == (23, 59, 59)


def test_offset_representative_value():
    # 18:30:00 = 18*3600 + 30*60 = 66600
    assert offset_to_civil_time(66_600) == (18, 30, 0)


def test_civil_time_to_offset_midnight():
    assert civil_time_to_offset(0, 0, 0) == 0


def test_civil_time_to_offset_last_second():
    assert civil_time_to_offset(23, 59, 59) == PULSES_PER_DAY - 1


def test_civil_time_to_offset_representative_value():
    assert civil_time_to_offset(18, 30, 0) == 66_600


@pytest.mark.parametrize("offset", [0, 1, 3_599, 66_600, 43_200, PULSES_PER_DAY - 1])
def test_offset_round_trips_through_civil_time(offset):
    h, m, s = offset_to_civil_time(offset)
    assert civil_time_to_offset(h, m, s) == offset


@pytest.mark.parametrize(
    "hour,minute,second",
    [(24, 0, 0), (12, 60, 0), (0, 0, 60), (-1, 0, 0), (0, -1, 0), (0, 0, -1)],
)
def test_civil_time_to_offset_rejects_out_of_range(hour, minute, second):
    with pytest.raises(CalendarRangeError):
        civil_time_to_offset(hour, minute, second)


# ── format_civil_time / parse_civil_time ─────────────────────────────────────


def test_format_civil_time_matches_offset_to_civil_time():
    assert format_civil_time(66_600) == "18:30:00"


def test_parse_civil_time_matches_civil_time_to_offset():
    assert parse_civil_time("18:30:00") == 66_600


@pytest.mark.parametrize("offset", [0, 1, 66_600, PULSES_PER_DAY - 1])
def test_format_and_parse_round_trip(offset):
    # A time displayed and then re-entered round-trips to the same pulse
    # offset (REQ-FUN-016 acceptance #3).
    assert parse_civil_time(format_civil_time(offset)) == offset


@pytest.mark.parametrize(
    "text",
    ["24:00:00", "12:60:00", "00:00:60", "not a time", "18:30", "18:30:00:00", ""],
)
def test_parse_civil_time_rejects_malformed_or_out_of_range(text):
    with pytest.raises(CalendarRangeError):
        parse_civil_time(text)


# ── resolve_moment ────────────────────────────────────────────────────────────


def test_resolve_moment_day_alone_is_day_base():
    # Omitting time reproduces today's default (day's base pulse).
    assert resolve_moment(1, None) == 0
    assert resolve_moment(2, None) == PULSES_PER_DAY


def test_resolve_moment_empty_string_is_day_base():
    assert resolve_moment(1, "") == 0


def test_resolve_moment_day_plus_time():
    assert resolve_moment(1, "18:30:00") == 66_600
    assert resolve_moment(2, "00:00:01") == PULSES_PER_DAY + 1


def test_resolve_moment_invalid_time_raises():
    with pytest.raises(CalendarRangeError):
        resolve_moment(1, "24:00:00")


# ── Convention: civil clock is midnight-based, not culture-day-start-based ───


def test_civil_clock_ignores_fatunik_day_start_offset():
    # Fatunik's day starts at sunrise (day_start_offset=21600), but the civil
    # clock reading is still Astro-midnight-based: pulse 21600 (Fatunik's own
    # civil day start) reads as 06:00:00, not 00:00:00.
    assert format_civil_time(FC.day_start_offset) == "06:00:00"


def test_civil_clock_matches_terpin_midnight_day_start():
    assert TC.day_start_offset == 0
    assert format_civil_time(TC.day_start_offset) == "00:00:00"


# ── Web endpoints ─────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def app():
    return create_app(config_dir=REAL_CONFIG)


@pytest.fixture(scope="module")
def client(app):
    return app.test_client()


def test_moons_time_of_day_refines_moment(client):
    with_time = client.get("/moons?astro_day=1&time_of_day=12:00:00").data
    without_time = client.get("/moons?astro_day=1").data
    assert b"12:00:00" in with_time
    assert b"12:00:00" not in without_time


def test_moons_omitted_time_reproduces_today_behaviour(client):
    resp = client.get("/moons?astro_day=1")
    assert resp.status_code == 200
    assert b"00:00:00" in resp.data


def test_planets_time_of_day_refines_moment(client):
    resp = client.get("/planets?astro_day=1&time_of_day=12:00:00")
    assert resp.status_code == 200
    assert b"12:00:00" in resp.data


def test_planets_shows_time_of_day_at_parity_with_moons(client):
    # planets() previously showed no time-of-day at all; SPEC-037 brings it
    # to parity with moons()/sky().
    resp = client.get("/planets?astro_day=1")
    assert resp.status_code == 200
    assert b"00:00:00" in resp.data


def test_sky_time_of_day_refines_moment(client):
    with_time = client.get("/sky?astro_day=1&time_of_day=18:30:00").data
    assert b"18:30:00" in with_time


def test_sky_omitted_time_reproduces_today_behaviour(client):
    resp = client.get("/sky?astro_day=1")
    assert resp.status_code == 200
    assert b"00:00:00" in resp.data


def test_moons_invalid_time_returns_200_with_error(client):
    resp = client.get("/moons?astro_day=1&time_of_day=24:00:00")
    assert resp.status_code == 200
    assert b"Invalid" in resp.data


def test_sky_invalid_time_returns_200_with_error(client):
    resp = client.get("/sky?astro_day=1&time_of_day=12:60:00")
    assert resp.status_code == 200
    assert b"Invalid" in resp.data


def test_planets_malformed_time_returns_200_with_error(client):
    resp = client.get("/planets?astro_day=1&time_of_day=not-a-time")
    assert resp.status_code == 200
    assert b"Invalid" in resp.data


def test_astro_day_only_requests_still_pass(client):
    # Backward-compatibility: existing Astro-Day-only requests are unaffected.
    resp = client.get("/moons?astro_day=1")
    assert resp.status_code == 200
    assert b"Endor" in resp.data


def _duration_qs(start_time=None, duration_days=1, profile="scribal"):
    qs = f"/ephemeris?start_astro_day=1&duration_days={duration_days}&step_minutes=5&profile={profile}"
    if start_time is not None:
        qs += f"&start_time_of_day={start_time}"
    return qs


def test_ephemeris_start_time_of_day_pins_sweep_start(client):
    resp = client.get(_duration_qs(start_time="06:00:00"))
    assert resp.status_code == 200
    assert b"06:00:00" in resp.data


def test_ephemeris_omitted_start_time_reproduces_day_start(client):
    resp = client.get(_duration_qs())
    assert resp.status_code == 200
    assert b"00:00:00" in resp.data


def test_ephemeris_invalid_start_time_returns_200_with_error(client):
    resp = client.get(_duration_qs(start_time="24:00:00"))
    assert resp.status_code == 200
    assert b"Invalid" in resp.data


def test_ephemeris_throttle_unaffected_by_start_time(client):
    # Step floor (5 min) and range cap (30 days) still apply regardless of
    # start_time_of_day; a too-small step still errors, not 500.
    qs = (
        "/ephemeris?start_astro_day=1&start_time_of_day=06:00:00"
        "&duration_days=1&step_minutes=1&profile=scribal"
    )
    resp = client.get(qs)
    assert resp.status_code == 200
    assert b"error" in resp.data.lower() or b"minimum" in resp.data.lower()
