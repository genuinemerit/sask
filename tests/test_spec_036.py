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
  - SENTENCE/STATEMENT tier: routes.py validation errors (incl. prefixed
    start_/end_ variants), the ephemeris instructional paragraph, co-
    fullness pluralization, house names, and lunar-calendar names all
    resolve correctly in es-ES via the live Flask test client
  - full-text pages: index.md and calendar-lore.md's tagged bases render
    deterministically; both es-ES translations (hand-authored, promoted
    from the builder's proper-noun-substituted draft) serve correctly
    through the /help routes
  - scholar-description tier: render_night_summary/render_image_prompt
    localize correctly (season mood, body/star/house names via .id,
    compass/height/phase, singular/plural star-count and co-fullness
    templates); en-US output is unchanged from pre-SPEC-036 (SPEC-013)
    behavior; render_image_prompt's directive list stays English
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from sask.calendar.bodies import all_body_states
from sask.calendar.lore import render_lore_date, render_lore_time
from sask.calendar.lunar import get_lunar_date
from sask.calendar.pulse import astro_to_fatunik, astro_to_terpin
from sask.calendar.scene import get_sky_scene, render_image_prompt, render_night_summary
from sask.calendar.sky import all_sky_positions
from sask.config_loader import load_config
from sask.message import CofullnessTonightRef, HouseRef, NextCofullnessRef, SkyScene
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
    assert result == "Velden, el 6.º kel de Tárnel, Año 1782 en la Era Brillante"
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


# ── SENTENCE/STATEMENT tier ─────────────────────────────────────────────────────


def test_index_invalid_pulse_error_es_es(client):
    resp = client.get("/?pulse=abc&locale=es-ES")
    assert resp.status_code == 200
    assert "Valor de pulso inv\xe1lido" in resp.data.decode()


def test_ephemeris_prefixed_start_pulse_error_es_es(client):
    resp = client.get("/ephemeris?start_pulse=abc&step_minutes=5&locale=es-ES")
    assert resp.status_code == 200
    assert "start_pulse inv\xe1lido" in resp.data.decode()


def test_ephemeris_step_exceeds_duration_error_es_es(client):
    resp = client.get(
        "/ephemeris?start_pulse=0&end_pulse=100&step_minutes=5&locale=es-ES"
    )
    assert resp.status_code == 200
    html = resp.data.decode()
    assert "iguala o supera la duraci\xf3n total" in html


def test_help_topic_not_found_es_es(client):
    resp = client.get("/help/nonexistent-topic-xyz?locale=es-ES")
    assert resp.status_code == 404
    html = resp.data.decode()
    assert "No existe un tema de ayuda llamado" in html


def test_ephemeris_statement_intro_renders_html_bold_es_es(client):
    resp = client.get("/ephemeris?locale=es-ES")
    html = resp.data.decode()
    assert "<strong>hora de inicio</strong>" in html
    assert "**" not in html  # markdown markers must not leak into HTML


def test_sky_page_co_fullness_pluralization_es_es(client):
    resp = client.get(f"/sky?pulse={STORY_PULSE}&locale=es-ES")
    text = " ".join(resp.data.decode().split())  # collapse template whitespace
    assert "lunas casi llenas al mismo tiempo" in text  # count=3, plural
    assert "en 1 d\xeda" in text  # singular day count


def test_sky_page_house_and_calendar_names_es_es(client):
    resp = client.get(f"/sky?pulse={STORY_PULSE}&locale=es-ES")
    html = resp.data.decode()
    assert "El polinizador alado" in html  # active house
    assert "El c\xf3mputo salvaje" in html  # untamed calendar name


# ── Full-text pages (DD-0023) ───────────────────────────────────────────────────


def test_index_and_calendar_lore_bases_match_committed_en_us_pages():
    for topic in ("index", "calendar-lore"):
        base_path = PROJECT_ROOT / "docs" / "help_src" / f"{topic}.md"
        served_path = PROJECT_ROOT / "docs" / "help" / f"{topic}.md"
        rendered = build_i18n_pages.render_page(
            base_path.read_text(encoding="utf-8"), "en-US", CONFIG.i18n
        )
        assert rendered == served_path.read_text(encoding="utf-8")
        assert "{" not in rendered


def test_help_index_serves_es_es_translation(client):
    # Regression: get_help_index() previously ignored SASK_HELP_PARALLEL_DOCS
    # entirely (only get_help_topic() consulted it), so index.es-ES.md was
    # never served even after it existed -- found while promoting this tier.
    resp = client.get("/help?locale=es-ES")
    assert resp.status_code == 200
    html = resp.data.decode()
    assert "gu\xeda de ayuda" in html
    assert "Welcome to the" not in html


def test_help_index_en_us_unaffected_by_locale_fix(client):
    resp = client.get("/help?locale=en-US")
    assert resp.status_code == 200
    html = resp.data.decode()
    assert "Welcome to the" in html


def test_calendar_lore_serves_es_es_translation_with_respellings(client):
    resp = client.get("/help/calendar-lore?locale=es-ES")
    assert resp.status_code == 200
    html = resp.data.decode()
    # Respelled catalog terms fixed after initial review must appear.
    assert "Jarven" in html
    assert "J\xe1labet" in html
    assert ">kel<" in html or "kel," in html or "kel " in html
    assert "Jesek" in html
    assert "Esaquel" in html
    assert "Darum" in html
    assert "J\xe1sek" in html
    # Terminology translations must appear; old English terms must not.
    assert "Indomado" in html
    assert "Madriguera" in html
    assert "Ronda" in html
    assert "Hogar" in html
    assert "sensiente" in html
    assert "Untamed" not in html
    assert "Warren" not in html
    assert ">Hearth<" not in html


def test_calendar_lore_en_us_still_serves_original_english(client):
    resp = client.get("/help/calendar-lore?locale=en-US")
    assert resp.status_code == 200
    html = resp.data.decode()
    assert "Untamed" in html
    assert "Harvenn" in html  # en-US month spelling unaffected by es-ES fix


# ── Scholar-description tier (scene.py) ─────────────────────────────────────────


def _empty_scene(**overrides) -> SkyScene:
    base = dict(
        pulse=0,
        season="stillness",
        bodies_up=(),
        stars_up=(),
        active_house=HouseRef(id="ember_gate", name="The Ember Gate"),
        circumpolar_houses=(),
        co_fullness_tonight=None,
        next_co_fullness=NextCofullnessRef(pulse=86400, count=0, moons=()),
    )
    base.update(overrides)
    return SkyScene(**base)


def test_night_summary_real_scene_es_es_matches_verified_output():
    scene = get_sky_scene(STORY_PULSE, CONFIG, locale="es-ES")
    summary = render_night_summary(scene, CONFIG, "es-ES")
    assert summary.startswith(
        "Una noche de quietud: pleno invierno, el cielo largo y fr\xedo."
    )
    assert "Djémbor" in summary  # body name resolved via .id, not raw .name
    assert " O " in summary or " O medio" in summary  # compass.w -> "O"
    assert (
        "cuarto creciente" in summary
    )  # lowercase phase, unlike translator.py's Title Case
    assert "El polinizador alado" in summary  # house name via .id
    assert "estrellas fijas son visibles" in summary  # plural verb agreement
    assert "casi llenas al mismo tiempo" in summary
    assert "d\xeda de distancia" in summary  # singular "day" (1 day to next event)


def test_night_summary_no_moons_es_es():
    scene = _empty_scene()
    summary = render_night_summary(scene, CONFIG, "es-ES")
    assert "No hay lunas sobre el horizonte." in summary


def test_night_summary_singular_star_count_es_es():
    from sask.message import StarInScene

    scene = _empty_scene(
        stars_up=(StarInScene(id="ilyrun", name="Ilyrun", direction="x"),)
    )
    summary = render_night_summary(scene, CONFIG, "es-ES")
    assert "1 estrella fija es visible, incluyendo Ilirun" in summary


def test_night_summary_and_one_other_singular_es_es():
    from sask.message import StarInScene

    stars = tuple(
        StarInScene(id=sid, name=sid, direction="x")
        for sid in ("ilyrun", "kresh", "marnok", "sethera")
    )
    scene = _empty_scene(stars_up=stars)
    summary = render_night_summary(scene, CONFIG, "es-ES")
    assert "y 1 m\xe1s" in summary


def test_night_summary_singular_cofullness_es_es():
    scene = _empty_scene(
        co_fullness_tonight=CofullnessTonightRef(
            count=1, moons=("sella",), observable=True
        )
    )
    summary = render_night_summary(scene, CONFIG, "es-ES")
    assert "Este d\xeda, 1 luna est\xe1 casi llena: Sela." in summary


def test_night_summary_cofullness_below_horizon_es_es():
    scene = _empty_scene(
        co_fullness_tonight=CofullnessTonightRef(
            count=2, moons=("sella", "shunna"), observable=False
        )
    )
    summary = render_night_summary(scene, CONFIG, "es-ES")
    assert "(bajo el horizonte)" in summary


def test_night_summary_en_us_unchanged_default_locale():
    scene = get_sky_scene(STORY_PULSE, CONFIG)  # no locale kwarg -> defaults en-US
    summary = render_night_summary(scene, CONFIG)  # no locale arg -> defaults en-US
    assert summary.startswith(
        "A night of stillness: deep winter, the sky long and cold."
    )
    assert "Jembor" in summary
    assert "W mid" in summary


def test_image_prompt_directives_stay_english_in_es_es():
    scene = get_sky_scene(STORY_PULSE, CONFIG, locale="es-ES")
    prompt = render_image_prompt(scene, CONFIG, locale="es-ES")
    assert prompt.startswith(render_night_summary(scene, CONFIG, "es-ES"))
    assert "Image style:" in prompt  # directive wrapper text stays English


def test_sky_page_night_summary_es_es_via_flask(client):
    resp = client.get(f"/sky?pulse={STORY_PULSE}&locale=es-ES")
    assert resp.status_code == 200
    html = resp.data.decode()
    assert "Una noche de quietud" in html
    assert "El polinizador alado" in html


# ── Completeness gate (REQ-OPS-021, DD-0023) ────────────────────────────────────


def test_deploy_gates_on_both_i18n_strict_and_page_staleness():
    """SPEC-036's completeness_gate deliverable: a base page whose es-ES
    rendered page is stale/missing blocks deploy, same as a missing tag
    translation -- not just checked at pre-commit. Regression guard: a
    future deploy.sh edit can't silently drop either gate."""
    deploy_sh = (PROJECT_ROOT / "tools" / "ops" / "deploy.sh").read_text(
        encoding="utf-8"
    )
    assert "validate_i18n.py --strict" in deploy_sh
    assert "check_page_staleness.py" in deploy_sh
