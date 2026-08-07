"""Dev-side API reference builder (DD-0027, SPEC-040).

Generates the structural facts (endpoint list, parameters, response shapes,
error codes) from the code + config, weaves them with the hand-authored
prose source (docs/api_reference_src/reference.toml), captures worked
examples by exercising a real (in-process, no network) Flask app, and
renders the result to committed static HTML (human) and JSON (machine)
artifacts served at /api/reference via DD-0026 content negotiation.

Structural facts and never hand-authored here:
  - Endpoint list + per-endpoint parameters: config/endpoint_params.toml
    (DD-0028/SPEC-041), via AppConfig.endpoint_params -- the single source
    the routes themselves parse/validate from.
  - Response shape per endpoint: derived by walking a captured real "basic"
    example response (guaranteed accurate, cannot drift independently of
    the example -- reusing the capture step rather than a second, separate
    introspection of json_render.py).
  - Error code catalog: every "error.*" i18n tag actually reachable from
    the five JSON-capable route functions (an AST scan of routes.py's
    index/moons/planets/sky/ephemeris function bodies + all of params.py,
    which those five functions are the only callers of) -- excludes tags
    used only by non-JSON-capable routes (/help, /ephemeris/download).

This script runs ONLY in dev (poetry run), never at deploy -- mirrors
tools/dev/build_i18n_pages.py's dev/prod split (DD-0023).

Usage:
    poetry run python3 tools/dev/build_api_reference.py
"""

from __future__ import annotations

import ast
import html
import json
import re
import sys
import tomllib
from pathlib import Path
from typing import Any

_ERROR_TAG_RE = re.compile(r"error\.[a-z_]+")

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))

from sask.config_loader import AppConfig  # noqa: E402
from sask.web import create_app  # noqa: E402

PROSE_SRC = ROOT / "docs" / "api_reference_src" / "reference.toml"
OUT_DIR = ROOT / "docs" / "api_reference"
ROUTES_SRC = ROOT / "src" / "sask" / "web" / "routes.py"
PARAMS_SRC = ROOT / "src" / "sask" / "web" / "params.py"

# The five JSON-capable route functions (DD-0028's scope) -- everything
# else in routes.py (health, get_asset, ephemeris_download, the /help
# family) is deliberately excluded from the error-code AST scan below.
_JSON_ROUTE_FUNCS = {"index", "moons", "planets", "sky", "ephemeris"}

REFERENCE_PULSE = 86_400  # Astro day 2, 00:00:00 -- a stable, arbitrary moment

_EXAMPLE_QUERIES: dict[str, dict[str, str]] = {
    "/": {
        "basic": f"/?pulse={REFERENCE_PULSE}&format=json",
        "localized": f"/?pulse={REFERENCE_PULSE}&format=json&locale=es-ES",
        "error": "/?format=json",
    },
    "/moons": {
        "basic": f"/moons?pulse={REFERENCE_PULSE}&format=json",
        "localized": f"/moons?pulse={REFERENCE_PULSE}&format=json&locale=es-ES",
        "error": "/moons?pulse=not_a_number&format=json",
    },
    "/planets": {
        "basic": f"/planets?pulse={REFERENCE_PULSE}&format=json",
        "localized": f"/planets?pulse={REFERENCE_PULSE}&format=json&locale=es-ES",
        "error": "/planets?pulse=not_a_number&format=json",
    },
    "/sky": {
        "basic": f"/sky?pulse={REFERENCE_PULSE}&format=json",
        "localized": f"/sky?pulse={REFERENCE_PULSE}&format=json&locale=es-ES",
        "error": "/sky?pulse=not_a_number&format=json",
    },
    "/ephemeris": {
        "basic": (
            f"/ephemeris?start_pulse={REFERENCE_PULSE}&step_minutes=60"
            "&duration_days=1&format=json"
        ),
        "localized": (
            f"/ephemeris?start_pulse={REFERENCE_PULSE}&step_minutes=60"
            "&duration_days=1&format=json&locale=es-ES"
        ),
        "error": (
            f"/ephemeris?start_pulse={REFERENCE_PULSE}&step_minutes=1"
            "&duration_days=1&format=json"
        ),
    },
}


# ── Structural facts: error-code catalog (AST scan) ─────────────────────────


def _error_tags_in_functions(source: str, func_names: set[str] | None) -> set[str]:
    """String constants matching "error.*" inside the named top-level
    functions (func_names=None scans the whole module)."""
    tree = ast.parse(source)
    tags: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            if func_names is not None and node.name not in func_names:
                continue
            for sub in ast.walk(node):
                if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                    if _ERROR_TAG_RE.fullmatch(sub.value):
                        tags.add(sub.value)
            if func_names is not None:
                continue
    # Whole-module scan (func_names=None): also catch module-level constants.
    if func_names is None:
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if _ERROR_TAG_RE.fullmatch(node.value):
                    tags.add(node.value)
    return tags


def _error_catalog(cfg: AppConfig) -> list[dict[str, str]]:
    routes_tags = _error_tags_in_functions(
        ROUTES_SRC.read_text(encoding="utf-8"), _JSON_ROUTE_FUNCS
    )
    params_tags = _error_tags_in_functions(PARAMS_SRC.read_text(encoding="utf-8"), None)
    en = cfg.i18n.entries["en-US"]
    catalog = [
        {
            "code": tag.removeprefix("error."),
            "message_template": en[tag],
        }
        for tag in sorted(routes_tags | params_tags)
    ]
    return catalog


# ── Structural facts: per-endpoint parameters ────────────────────────────────


def _param_fact(wire_name: str, spec) -> dict[str, Any]:
    fact: dict[str, Any] = {
        "name": wire_name,
        "type": spec.type,
        "required": spec.required,
        "description": spec.description,
    }
    if spec.default is not None:
        fact["default"] = spec.default
    if spec.constraints:
        fact["constraints"] = spec.constraints
    return fact


def _endpoint_facts(path: str, cfg: AppConfig) -> dict[str, Any]:
    declaration = cfg.endpoint_params
    ep = declaration.endpoints[path]
    facts: dict[str, Any] = {
        "parameters": [
            _param_fact(name, declaration.params[name]) for name in ep.scalars
        ]
    }
    if ep.moment_group:
        group = declaration.moment_groups[ep.moment_group]
        facts["moment_resolution"] = {
            "prefix": ep.moment_group_prefix or None,
            "priority": list(group.priority),
            "branches": {
                branch: [
                    _param_fact(
                        f"{ep.moment_group_prefix}{field}", declaration.params[field]
                    )
                    for field in group.fields[branch]
                ]
                for branch in group.priority
            },
        }
    return facts


def _shared_parameters(cfg: AppConfig) -> list[dict[str, Any]]:
    declaration = cfg.endpoint_params
    return [_param_fact(name, declaration.params[name]) for name in declaration.globals]


def _ephemeris_throttle(cfg: AppConfig) -> dict[str, int]:
    eph = cfg.ephemeris
    ppd = cfg.time_constants.pulses_per_day
    return {
        "step_floor_pulses": eph.step_floor_pulses,
        "step_floor_minutes": eph.step_floor_pulses // 60,
        "range_cap_pulses": eph.range_cap_pulses,
        "range_cap_days": eph.range_cap_pulses // ppd,
    }


# ── Structural facts: examples + response shape (captured, not guessed) ─────


def _shape_of(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _shape_of(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_shape_of(value[0])] if value else []
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    if value is None:
        return "null"
    return "unknown"  # pragma: no cover -- JSON has no other value kinds


def _capture_examples(app, path: str) -> dict[str, dict[str, Any]]:
    client = app.test_client()
    captured = {}
    for kind, query in _EXAMPLE_QUERIES[path].items():
        resp = client.get(query)
        captured[kind] = {
            "request": query,
            "status": resp.status_code,
            "body": resp.get_json(),
        }
    return captured


# ── Assemble + render ────────────────────────────────────────────────────────


def _load_prose() -> dict[str, Any]:
    with PROSE_SRC.open("rb") as fh:
        return tomllib.load(fh)


def build_reference(app) -> tuple[str, str]:
    """Pure of file I/O beyond the prose-source read: returns (html, json)
    text. Exercises `app` in-process only (no network) to capture examples.
    Raises KeyError if a declared endpoint has no prose description (the
    SPEC-040 human-flag case -- a genuinely new endpoint/param needs a
    one-line description added to docs/api_reference_src/reference.toml).
    """
    cfg: AppConfig = app.config["SASK_CONFIG"]
    prose = _load_prose()

    endpoints: dict[str, Any] = {}
    for path in sorted(cfg.endpoint_params.endpoints):
        try:
            description = prose["endpoints"][path]["description"].strip()
        except KeyError as exc:
            raise KeyError(
                f"docs/api_reference_src/reference.toml: no [endpoints.{path!r}] "
                "description -- add one (SPEC-040 human-flag: a new endpoint "
                "needs a hand-authored description before the reference can "
                "be built)"
            ) from exc
        facts = _endpoint_facts(path, cfg)
        examples = _capture_examples(app, path)
        entry: dict[str, Any] = {
            "description": description,
            **facts,
            "response_shape": _shape_of(examples["basic"]["body"]),
            "examples": examples,
        }
        if path == "/ephemeris":
            entry["throttle"] = _ephemeris_throttle(cfg)
        endpoints[path] = entry

    data = {
        "negotiation": prose["concepts"]["negotiation"].strip(),
        "locale": prose["concepts"]["locale"].strip(),
        "id_label": prose["concepts"]["id_label"].strip(),
        "temporal_contract": prose["concepts"]["temporal_contract"].strip(),
        "error_envelope": prose["concepts"]["error_envelope"].strip(),
        "integration_guidance": prose["concepts"]["integration_guidance"].strip(),
        "locales": list(cfg.i18n.locales),
        "shared_parameters": _shared_parameters(cfg),
        "endpoints": endpoints,
        "error_codes": _error_catalog(cfg),
    }

    return _render_html(data), json.dumps(data, indent=2, sort_keys=False) + "\n"


def _render_html(data: dict[str, Any]) -> str:
    def esc(s: Any) -> str:
        return html.escape(str(s))

    def pre(obj: Any) -> str:
        return f"<pre>{esc(json.dumps(obj, indent=2))}</pre>"

    def param_row(p: dict[str, Any]) -> str:
        extra = []
        if "default" in p:
            extra.append(f"default={esc(p['default'])}")
        if "constraints" in p:
            extra.append(esc(json.dumps(p["constraints"])))
        extra_text = f" ({'; '.join(extra)})" if extra else ""
        req = "required" if p["required"] else "optional"
        return (
            f"<tr><td><code>{esc(p['name'])}</code></td><td>{esc(p['type'])}</td>"
            f"<td>{req}</td><td>{esc(p['description'])}{extra_text}</td></tr>"
        )

    def params_table(params: list[dict[str, Any]]) -> str:
        if not params:
            return ""
        rows = "\n".join(param_row(p) for p in params)
        return (
            "<table><thead><tr><th>name</th><th>type</th><th>required</th>"
            f"<th>description</th></tr></thead><tbody>{rows}</tbody></table>"
        )

    nav = "\n".join(
        f'<li><a href="#{esc(path)}">{esc(path)}</a></li>' for path in data["endpoints"]
    )

    endpoint_sections = []
    for path, entry in data["endpoints"].items():
        anchor = esc(path)
        section = [f'<section id="{anchor}"><h2><code>{esc(path)}</code></h2>']
        section.append(f"<p>{esc(entry['description'])}</p>")
        if "throttle" in entry:
            section.append(
                "<p><strong>Throttle:</strong> step_minutes floor "
                f"{entry['throttle']['step_floor_minutes']} min; range cap "
                f"{entry['throttle']['range_cap_days']} days.</p>"
            )
        if entry.get("moment_resolution"):
            mr = entry["moment_resolution"]
            prefix = mr["prefix"] or "(none)"
            section.append(
                f"<p><strong>Moment resolution</strong> (prefix: <code>{esc(prefix)}</code>) "
                f"— first populated branch wins, in priority order: "
                f"{' &gt; '.join(esc(b) for b in mr['priority'])}.</p>"
            )
            for branch in mr["priority"]:
                section.append(f"<h4>{esc(branch)}</h4>")
                section.append(params_table(mr["branches"][branch]))
        if entry["parameters"]:
            section.append("<h3>Parameters</h3>")
            section.append(params_table(entry["parameters"]))
        section.append("<h3>Response shape</h3>")
        section.append(pre(entry["response_shape"]))
        section.append("<h3>Examples</h3>")
        for kind, ex in entry["examples"].items():
            section.append(f"<h4>{esc(kind)}</h4>")
            section.append(
                f"<p><code>GET {esc(ex['request'])}</code> → {ex['status']}</p>"
            )
            section.append(pre(ex["body"]))
        section.append("</section>")
        endpoint_sections.append("\n".join(section))

    error_rows = "\n".join(
        f"<tr><td><code>{esc(c['code'])}</code></td><td>{esc(c['message_template'])}</td></tr>"
        for c in data["error_codes"]
    )

    shared_params_table = params_table(data["shared_parameters"])

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>sask API reference</title>
<style>
body {{ font-family: system-ui, sans-serif; max-width: 60rem; margin: 2rem auto; padding: 0 1rem; line-height: 1.5; color: #1a1a1a; }}
code, pre {{ font-family: ui-monospace, monospace; }}
pre {{ background: #f4f4f4; padding: 0.75rem; overflow-x: auto; border-radius: 4px; font-size: 0.85rem; }}
table {{ border-collapse: collapse; width: 100%; margin: 0.5rem 0 1rem; }}
th, td {{ border: 1px solid #ddd; padding: 0.4rem 0.6rem; text-align: left; vertical-align: top; }}
th {{ background: #f0f0f0; }}
nav ul {{ list-style: none; padding: 0; display: flex; gap: 1rem; flex-wrap: wrap; }}
section {{ margin-top: 2.5rem; border-top: 1px solid #ddd; padding-top: 1rem; }}
h1 {{ margin-bottom: 0.25rem; }}
</style>
</head>
<body>
<h1>sask API reference</h1>

<nav><ul>{nav}</ul></nav>

<section id="concepts">
<h2>Concepts</h2>
<h3>Content negotiation</h3><p>{esc(data["negotiation"])}</p>
<h3>Locale</h3><p>{esc(data["locale"])}</p>
<p>Served locales: {", ".join(f"<code>{esc(loc)}</code>" for loc in data["locales"])}</p>
<h3>The {{id, label}} convention</h3><p>{esc(data["id_label"])}</p>
<h3>Temporal contract</h3><p>{esc(data["temporal_contract"])}</p>
<h3>Error envelope</h3><p>{esc(data["error_envelope"])}</p>
<h3>Integration guidance</h3><p>{esc(data["integration_guidance"])}</p>
</section>

<section id="shared-parameters">
<h2>Shared parameters (every endpoint)</h2>
{shared_params_table}
</section>

{"".join(endpoint_sections)}

<section id="error-codes">
<h2>Error codes</h2>
<table><thead><tr><th>code</th><th>message template</th></tr></thead>
<tbody>{error_rows}</tbody></table>
</section>

</body>
</html>
"""


def main() -> int:
    app = create_app(config_dir=ROOT / "config")
    html_text, json_text = build_reference(app)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "index.html").write_text(html_text, encoding="utf-8")
    (OUT_DIR / "reference.json").write_text(json_text, encoding="utf-8")
    print(f"wrote {(OUT_DIR / 'index.html').relative_to(ROOT)}")
    print(f"wrote {(OUT_DIR / 'reference.json').relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
