"""SPEC-039 tests — JSON output for functional endpoints via content
negotiation (DD-0026).

Covers:
  - Negotiation: ?format=json and Accept: application/json each yield JSON;
    default is HTML; ?format param wins over Accept; unsupported/absent
    Accept with no param yields HTML.
  - Shape per endpoint: JSON follows the message-unit data shape and
    represents the COMPLETE unit (ephemeris includes parameters + summary +
    series, not only a bare series array).
  - Schema invariance: keys/ids are identical English in en-US and es-ES;
    only content values differ.
  - {id, label}: localizable domain values render as invariant id +
    localized label.
  - null: absent optionals render as null, never omitted.
  - Temporal contract: every response carries resolved pulse + atomic
    date/time; /sky also carries lore-language time.
  - Error envelope: malformed input and ephemeris throttle violations return
    the consistent {error: {code, message}} shape with 400 status.
  - Parity: the JSON carries the same underlying data the HTML renders.
  - HTML output is unchanged when JSON is not requested.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sask.web import create_app

REAL_CONFIG = Path(__file__).parent.parent / "config"

PULSE = 86_400  # Astro day 2, 00:00:00 — a stable, arbitrary query moment


@pytest.fixture(scope="module")
def app():
    return create_app(config_dir=REAL_CONFIG)


@pytest.fixture(scope="module")
def client(app):
    return app.test_client()


# ── Content negotiation ──────────────────────────────────────────────────────


@pytest.mark.parametrize("path", ["/", "/moons", "/planets", "/sky"])
def test_format_json_param_returns_json(client, path):
    resp = client.get(f"{path}?pulse={PULSE}&format=json")
    assert resp.status_code == 200
    assert resp.content_type == "application/json"


@pytest.mark.parametrize("path", ["/", "/moons", "/planets", "/sky"])
def test_accept_header_json_returns_json(client, path):
    resp = client.get(f"{path}?pulse={PULSE}", headers={"Accept": "application/json"})
    assert resp.content_type == "application/json"


@pytest.mark.parametrize("path", ["/", "/moons", "/planets", "/sky", "/ephemeris"])
def test_default_is_html(client, path):
    resp = client.get(f"{path}?pulse={PULSE}")
    assert resp.content_type == "text/html; charset=utf-8"


@pytest.mark.parametrize("path", ["/", "/moons", "/planets", "/sky"])
def test_bare_wildcard_accept_yields_html(client, path):
    resp = client.get(f"{path}?pulse={PULSE}", headers={"Accept": "*/*"})
    assert resp.content_type == "text/html; charset=utf-8"


def test_format_param_wins_over_conflicting_accept_header(client):
    resp = client.get(
        f"/moons?pulse={PULSE}&format=json", headers={"Accept": "text/html"}
    )
    assert resp.content_type == "application/json"

    resp = client.get(
        f"/moons?pulse={PULSE}&format=html", headers={"Accept": "application/json"}
    )
    assert resp.content_type == "text/html; charset=utf-8"


def test_html_output_unchanged_when_json_not_requested(client):
    resp = client.get(f"/moons?pulse={PULSE}")
    assert b"<table>" in resp.data
    assert b"<script" not in resp.data


# ── / (Pulse) shape ─────────────────────────────────────────────────────────
#
# Added after DD-0026/REQ-FUN-018/SPEC-039 were corrected 2026-08-02: / (Pulse)
# was omitted from the original endpoint list by mistake. Its message unit
# (PulseInfo + Fatunik/Terpin dates) IS the whole response -- unlike the other
# four, there's no separate body/scene payload to nest it under, so the
# response is temporal_json(...) directly at the top level, not wrapped in a
# "query" key.


def test_index_json_shape(client):
    resp = client.get(f"/?pulse={PULSE}&format=json")
    assert resp.status_code == 200
    data = resp.get_json()

    assert set(data.keys()) == {
        "pulse",
        "astro_day",
        "astro_time",
        "orbital_position",
        "fatunik_date",
        "terpin_date",
    }
    assert data["pulse"] == PULSE
    assert data["astro_day"] == 2
    assert data["astro_time"] == "00:00:00"
    assert data["fatunik_date"]["calendar_id"] == "fatunik"
    assert data["terpin_date"]["calendar_id"] == "terpin"


def test_index_json_matches_html_view(client):
    """Parity: the JSON pulse/astro_day match what the HTML view renders."""
    json_data = client.get(f"/?pulse={PULSE}&format=json").get_json()
    html_resp = client.get(f"/?pulse={PULSE}")
    assert str(json_data["astro_day"]).encode() in html_resp.data


def test_index_json_missing_moment_error_envelope(client):
    resp = client.get("/?format=json")
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "missing_moment_query"


def test_index_json_invalid_pulse_error_envelope(client):
    resp = client.get("/?pulse=not_a_number&format=json")
    assert resp.status_code == 400
    data = resp.get_json()
    assert set(data.keys()) == {"error"}
    assert data["error"]["code"] == "invalid_pulse_value"


def test_index_html_unchanged_when_json_not_requested(client):
    resp = client.get(f"/?pulse={PULSE}")
    assert b"<script" not in resp.data


# ── /moons shape ──────────────────────────────────────────────────────────────


def test_moons_json_shape(client):
    resp = client.get(f"/moons?pulse={PULSE}&format=json")
    data = resp.get_json()

    assert set(data.keys()) == {"query", "fatune", "bodies"}
    assert data["query"]["pulse"] == PULSE
    assert data["query"]["astro_day"] == 2
    assert data["query"]["astro_time"] == "00:00:00"
    assert data["query"]["fatunik_date"]["calendar_id"] == "fatunik"
    assert data["query"]["terpin_date"]["calendar_id"] == "terpin"

    assert len(data["bodies"]) == 8  # eight moons (SPEC-009)
    for body in data["bodies"]:
        assert body["body_type"] == "moon"
        assert set(body["name"].keys()) == {"id", "label"}
        assert body["albedo"] is not None
        assert body["visible_moons"] is None  # moon-only field's planet twin -> null
        # complete message unit: raw fields the HTML table never shows
        assert "sidereal_fraction" in body
        assert "ecliptic_lon_deg" in body
        assert "geocentric_dist" in body


def test_moons_json_eclipse_null_when_absent(client):
    resp = client.get(f"/moons?pulse={PULSE}&format=json")
    data = resp.get_json()
    non_eclipsed = [b for b in data["bodies"] if b["eclipse_type"] is None]
    assert non_eclipsed  # at least one moon isn't eclipsed at this pulse
    eclipsed = [b for b in data["bodies"] if b["eclipse_type"] is not None]
    for body in eclipsed:
        assert set(body["eclipse_type"].keys()) == {"id", "label"}
        assert body["eclipse_type"]["id"] in ("solar", "lunar")


def test_moons_json_parity_with_html(client):
    """The JSON body list and HTML table agree on which moons are present."""
    json_resp = client.get(f"/moons?pulse={PULSE}&format=json")
    html_resp = client.get(f"/moons?pulse={PULSE}")
    names = [b["name"]["label"] for b in json_resp.get_json()["bodies"]]
    for name in names:
        assert name.encode() in html_resp.data


# ── /planets shape ────────────────────────────────────────────────────────────


def test_planets_json_shape(client):
    resp = client.get(f"/planets?pulse={PULSE}&format=json")
    data = resp.get_json()

    assert len(data["bodies"]) == 7  # seven planets (SPEC-009)
    for body in data["bodies"]:
        assert body["body_type"] == "planet"
        assert body["albedo"] is None  # planet-only response -> moon field null
        assert body["visible_moons"] is not None
        assert body["rings"] is None or isinstance(body["rings"], str)


def test_planets_json_rings_null_vs_label(client):
    resp = client.get(f"/planets?pulse={PULSE}&format=json")
    data = resp.get_json()
    ringed = [b for b in data["bodies"] if b["rings"] is not None]
    ringless = [b for b in data["bodies"] if b["rings"] is None]
    assert ringed and ringless  # config has a mix (Dramond has rings)


# ── /sky shape ────────────────────────────────────────────────────────────────


def test_sky_json_shape(client):
    resp = client.get(f"/sky?pulse={PULSE}&format=json")
    data = resp.get_json()

    assert set(data.keys()) == {
        "query",
        "season",
        "scene",
        "days_until_next_cofullness",
        "lunar_calendars",
        "lore",
        "night_summary",
        "image_prompt",
    }
    assert set(data["season"]["season"].keys()) == {"id", "label"}
    assert set(data["scene"].keys()) == {
        "bodies_up",
        "stars_up",
        "active_house",
        "circumpolar_houses",
        "co_fullness_tonight",
        "next_co_fullness",
    }
    assert set(data["scene"]["active_house"].keys()) == {"id", "label"}
    assert len(data["lunar_calendars"]) == 4  # four lunar calendars (SPEC-012)
    for entry in data["lunar_calendars"]:
        assert set(entry["calendar"].keys()) == {"id", "label"}
        assert set(entry["moon"].keys()) == {"id", "label"}


def test_sky_json_lore_present_when_enabled(client, app):
    cfg = app.config["SASK_CONFIG"]
    resp = client.get(f"/sky?pulse={PULSE}&format=json")
    data = resp.get_json()
    if cfg.lore_time.enabled:
        assert data["lore"] is not None
        assert set(data["lore"].keys()) == {
            "fatunik_time",
            "terpin_time",
            "fatunik_date",
            "terpin_date",
            "lunar_dates",
        }
        assert isinstance(data["lore"]["fatunik_time"], str)
        assert len(data["lore"]["lunar_dates"]) == 4
    else:
        assert data["lore"] is None


def test_sky_json_near_event_null_when_absent(client):
    # A pulse far from any near-event tolerance window; near_event should be null.
    resp = client.get("/sky?pulse=5000000&format=json")
    data = resp.get_json()
    assert data["season"]["near_event"] is None or set(
        data["season"]["near_event"].keys()
    ) == {"id", "label"}


# ── Schema invariance / localization ────────────────────────────────────────


@pytest.mark.parametrize("path", ["/", "/moons", "/planets", "/sky"])
def test_keys_identical_across_locales(client, path):
    en = client.get(f"{path}?pulse={PULSE}&format=json&locale=en-US").get_json()
    es = client.get(f"{path}?pulse={PULSE}&format=json&locale=es-ES").get_json()
    assert set(en.keys()) == set(es.keys())


def test_moons_body_keys_identical_across_locales(client):
    en = client.get(f"/moons?pulse={PULSE}&format=json&locale=en-US").get_json()
    es = client.get(f"/moons?pulse={PULSE}&format=json&locale=es-ES").get_json()
    assert set(en["bodies"][0].keys()) == set(es["bodies"][0].keys())
    assert en["bodies"][0]["name"]["id"] == es["bodies"][0]["name"]["id"]


def test_moons_body_labels_localize(client):
    en = client.get(f"/moons?pulse={PULSE}&format=json&locale=en-US").get_json()
    es = client.get(f"/moons?pulse={PULSE}&format=json&locale=es-ES").get_json()
    en_labels = {b["name"]["id"]: b["name"]["label"] for b in en["bodies"]}
    es_labels = {b["name"]["id"]: b["name"]["label"] for b in es["bodies"]}
    assert en_labels != es_labels  # at least one body name translates differently
    assert en_labels.keys() == es_labels.keys()  # ids invariant


def test_sky_season_label_localizes_id_stays(client):
    en = client.get(f"/sky?pulse={PULSE}&format=json&locale=en-US").get_json()
    es = client.get(f"/sky?pulse={PULSE}&format=json&locale=es-ES").get_json()
    assert en["season"]["season"]["id"] == es["season"]["season"]["id"]


def test_fatunik_terpin_calendar_id_invariant_string(client):
    """calendar_id has no i18n label in the catalog (verification-point
    finding) -- it's a plain invariant string, never {id, label}, in every
    locale."""
    en = client.get(f"/moons?pulse={PULSE}&format=json&locale=en-US").get_json()
    es = client.get(f"/moons?pulse={PULSE}&format=json&locale=es-ES").get_json()
    assert en["query"]["fatunik_date"]["calendar_id"] == "fatunik"
    assert es["query"]["fatunik_date"]["calendar_id"] == "fatunik"


# ── Temporal contract ─────────────────────────────────────────────────────────


@pytest.mark.parametrize("path", ["/moons", "/planets", "/sky"])
def test_temporal_contract_present(client, path):
    data = client.get(f"{path}?pulse={PULSE}&format=json").get_json()
    q = data["query"]
    assert q["pulse"] == PULSE
    assert q["astro_day"] == 2
    assert q["astro_time"] == "00:00:00"
    assert "orbital_position" in q
    assert q["fatunik_date"]["year"] is not None
    assert q["terpin_date"]["year"] is not None


def test_civic_date_query_resolves_explicit_moment(client):
    """A civil-date (Fatunik) query, which carries no time of its own, still
    yields an explicit resolved pulse/atomic time in the response (here,
    06:00:00 — Fatunik's civil day starts at its configured sunrise offset,
    not Astro midnight; the point is that SOME explicit time is always
    stated, never left for a program to assume)."""
    resp = client.get("/moons?fatunik_year=1&fatunik_month=1&fatunik_day=1&format=json")
    data = resp.get_json()
    assert isinstance(data["query"]["pulse"], int)
    assert data["query"]["astro_time"] == "06:00:00"
    assert data["query"]["fatunik_date"] == {
        "calendar_id": "fatunik",
        "year": 1,
        "month": 1,
        "day": 1,
    }


# ── Ephemeris ────────────────────────────────────────────────────────────────


def _ephemeris_query(profile: str = "scribal") -> str:
    return (
        f"/ephemeris?start_pulse={PULSE}&step_minutes=60"
        f"&duration_days=1&profile={profile}&format=json"
    )


def test_ephemeris_json_shape_complete_unit(client):
    resp = client.get(_ephemeris_query("both"))
    assert resp.status_code == 200
    data = resp.get_json()

    assert set(data.keys()) == {"parameters", "summary", "series"}
    assert set(data["parameters"].keys()) == {
        "start",
        "end",
        "step_pulses",
        "step_minutes",
        "profile",
    }
    assert data["parameters"]["start"]["pulse"] == PULSE
    assert data["parameters"]["step_minutes"] == 60
    assert data["summary"]["step_count"] == len(data["series"]["scribal"]["steps"])
    # not only the series array: parameters + summary are siblings of series
    assert isinstance(data["series"], dict)
    assert data["series"]["scribal"] is not None
    assert data["series"]["kinematic"] is not None


def test_ephemeris_profile_selects_null_series(client):
    scribal_only = client.get(_ephemeris_query("scribal")).get_json()
    assert scribal_only["series"]["scribal"] is not None
    assert scribal_only["series"]["kinematic"] is None

    kinematic_only = client.get(_ephemeris_query("kinematic")).get_json()
    assert kinematic_only["series"]["scribal"] is None
    assert kinematic_only["series"]["kinematic"] is not None


def test_ephemeris_scribal_step_shape(client):
    data = client.get(_ephemeris_query("scribal")).get_json()
    step = data["series"]["scribal"]["steps"][0]
    assert set(step.keys()) == {
        "pulse",
        "astro_day",
        "astro_time",
        "bodies_up",
        "stars_up",
        "active_house",
        "circumpolar_houses",
        "co_fullness_tonight",
    }
    assert set(step["active_house"].keys()) == {"id", "label"}
    for body in step["bodies_up"]:
        assert set(body["name"].keys()) == {"id", "label"}


def test_ephemeris_kinematic_step_shape(client):
    data = client.get(_ephemeris_query("kinematic")).get_json()
    step = data["series"]["kinematic"]["steps"][0]
    assert set(step.keys()) == {"pulse", "bodies"}
    assert data["series"]["kinematic"]["tracked_bodies"]
    for body_id, entry in step["bodies"].items():
        assert body_id == body_id.lower()
        assert set(entry.keys()) == {"alt", "az", "ill", "up"}


def test_ephemeris_astro_day_matches_moons_convention(client):
    """astro_day inside the ephemeris series uses the same 1-indexed Astro
    Day convention as every other endpoint's temporal contract."""
    data = client.get(_ephemeris_query("scribal")).get_json()
    first_step = data["series"]["scribal"]["steps"][0]
    assert first_step["astro_day"] == data["parameters"]["start"]["astro_day"]


def test_ephemeris_json_localizes_scene_content(client):
    en = client.get(_ephemeris_query("scribal") + "&locale=en-US").get_json()
    es = client.get(_ephemeris_query("scribal") + "&locale=es-ES").get_json()
    en_body = en["series"]["scribal"]["steps"][0]["bodies_up"][0]
    es_body = es["series"]["scribal"]["steps"][0]["bodies_up"][0]
    assert en_body["name"]["id"] == es_body["name"]["id"]
    assert en_body["name"]["label"] != es_body["name"]["label"]


def test_ephemeris_json_parity_with_download(client):
    """The JSON kinematic step count/tracked bodies match the equivalent
    /ephemeris/download export for the same range."""
    json_data = client.get(_ephemeris_query("kinematic")).get_json()
    dl = client.get(
        f"/ephemeris/download?start={PULSE}&end={PULSE + 86400}"
        f"&step=3600&profile=kinematic"
    )
    dl_data = dl.get_json()
    assert (
        json_data["series"]["kinematic"]["tracked_bodies"] == dl_data["tracked_bodies"]
    )
    assert len(json_data["series"]["kinematic"]["steps"]) == len(dl_data["steps"])


# ── Error envelope ───────────────────────────────────────────────────────────


def test_invalid_pulse_error_envelope(client):
    resp = client.get("/moons?pulse=not_a_number&format=json")
    assert resp.status_code == 400
    data = resp.get_json()
    assert set(data.keys()) == {"error"}
    assert set(data["error"].keys()) == {"code", "message"}
    assert data["error"]["code"] == "invalid_pulse_value"


def test_missing_moment_error_envelope(client):
    for path in ("/moons", "/planets", "/sky"):
        resp = client.get(f"{path}?format=json")
        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "missing_moment_query"


def test_ephemeris_missing_params_error_envelope(client):
    resp = client.get("/ephemeris?format=json")
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "missing_ephemeris_query"


def test_ephemeris_step_floor_violation_error_envelope(client):
    resp = client.get(
        "/ephemeris?start_pulse=0&step_minutes=1&duration_days=1"
        "&format=json&locale=en-US"
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["error"]["code"] == "ephemeris_range_invalid"
    assert "minimum" in data["error"]["message"]


def test_ephemeris_step_exceeds_duration_error_envelope(client):
    resp = client.get(
        "/ephemeris?start_pulse=0&step_minutes=1440&duration_days=1&format=json"
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "step_exceeds_duration"


def test_error_message_localizes(client):
    en = client.get("/moons?pulse=not_a_number&format=json&locale=en-US").get_json()
    es = client.get("/moons?pulse=not_a_number&format=json&locale=es-ES").get_json()
    assert en["error"]["code"] == es["error"]["code"]
    assert en["error"]["message"] != es["error"]["message"]


def test_invalid_fatunik_date_error_envelope(client):
    resp = client.get(
        "/moons?fatunik_year=1&fatunik_month=99&fatunik_day=1&format=json"
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "invalid_fatunik_date"
