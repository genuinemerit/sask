"""Flask application factory for the sask web UI (SPEC-005)."""

from __future__ import annotations

from pathlib import Path

from flask import Flask

from sask.help.loader import discover_topics, index_path

from ..config_loader import load_config


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
    if config_dir is None:
        # src/sask/web/__init__.py → src/sask/web/ → src/sask/ → src/ → root
        config_dir = Path(__file__).resolve().parent.parent.parent.parent / "config"

    if help_dir is None:
        help_dir = (
            Path(__file__).resolve().parent.parent.parent.parent / "docs" / "help"
        )

    template_dir = Path(__file__).resolve().parent / "templates"
    app = Flask(__name__, template_folder=str(template_dir))

    cfg = load_config(config_dir, assets_dir)
    app.config["SASK_CONFIG"] = cfg
    app.config["SASK_HELP_TOPICS"] = discover_topics(help_dir)
    app.config["SASK_HELP_INDEX_PATH"] = index_path(help_dir)

    from .routes import bp

    app.register_blueprint(bp)

    return app
