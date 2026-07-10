"""i18n resolver: tag -> localized text (DD-0022, REQ-FUN-015, SPEC-035).

Flask-free, engine-free, cli-free — imports nothing from sask.web,
sask.calendar, or sask.cli. Locale is always an explicit argument, never
read from a global/env var: sask's web adapter localizes per-request in a
concurrent process, unlike the legacy project's server (which never
localized server-side, and so could get away with a global env-var
lookup — see analysis/legacy-i18n-deepening.md). No separate cache layer:
the catalog is already loaded once at config-load time and held in
AppConfig, same as every other config concern.
"""

from __future__ import annotations

from sask.config_loader import I18nCatalog


def resolve(tag: str, locale: str, catalog: I18nCatalog) -> str:
    """Resolve tag for locale: locale -> base -> raw tag. Never raises.

    Uses explicit None-checks at each rung, not truthiness — an
    intentionally-empty catalog value must not be confused with an absent
    one (the legacy project's "fallback or i18n_id" bug, deliberately not
    repeated here).
    """
    locale_tags = catalog.entries.get(locale)
    if locale_tags is not None:
        text = locale_tags.get(tag)
        if text is not None:
            return text

    if locale != catalog.base_locale:
        base_tags = catalog.entries.get(catalog.base_locale, {})
        text = base_tags.get(tag)
        if text is not None:
            return text

    return tag


def best_locale(
    cookie_value: str | None,
    accept_language_header: str | None,
    catalog: I18nCatalog,
) -> str:
    """Resolve the bound locale for one request/invocation.

    Precedence: an explicit, known cookie value wins outright; otherwise
    the Accept-Language header is matched against the declared locale set
    (a plain prefix/exact match — no external dependency); otherwise the
    catalog's base locale. Pure function, no Flask import, so it's testable
    without a request context.
    """
    if cookie_value in catalog.locales:
        return cookie_value  # type: ignore[return-value]

    if accept_language_header:
        for part in accept_language_header.split(","):
            candidate = part.split(";")[0].strip()
            if candidate in catalog.locales:
                return candidate
            # loose language-only match, e.g. "es" matching "es-ES"
            for locale in catalog.locales:
                if locale.split("-")[0].lower() == candidate.split("-")[0].lower():
                    return locale

    return catalog.base_locale
