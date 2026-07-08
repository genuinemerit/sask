"""Flask application factory for the sask web UI (SPEC-005, SPEC-032)."""

from __future__ import annotations

import time
import uuid
from pathlib import Path

from flask import Flask, g, request

from sask import logsetup
from sask.help.loader import discover_topics, index_path

from ..config_loader import ConfigError, load_config


def create_app(
    config_dir: Path | None = None,
    assets_dir: Path | None = None,
    help_dir: Path | None = None,
) -> Flask:
    """Create and configure the Flask application.

    config_dir defaults to <project_root>/config/, detected by walking up
    from this file's location. assets_dir is forwarded as-is to
    load_config(), which derives its own default (a sibling of config_dir)
    when omitted — see config_loader.load_config's docstring. help_dir
    defaults to <project_root>/docs/help/, same walk-up depth as config_dir.
    """
    # Called first (SPEC-032): installs the "sask" logger's stdout handler
    # before Flask's own app.logger is first touched, so Flask's automatic
    # unhandled-exception logging (app.logger, a child of "sask") lands on
    # the same JSON handler instead of Flask installing its own default one.
    logsetup.configure()
    logger = logsetup.get_logger(__name__)

    if config_dir is None:
        # src/sask/web/__init__.py → src/sask/web/ → src/sask/ → src/ → root
        config_dir = Path(__file__).resolve().parent.parent.parent.parent / "config"

    if help_dir is None:
        help_dir = (
            Path(__file__).resolve().parent.parent.parent.parent / "docs" / "help"
        )

    template_dir = Path(__file__).resolve().parent / "templates"
    app = Flask(__name__, template_folder=str(template_dir))

    try:
        cfg = load_config(config_dir, assets_dir)
    except ConfigError:
        # DD-0020 level_rubric: the app cannot serve without config — CRITICAL,
        # then the process exits (the exception still propagates).
        logger.critical("config load failed; app cannot serve")
        raise
    app.config["SASK_CONFIG"] = cfg
    app.config["SASK_HELP_TOPICS"] = discover_topics(help_dir)
    app.config["SASK_HELP_INDEX_PATH"] = index_path(help_dir)

    @app.before_request
    def _bind_request_context() -> None:
        g.sask_request_started = time.perf_counter()
        g.sask_context_token = logsetup.bind_context(
            request_id=uuid.uuid4().hex,
            method=request.method,
            path=request.path,
        )

    @app.after_request
    def _log_request_finished(response):
        duration_s = time.perf_counter() - g.sask_request_started
        logger.info(
            "request finished",
            extra={
                "status": response.status_code,
                "duration_s": round(duration_s, 3),
            },
        )
        return response

    @app.teardown_request
    def _reset_request_context(exc: BaseException | None = None) -> None:
        # Runs even when the view raised — unbinds the context so it never
        # leaks into the next request handled by the same worker. Genuinely
        # unhandled exceptions are logged once by Flask's own app.logger
        # (this module's logger, per SPEC-032 adapter_logging), which still
        # carries the bound request_id/method/path since teardown fires
        # after that logging, not before.
        token = getattr(g, "sask_context_token", None)
        if token is not None:
            logsetup.reset_context(token)

    from .routes import bp

    app.register_blueprint(bp)

    return app
