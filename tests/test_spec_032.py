"""SPEC-032 tests — structured logging: spine, engine, layer purity.

Phase 1 — the shared-spine module (src/sask/logsetup.py):
  - JsonFormatter emits one valid JSON object per line with the expected
    base fields
  - TRACE is registered below DEBUG and Logger.trace() respects it
  - LevelRangeFilter passes/rejects records by level range
  - bind_context()/reset_context(): fields appear on records emitted within
    the bound context, are absent outside it, and don't leak across a
    reset
  - redact_fields(): a sensitive-keyed field is redacted; an added
    sensitive key name is redacted without call-site changes; a known
    secret value appearing in free text is scrubbed (REQ-SEC-004)
  - configure() is idempotent (does not double-install handlers) and
    resolves level from the SASK_LOG_LEVEL env var

Phase 2 — engine-layer instrumentation (context-free; DD-0020 level rubric):
  - config_loader.load_config() logs one INFO record with counts
  - calendar.ephemeris.get_sky_series() logs one INFO record with
    step_count + duration on a normal request, WARNING when the duration
    nears/exceeds the ~5s soft budget
  - asset.retrieval: a served asset logs INFO; a catalog miss logs INFO
    (never WARNING/ERROR) from both resolve_descriptor() and fetch_payload()
  - layer purity: engine modules (config_loader.py, calendar/*.py,
    asset/*.py) import no Flask and no sask.web (mirrors the existing
    Flask-free engine test, extended to the adapter's context module)

Phase 3 — web adapter (create_app request-context binding, SPEC-032
adapter_logging), end to end against real captured stdout (capsys), since
configure() writes to sys.stdout by default:
  - create_app() configures logging before Flask's own app.logger is
    touched; a ConfigError during create_app logs CRITICAL and still
    propagates
  - a normal request logs "request finished" at INFO with request_id,
    method, path, status, duration
  - an engine outcome line (e.g. an asset catalog miss on a 404) and the
    adapter's "request finished" line share one request_id; the 404 stays
    INFO on both, never WARNING/ERROR
  - a genuinely unhandled exception is logged exactly once, at ERROR, by
    Flask's own app.logger (a child of "sask"), carrying the bound
    request_id/method/path
  - request context does not leak between two sequential requests
  - "config loaded" (emitted outside any request, at create_app time)
    carries no request context
"""

from __future__ import annotations

import ast
import io
import json
import logging
from pathlib import Path

import pytest

from sask import logsetup
from sask.asset.retrieval import fetch_payload, resolve_descriptor
from sask.calendar.ephemeris import get_sky_series
from sask.config_loader import ConfigError, load_config
from sask.web import create_app

PROJECT_ROOT = Path(__file__).parent.parent
REAL_CONFIG = PROJECT_ROOT / "config"
CONFIG = load_config(REAL_CONFIG)


def _json_lines(text: str) -> list[dict]:
    return [json.loads(line) for line in text.strip().splitlines() if line.strip()]


def _reset_all_sask_loggers() -> None:
    """Blank-slate every "sask"/"sask.*" logger: no handlers, propagate=True.

    _make_logger_with_buffer() below mutates real, cached logger singletons
    (e.g. "sask.config_loader") directly, since that's exactly what
    src/sask modules obtain via get_logger(__name__). Without resetting
    them between tests, a stale handler/propagate=False from one test
    silently swallows another test's records (they'd go to an abandoned
    buffer instead of propagating to "sask"'s real handler).
    """
    for name, candidate in list(logging.Logger.manager.loggerDict.items()):
        if isinstance(candidate, logging.Logger) and (
            name == "sask" or name.startswith("sask.")
        ):
            candidate.handlers = []
            candidate.propagate = True
            candidate.setLevel(logging.NOTSET)


@pytest.fixture(autouse=True)
def _reset_logsetup():
    _reset_all_sask_loggers()
    logsetup.reset()
    yield
    logsetup.reset()
    _reset_all_sask_loggers()


def _make_logger_with_buffer(
    name: str, level: int = logging.DEBUG
) -> tuple[logging.Logger, io.StringIO]:
    buffer = io.StringIO()
    handler = logging.StreamHandler(buffer)
    handler.setFormatter(logsetup.JsonFormatter())
    logger = logging.getLogger(name)
    logger.handlers = [handler]
    logger.setLevel(level)
    logger.propagate = False
    return logger, buffer


# ── JsonFormatter ─────────────────────────────────────────────────────────────


def test_formatter_emits_one_json_object_per_line():
    logger, buffer = _make_logger_with_buffer("sask.test.formatter")
    logger.info("app ready")

    lines = buffer.getvalue().strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["level"] == "INFO"
    assert record["logger"] == "sask.test.formatter"
    assert record["message"] == "app ready"
    assert "timestamp" in record


def test_formatter_includes_extra_fields():
    logger, buffer = _make_logger_with_buffer("sask.test.extra")
    logger.info("request finished", extra={"status": 200, "duration": 0.012})

    record = json.loads(buffer.getvalue().strip())
    assert record["status"] == 200
    assert record["duration"] == 0.012


# ── TRACE level ───────────────────────────────────────────────────────────────


def test_trace_registered_below_debug():
    assert logsetup.TRACE < logging.DEBUG
    assert logging.getLevelName(logsetup.TRACE) == "TRACE"


def test_trace_call_respects_level():
    logger, buffer = _make_logger_with_buffer("sask.test.trace", level=logging.DEBUG)
    logger.trace("per-record detail")  # type: ignore[attr-defined]
    assert buffer.getvalue() == ""

    logger.setLevel(logsetup.TRACE)
    logger.trace("per-record detail")  # type: ignore[attr-defined]
    record = json.loads(buffer.getvalue().strip())
    assert record["level"] == "TRACE"


# ── LevelRangeFilter ──────────────────────────────────────────────────────────


def _record(level: int) -> logging.LogRecord:
    return logging.LogRecord("sask.test", level, __file__, 1, "msg", (), None)


def test_level_range_filter_bounds():
    f = logsetup.LevelRangeFilter(min_level=logging.INFO, max_level=logging.ERROR)
    assert not f.filter(_record(logging.DEBUG))
    assert f.filter(_record(logging.INFO))
    assert f.filter(_record(logging.ERROR))
    assert not f.filter(_record(logging.CRITICAL))


# ── Context binding ───────────────────────────────────────────────────────────


def test_bound_context_appears_on_records_within_scope():
    logger, buffer = _make_logger_with_buffer("sask.test.context")
    token = logsetup.bind_context(request_id="req-1", method="GET", path="/")
    try:
        logger.info("request finished")
    finally:
        logsetup.reset_context(token)

    record = json.loads(buffer.getvalue().strip())
    assert record["request_id"] == "req-1"
    assert record["method"] == "GET"
    assert record["path"] == "/"


def test_context_absent_outside_bound_scope():
    logger, buffer = _make_logger_with_buffer("sask.test.no_context")
    logger.info("engine outcome")

    record = json.loads(buffer.getvalue().strip())
    assert "request_id" not in record


def test_context_does_not_leak_after_reset():
    logger, buffer = _make_logger_with_buffer("sask.test.leak")
    token = logsetup.bind_context(request_id="req-1")
    logsetup.reset_context(token)

    logger.info("next request's engine call")
    record = json.loads(buffer.getvalue().strip())
    assert "request_id" not in record


# ── Redaction (REQ-SEC-004) ──────────────────────────────────────────────────


def test_redact_fields_scrubs_sensitive_key():
    fields = {"message": "auth attempt", "token": "abc123"}
    redacted = logsetup.redact_fields(fields)
    assert redacted["token"] == logsetup.REDACTED
    assert redacted["message"] == "auth attempt"


def test_redact_fields_extensible_without_call_site_changes(monkeypatch):
    monkeypatch.setitem(
        logsetup.__dict__,
        "SENSITIVE_KEY_MARKERS",
        logsetup.SENSITIVE_KEY_MARKERS | {"new_secret_field"},
    )
    redacted = logsetup.redact_fields({"new_secret_field": "leaked-value"})
    assert redacted["new_secret_field"] == logsetup.REDACTED


def test_redact_known_env_value_in_message_text(monkeypatch):
    monkeypatch.setenv("DIGITALOCEAN_TOKEN", "dop_v1_supersecret")
    logger, buffer = _make_logger_with_buffer("sask.test.redact_message")
    logger.info("provisioning failed with token dop_v1_supersecret")

    output = buffer.getvalue()
    assert "dop_v1_supersecret" not in output
    assert logsetup.REDACTED in output


def test_redact_nested_dict_field():
    fields = {"context": {"password": "hunter2", "user": "dave"}}
    redacted = logsetup.redact_fields(fields)
    assert redacted["context"]["password"] == logsetup.REDACTED
    assert redacted["context"]["user"] == "dave"


# ── configure() ───────────────────────────────────────────────────────────────


def test_configure_is_idempotent():
    logsetup.configure(level="DEBUG", stream=io.StringIO())
    logsetup.configure(level="DEBUG", stream=io.StringIO())

    logger = logging.getLogger("sask")
    assert len(logger.handlers) == 1


def test_configure_resolves_level_from_env(monkeypatch):
    monkeypatch.setenv("SASK_LOG_LEVEL", "WARNING")
    logsetup.configure(stream=io.StringIO())

    logger = logging.getLogger("sask")
    assert logger.level == logging.WARNING


def test_configure_writes_json_to_given_stream():
    buffer = io.StringIO()
    logsetup.configure(level="INFO", stream=buffer)

    logsetup.get_logger("sask.test.configured").info("app ready")
    record = json.loads(buffer.getvalue().strip())
    assert record["message"] == "app ready"


# ── Engine instrumentation (Phase 2) ────────────────────────────────────────

_STORY = CONFIG.timeline.story_now_pulse
_STEP = CONFIG.ephemeris.step_floor_pulses


def test_config_load_logs_info_with_counts():
    logger, buffer = _make_logger_with_buffer("sask.config_loader")
    load_config(REAL_CONFIG)

    record = json.loads(buffer.getvalue().strip())
    assert record["level"] == "INFO"
    assert record["message"] == "config loaded"
    assert record["bodies"] == len(CONFIG.bodies)
    assert record["assets"] == len(CONFIG.asset_catalog.entries)


def test_ephemeris_normal_request_logs_info():
    logger, buffer = _make_logger_with_buffer("sask.calendar.ephemeris")
    get_sky_series(_STORY, _STORY, _STEP, CONFIG)

    record = json.loads(buffer.getvalue().strip())
    assert record["level"] == "INFO"
    assert record["step_count"] == 1
    assert record["duration_s"] < 1.0


def test_ephemeris_near_budget_logs_warning(monkeypatch):
    values = iter([0.0, 4.6])
    monkeypatch.setattr(
        "sask.calendar.ephemeris.time.perf_counter", lambda: next(values)
    )
    logger, buffer = _make_logger_with_buffer("sask.calendar.ephemeris")
    get_sky_series(_STORY, _STORY, _STEP, CONFIG)

    record = json.loads(buffer.getvalue().strip())
    assert record["level"] == "WARNING"
    assert record["duration_s"] == 4.6


def test_asset_served_logs_info():
    logger, buffer = _make_logger_with_buffer("sask.asset.retrieval")
    descriptor = resolve_descriptor("image", "splash.bg", CONFIG)
    fetch_payload(descriptor, CONFIG)

    record = json.loads(buffer.getvalue().strip())
    assert record["level"] == "INFO"
    assert record["message"] == "asset served"
    assert record["kind"] == "image"
    assert record["id"] == "splash.bg"


def test_asset_catalog_miss_logs_info_not_warning():
    from sask.asset.retrieval import AssetNotFoundError

    logger, buffer = _make_logger_with_buffer("sask.asset.retrieval")
    with pytest.raises(AssetNotFoundError):
        resolve_descriptor("image", "does-not-exist", CONFIG)

    record = json.loads(buffer.getvalue().strip())
    assert record["level"] == "INFO"
    assert record["message"] == "asset catalog miss"


def test_fetch_payload_miss_logs_info_independently():
    from sask.asset.retrieval import AssetNotFoundError
    from sask.message import AssetDescriptor

    logger, buffer = _make_logger_with_buffer("sask.asset.retrieval")
    ghost = AssetDescriptor(kind="image", id="does-not-exist", content_type="x", size=0)
    with pytest.raises(AssetNotFoundError):
        fetch_payload(ghost, CONFIG)

    record = json.loads(buffer.getvalue().strip())
    assert record["level"] == "INFO"
    assert record["message"] == "asset catalog miss"


# ── Layer purity: engine imports no Flask, no sask.web ──────────────────────

_ENGINE_FILES = (
    [PROJECT_ROOT / "src" / "sask" / "config_loader.py"]
    + sorted((PROJECT_ROOT / "src" / "sask" / "calendar").glob("*.py"))
    + sorted((PROJECT_ROOT / "src" / "sask" / "asset").glob("*.py"))
)


def _forbidden_imports_in(path: Path) -> list[str]:
    """Return flask / sask.web import lines found in path (SPEC-032)."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                lowered = alias.name.lower()
                if "flask" in lowered or lowered.startswith("sask.web"):
                    found.append(f"import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            module = (node.module or "").lower()
            if "flask" in module or module.startswith("sask.web"):
                found.append(f"from {module} import ...")
    return found


@pytest.mark.parametrize("path", _ENGINE_FILES, ids=lambda p: p.name)
def test_engine_modules_import_no_flask_or_web(path: Path):
    assert _forbidden_imports_in(path) == []


# ── Web adapter (Phase 3) ─────────────────────────────────────────────────────


def test_config_loaded_log_has_no_request_context(capsys):
    capsys.readouterr()
    create_app(config_dir=REAL_CONFIG)

    records = _json_lines(capsys.readouterr().out)
    config_line = next(r for r in records if r["message"] == "config loaded")
    assert "request_id" not in config_line


def test_config_error_logs_critical_and_reraises(capsys, tmp_path):
    capsys.readouterr()
    with pytest.raises(ConfigError):
        create_app(config_dir=tmp_path)

    records = _json_lines(capsys.readouterr().out)
    critical = [r for r in records if r["level"] == "CRITICAL"]
    assert len(critical) == 1
    assert critical[0]["message"] == "config load failed; app cannot serve"


def test_request_finished_logs_info_with_context(capsys):
    app = create_app(config_dir=REAL_CONFIG)
    client = app.test_client()
    capsys.readouterr()

    resp = client.get("/")
    assert resp.status_code == 200

    records = _json_lines(capsys.readouterr().out)
    finished = [r for r in records if r["message"] == "request finished"]
    assert len(finished) == 1
    assert finished[0]["level"] == "INFO"
    assert finished[0]["method"] == "GET"
    assert finished[0]["path"] == "/"
    assert finished[0]["status"] == 200
    assert isinstance(finished[0]["duration_s"], (int, float))
    assert finished[0]["request_id"]


def test_engine_and_adapter_lines_share_request_id_on_404(capsys):
    app = create_app(config_dir=REAL_CONFIG)
    client = app.test_client()
    capsys.readouterr()

    resp = client.get("/asset/image/does-not-exist")
    assert resp.status_code == 404

    records = _json_lines(capsys.readouterr().out)
    miss = next(r for r in records if r["message"] == "asset catalog miss")
    finished = next(r for r in records if r["message"] == "request finished")
    assert miss["request_id"] == finished["request_id"]
    assert miss["level"] == "INFO"
    assert finished["level"] == "INFO"
    assert finished["status"] == 404


def test_unhandled_exception_logs_error_once_with_context(capsys):
    app = create_app(config_dir=REAL_CONFIG)

    @app.route("/__test_boom__")
    def _boom():
        raise RuntimeError("synthetic failure for testing")

    client = app.test_client()
    capsys.readouterr()

    resp = client.get("/__test_boom__")
    assert resp.status_code == 500

    records = _json_lines(capsys.readouterr().out)
    errors = [r for r in records if r["level"] == "ERROR"]
    assert len(errors) == 1
    assert "RuntimeError" in errors[0]["exception"]
    assert errors[0]["request_id"]

    finished = [r for r in records if r["message"] == "request finished"]
    assert len(finished) == 1
    assert finished[0]["status"] == 500
    assert finished[0]["request_id"] == errors[0]["request_id"]


def test_context_does_not_leak_between_requests(capsys):
    app = create_app(config_dir=REAL_CONFIG)
    client = app.test_client()

    capsys.readouterr()
    client.get("/")
    id1 = next(
        r["request_id"]
        for r in _json_lines(capsys.readouterr().out)
        if r["message"] == "request finished"
    )

    capsys.readouterr()
    client.get("/")
    id2 = next(
        r["request_id"]
        for r in _json_lines(capsys.readouterr().out)
        if r["message"] == "request finished"
    )

    assert id1 != id2
