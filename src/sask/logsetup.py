"""Shared-spine structured logging (DD-0020, REQ-OPS-019, REQ-SEC-004, SPEC-032).

Pure infrastructure: imports no Flask and no engine domain code. Engine
modules call get_logger(__name__) and log context-free (SPEC-032
engine_logging); the web adapter binds per-request fields via
bind_context()/reset_context() around each request (SPEC-032
adapter_logging). configure() installs a JSON-to-stdout handler on the
"sask" logger once, at create_app() time — never at import time.
"""

from __future__ import annotations

import contextvars
import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import IO

# ── TRACE level (below DEBUG; DD-0020 level_rubric) ────────────────────────

TRACE = 5
logging.addLevelName(TRACE, "TRACE")


def _trace(self: logging.Logger, message: str, *args: object, **kwargs: object) -> None:
    if self.isEnabledFor(TRACE):
        self._log(TRACE, message, args, **kwargs)


logging.Logger.trace = _trace  # type: ignore[attr-defined]


def get_logger(name: str) -> logging.Logger:
    """Return a logger under the "sask" hierarchy (SPEC-032 spine_module)."""
    return logging.getLogger(name)


# ── Level/range filter ──────────────────────────────────────────────────────


class LevelRangeFilter(logging.Filter):
    """Pass only records whose level falls within [min_level, max_level]."""

    def __init__(
        self,
        min_level: int = logging.NOTSET,
        max_level: int = logging.CRITICAL,
    ) -> None:
        super().__init__()
        self.min_level = min_level
        self.max_level = max_level

    def filter(self, record: logging.LogRecord) -> bool:
        return self.min_level <= record.levelno <= self.max_level


# ── Request context binding (SPEC-032 adapter_logging) ─────────────────────

_request_context: contextvars.ContextVar[dict[str, object]] = contextvars.ContextVar(
    "sask_request_context", default={}
)


def bind_context(**fields: object) -> contextvars.Token[dict[str, object]]:
    """Bind fields (request id, method, path, ...) onto the current context.

    Returns a token; pass it to reset_context() (e.g. in a Flask
    teardown_request hook) so bound fields never leak into a later request
    handled by the same worker.
    """
    updated = dict(_request_context.get())
    updated.update(fields)
    return _request_context.set(updated)


def reset_context(token: contextvars.Token[dict[str, object]]) -> None:
    _request_context.reset(token)


def current_context() -> dict[str, object]:
    return dict(_request_context.get())


# ── Redaction (REQ-SEC-004) ──────────────────────────────────────────────────

# Field-name markers: any field whose key contains one of these
# (case-insensitive) has its value redacted regardless of layer. Extend
# this set as new secret-bearing fields appear — no call-site changes
# needed.
SENSITIVE_KEY_MARKERS: frozenset[str] = frozenset(
    {"token", "password", "passwd", "secret", "api_key", "apikey", "authorization"}
)

# Env var names whose current values are scrubbed from message text and
# any string-valued field, in case a secret value is logged outside a
# named field (e.g. interpolated into a free-text message).
SENSITIVE_ENV_VARS: tuple[str, ...] = ("DIGITALOCEAN_TOKEN",)

REDACTED = "***REDACTED***"


def _is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    return any(marker in lowered for marker in SENSITIVE_KEY_MARKERS)


def _redact_known_values(text: str) -> str:
    for var in SENSITIVE_ENV_VARS:
        secret = os.environ.get(var)
        if secret:
            text = text.replace(secret, REDACTED)
    return text


def _redact_value(key: str, value: object) -> object:
    if _is_sensitive_key(key):
        return REDACTED
    if isinstance(value, dict):
        return redact_fields(value)
    if isinstance(value, str):
        return _redact_known_values(value)
    return value


def redact_fields(fields: dict[str, object]) -> dict[str, object]:
    """Return a copy of fields with sensitive keys/values redacted."""
    return {key: _redact_value(key, value) for key, value in fields.items()}


# ── JSON formatter ───────────────────────────────────────────────────────────

_STANDARD_RECORD_KEYS = frozenset(
    logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys()
) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    """Emit one structured JSON object per line (SPEC-032 spine_module)."""

    def format(self, record: logging.LogRecord) -> str:
        fields: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        fields.update(current_context())
        fields.update(
            {k: v for k, v in record.__dict__.items() if k not in _STANDARD_RECORD_KEYS}
        )
        if record.exc_info:
            fields["exception"] = self.formatException(record.exc_info)
        return json.dumps(redact_fields(fields), default=str)


# ── configure() ───────────────────────────────────────────────────────────────

_configured = False


def _resolve_level(level: str | int) -> int:
    if isinstance(level, int):
        return level
    name = level.strip().upper()
    resolved = logging.getLevelName(name)
    if not isinstance(resolved, int):
        raise ValueError(f"unknown log level: {level!r}")
    return resolved


def configure(level: str | int | None = None, stream: IO[str] | None = None) -> None:
    """Install the JSON-to-stdout handler on the "sask" logger.

    Idempotent: a second call is a no-op, so create_app() can call this
    unconditionally without double-installing handlers. level defaults to
    the SASK_LOG_LEVEL env var (DD-0020 production_threshold), then INFO.
    """
    global _configured
    if _configured:
        return

    resolved_level = _resolve_level(
        level if level is not None else os.environ.get("SASK_LOG_LEVEL", "INFO")
    )

    logger = logging.getLogger("sask")
    logger.setLevel(resolved_level)
    handler = logging.StreamHandler(stream if stream is not None else sys.stdout)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    logger.propagate = False
    _configured = True


def reset() -> None:
    """Remove installed handlers and clear configured state.

    Not used by application code — configure() is idempotent by design.
    Exists so tests can un-configure the "sask" logger between cases.
    """
    global _configured
    logger = logging.getLogger("sask")
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
    _configured = False
