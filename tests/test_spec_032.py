"""SPEC-032 tests — structured logging spine facility (Phase 1).

Covers the shared-spine module (src/sask/logsetup.py) only:
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
"""

from __future__ import annotations

import io
import json
import logging

import pytest

from sask import logsetup


@pytest.fixture(autouse=True)
def _reset_logsetup():
    logsetup.reset()
    yield
    logsetup.reset()


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
