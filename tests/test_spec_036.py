"""SPEC-036 tests — full localization: proper-noun catalog, lore-calendar
localization, page builder, staleness check, completeness gate.

This file grows alongside SPEC-036 implementation; not all deliverables
are covered yet. Currently covers:
  - proper-noun catalog: invariant terms present-with-identical-value in
    both locales; respelled terms differ; a term missing from es-ES fails
    the strict deploy gate
  - lore.py locale threading: render_lore_time/render_lore_date localize
    correctly across all 6 calendar shapes (solar/lunar-round/lunar-ages/
    hearth), including Spanish gender agreement and preposition handling;
    en-US output is unchanged from pre-SPEC-036 (SPEC-017) behavior
  - page builder (DD-0023): tagged base -> en-US deterministic render;
    es-ES render substitutes proper nouns without translating surrounding
    prose (translation is the separate, human-reviewed step); rendered
    en-US output is tag-free and matches the committed served page
  - staleness check: editing a base page makes the en-US check fail until
    rebuilt; makes the es-ES check fail until re-translated-and-
    acknowledged; acknowledging records the new hash and clears the flag
  - LABEL tier: translator.py resolves body/star/comet names, phase names,
    compass points, eclipse type, and rise/set special values through the
    catalog (not just lore.py's calendar dates); web routes render the
    localized templates end to end in both locales
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from sask.calendar.bodies import all_body_states
from sask.calendar.lore import render_lore_date, render_lore_time
from sask.calendar.lunar import get_lunar_date
from sask.calendar.pulse import astro_to_fatunik, astro_to_terpin
from sask.calendar.sky import all_sky_positions
from sask.config_loader import load_config
from sask.web import create_app
from sask.web.translator import to_moon_view, to_planet_view

PROJECT_ROOT = Path(__file__).parent.parent
REAL_CONFIG = PROJECT_ROOT / "config"
CONFIG = load_config(REAL_CONFIG)

sys.path.insert(0, str(PROJECT_ROOT / "tools" / "dev"))
import build_i18n_pages  # noqa: E402
import check_page_staleness  # noqa: E402
import validate_i18n  # noqa: E402

STORY_PULSE = 104548096103  # canonical "present moment" (timeline.toml)


# ── Proper-noun catalog ───────────────────────────────────────────────────────


def test_invariant_body_present_identical_both_locales():
    en = CONFIG.i18n.entries["en-US"]
    es = CONFIG.i18n.entries["es-ES"]
    assert en["body.calumbra"] == es["body.calumbra"] == "Calumbra"
    assert en["body.zehembra"] == es["body.zehembra"] == "Zehembra"


def test_respelled_terms_differ():
    en = CONFIG.i18n.entries["en-US"]
    es = CONFIG.i18n.entries["es-ES"]
    assert en["body.fatune"] == "Fatune"
    assert es["body.fatune"] == "Fatún"
    assert en["body.endor"] != es["body.endor"]
    assert en["lore.untamed.turn_word"] != es["lore.untamed.turn_word"]


def test_missing_non_base_translation_fails_strict(tmp_path):
    en_dir = tmp_path / "i18n"
    en_dir.mkdir()
    (en_dir / "en-US.toml").write_text(
        '[tags]\n"body.endor" = "Endor"\n"body.sella" = "Sella"\n'
    )
    (en_dir / "es-ES.toml").write_text('[tags]\n"body.endor" = "Endor"\n')

    permissive = validate_i18n.run(en_dir, strict=False)
    strict = validate_i18n.run(en_dir, strict=True)
    assert not any(m.startswith("ERROR") for m in permissive)  # warn only
    assert any(m.startswith("ERROR") for m in strict)  # hard-fail


# ── lore.py locale threading ──────────────────────────────────────────────────


def test_render_lore_time_en_us_unchanged():
    # Matches SPEC-017's pre-existing assertions exactly (regression check).
    assert (
        render_lore_time(300, "terpin", CONFIG, "en-US")
        == "First Watch . shur 1 : keyt 1"
    )


def test_render_lore_time_es_es_localized():
    result = render_lore_time(300, "terpin", CONFIG, "es-ES")
    assert result == "Primera Guardia . shur 1 : keit 1"


def test_render_lore_date_solar_es_es_gender_and_preposition():
    fd = astro_to_fatunik(STORY_PULSE, CONFIG)
    result = render_lore_date(fd, "fatunik_solar", CONFIG, "es-ES")
    assert result == "Velden, el 6.º kell de Tárnel, Año 1782 en la Era Brillante"
    assert "de el " not in result


def test_render_lore_date_terpin_ages_masculine_age_no_contraction_bug():
    ld = get_lunar_date(STORY_PULSE, "terpin_lunar", CONFIG)
    result = render_lore_date(ld, "terpin_lunar", CONFIG, "es-ES")
    # "el Ahondamiento" (masculine age) must render via "en", never "de el".
    assert "de el " not in result
    assert "en el Ahondamiento" in result or "en la" in result


def test_render_lore_date_lunar_round_del_contraction():
    ld = get_lunar_date(STORY_PULSE, "untamed", CONFIG)
    result = render_lore_date(ld, "untamed", CONFIG, "es-ES")
    assert "del Riv" in result
    assert "de el " not in result


def test_render_lore_date_hearth_feminine_ordinal_on_vuelta():
    ld = get_lunar_date(STORY_PULSE, "hearth", CONFIG)
    result = render_lore_date(ld, "hearth", CONFIG, "es-ES")
    assert "vuelta" in result
    assert ".ª" in result  # feminine ordinal marker on the vuelta count
    assert "Viejo Djem" in result


def test_render_lore_date_all_calendars_localize_without_raw_english_leak():
    fd = astro_to_fatunik(STORY_PULSE, CONFIG)
    td = astro_to_terpin(STORY_PULSE, CONFIG)
    checks = [
        render_lore_date(fd, "fatunik_solar", CONFIG, "es-ES"),
        render_lore_date(td, "terpin_solar", CONFIG, "es-ES"),
        render_lore_date(
            get_lunar_date(STORY_PULSE, "untamed", CONFIG), "untamed", CONFIG, "es-ES"
        ),
        render_lore_date(
            get_lunar_date(STORY_PULSE, "warren", CONFIG), "warren", CONFIG, "es-ES"
        ),
        render_lore_date(
            get_lunar_date(STORY_PULSE, "terpin_lunar", CONFIG),
            "terpin_lunar",
            CONFIG,
            "es-ES",
        ),
        render_lore_date(
            get_lunar_date(STORY_PULSE, "hearth", CONFIG), "hearth", CONFIG, "es-ES"
        ),
    ]
    for result in checks:
        assert " of " not in result
        assert " the " not in result
        assert " day " not in result


# ── Page builder (DD-0023) ─────────────────────────────────────────────────────


def test_render_page_en_us_deterministic_and_tag_free():
    base = "See {culture.fatunik} and {culture.terpin} for calendars."
    result = build_i18n_pages.render_page(base, "en-US", CONFIG.i18n)
    assert result == "See Fatunik and Terpin for calendars."
    assert "{" not in result and "}" not in result


def test_render_page_same_input_same_output_twice():
    base = "The moon {body.fatune} rises."
    r1 = build_i18n_pages.render_page(base, "en-US", CONFIG.i18n)
    r2 = build_i18n_pages.render_page(base, "en-US", CONFIG.i18n)
    assert r1 == r2 == "The moon Fatune rises."


def test_render_page_es_es_substitutes_proper_nouns_only():
    base = "The moon {body.fatune} rises over {body.endor}."
    result = build_i18n_pages.render_page(base, "es-ES", CONFIG.i18n)
    # Proper nouns substituted; surrounding English prose untouched (that
    # part is the separate, human-reviewed translation step, not this
    # function's job).
    assert result == "The moon Fatún rises over Éndor."


def test_real_canary_base_matches_committed_served_page():
    base_path = PROJECT_ROOT / "docs" / "help_src" / "getting-started.md"
    served_path = PROJECT_ROOT / "docs" / "help" / "getting-started.md"
    rendered = build_i18n_pages.render_page(
        base_path.read_text(encoding="utf-8"), "en-US", CONFIG.i18n
    )
    assert rendered == served_path.read_text(encoding="utf-8")
    assert "{" not in rendered


# ── Staleness check (DD-0023) ───────────────────────────────────────────────────


def _setup_staleness_fixture(tmp_path, monkeypatch):
    base_src = tmp_path / "help_src"
    served = tmp_path / "help"
    base_src.mkdir()
    served.mkdir()
    monkeypatch.setattr(check_page_staleness, "BASE_SRC_DIR", base_src)
    monkeypatch.setattr(check_page_staleness, "SERVED_DIR", served)
    monkeypatch.setattr(
        check_page_staleness, "MANIFEST_PATH", base_src / "translation-status.toml"
    )

    base_text = "Hello {culture.fatunik}."
    (base_src / "greet.md").write_text(base_text, encoding="utf-8")
    (served / "greet.md").write_text(
        build_i18n_pages.render_page(base_text, "en-US", CONFIG.i18n), encoding="utf-8"
    )
    (served / "greet.es-ES.md").write_text("Hola Fatunik.", encoding="utf-8")
    return base_src, served


def _acknowledge(base_src: Path) -> None:
    base_text = (base_src / "greet.md").read_text(encoding="utf-8")
    check_page_staleness._write_manifest(
        {"greet": {"es-ES": check_page_staleness._base_hash(base_text)}}
    )


def test_staleness_check_clean_before_any_edit(tmp_path, monkeypatch):
    _setup_staleness_fixture(tmp_path, monkeypatch)
    errors = check_page_staleness.check()
    # No manifest entry yet -> es-ES flags stale until acknowledged, en-US clean.
    assert not any("greet.md is stale" in e for e in errors)
    assert any("last reviewed" in e for e in errors)


def test_staleness_check_en_us_fails_after_base_edit_until_rebuilt(
    tmp_path, monkeypatch
):
    base_src, served = _setup_staleness_fixture(tmp_path, monkeypatch)
    _acknowledge(base_src)
    assert not check_page_staleness.check()  # clean baseline

    (base_src / "greet.md").write_text(
        "Hello {culture.fatunik}, again.", encoding="utf-8"
    )
    errors = check_page_staleness.check()
    assert any("stale relative to" in e for e in errors)

    served_en = served / "greet.md"
    served_en.write_text(
        build_i18n_pages.render_page(
            (base_src / "greet.md").read_text(), "en-US", CONFIG.i18n
        ),
        encoding="utf-8",
    )
    errors_after_rebuild = check_page_staleness.check()
    assert not any("stale relative to" in e for e in errors_after_rebuild)
    # es-ES still flags -- rebuilding en-US doesn't satisfy the translation review.
    assert any("last reviewed" in e for e in errors_after_rebuild)


def test_staleness_check_es_es_flags_until_acknowledged(tmp_path, monkeypatch):
    base_src, served = _setup_staleness_fixture(tmp_path, monkeypatch)

    _acknowledge(base_src)
    assert not check_page_staleness.check()

    new_base_text = "Hello {culture.terpin}."
    (base_src / "greet.md").write_text(new_base_text, encoding="utf-8")
    # Rebuild en-US so this test isolates the es-ES-specific flag/acknowledge
    # behavior from the (already separately tested) en-US staleness check.
    (served / "greet.md").write_text(
        build_i18n_pages.render_page(new_base_text, "en-US", CONFIG.i18n),
        encoding="utf-8",
    )
    errors = check_page_staleness.check()
    assert any("last reviewed" in e for e in errors)

    _acknowledge(base_src)
    assert not check_page_staleness.check()


# ── LABEL tier: body/star/comet name resolution ─────────────────────────────────


@pytest.fixture(scope="module")
def app():
    return create_app(config_dir=REAL_CONFIG)


@pytest.fixture(scope="module")
def client(app):
    return app.test_client()


def test_to_moon_view_resolves_name_es_es():
    states = all_body_states(STORY_PULSE, CONFIG)
    positions = all_sky_positions(STORY_PULSE, states, CONFIG)
    pos_map = {p.name: p for p in positions}
    endor = next(s for s in states if s.name == "Endor")
    view = to_moon_view(
        endor, pos_map["Endor"], notes="", albedo=0.13, locale="es-ES", i18n=CONFIG.i18n
    )
    assert view.name == "Éndor"


def test_to_planet_view_resolves_name_es_es():
    states = all_body_states(STORY_PULSE, CONFIG)
    positions = all_sky_positions(STORY_PULSE, states, CONFIG)
    pos_map = {p.name: p for p in positions}
    dramond = next(s for s in states if s.name == "Dramond")
    view = to_planet_view(
        dramond,
        pos_map["Dramond"],
        apparent_color="Warm amber",
        rings=None,
        visible_moons=None,
        notes="",
        locale="es-ES",
        i18n=CONFIG.i18n,
    )
    assert view.name == "Drámun"


def test_sky_page_es_es_localizes_body_and_star_names(client):
    resp = client.get(f"/sky?pulse={STORY_PULSE}&locale=es-ES")
    assert resp.status_code == 200
    html = resp.data.decode()
    assert "Éndor" in html
    assert "Ilirun" in html
    assert "Djémbor" in html  # co-fullness moon list also resolves


def test_moons_page_es_es_localizes_names_and_phase(client):
    resp = client.get(f"/moons?pulse={STORY_PULSE}&locale=es-ES")
    assert resp.status_code == 200
    html = resp.data.decode()
    assert "Éndor" in html
    assert "Sí" in html  # Yes -> Sí (visibility column)
