"""Flask application factory for the sask resource server."""

import os
from pathlib import Path

from flask import Flask, Response, request

from .auth import extract_bearer_token, is_valid_token, load_tokens
from .manifest import load_manifest
from .translators import error_to_json, health_to_json, resource_to_bytes

_SUPPORTED_KINDS = frozenset({"image", "json", "audio"})


def _tokens_path() -> Path | None:
    """Return the tokens file path from the environment, or ``None``."""
    val = os.environ.get("SASK_TOKENS_PATH")
    return Path(val) if val else None


def _manifest_path() -> Path | None:
    """Return the manifest file path from the environment, or ``None``."""
    val = os.environ.get("SASK_MANIFEST_PATH")
    return Path(val) if val else None


def create_app() -> Flask:
    """Create and return a configured Flask application instance.

    Configuration is read from environment variables at request time so that
    the app can be instantiated without any environment set up (useful for
    testing via monkeypatching).

    Returns:
        A :class:`flask.Flask` instance with all routes registered.
    """
    flask_app = Flask(__name__)

    @flask_app.route("/health")
    def health() -> Response:
        """Return a JSON health-check response with no authentication required."""
        return Response(health_to_json(), status=200, mimetype="application/json")

    @flask_app.route("/resource/<kind>/<resource_id>")
    def get_resource(kind: str, resource_id: str) -> Response:
        """Serve a resource identified by *kind* and *resource_id*.

        Requires a valid bearer token in the ``Authorization`` header.
        Returns 401 for a missing or invalid token, 404 for an unknown kind
        or unknown resource id, and 404 if the file is absent from disk.
        """
        token = extract_bearer_token(request.headers.get("Authorization"))
        tokens = load_tokens(_tokens_path())
        if token is None or not is_valid_token(token, tokens):
            return Response(
                error_to_json("Unauthorized"),
                status=401,
                mimetype="application/json",
            )

        if kind not in _SUPPORTED_KINDS:
            return Response(
                error_to_json(f"Unknown kind: {kind}"),
                status=404,
                mimetype="application/json",
            )

        resources = load_manifest(_manifest_path())
        entry = resources.get((kind, resource_id))
        if entry is None:
            return Response(
                error_to_json(f"Resource not found: {kind}/{resource_id}"),
                status=404,
                mimetype="application/json",
            )

        try:
            data = resource_to_bytes(entry)
        except FileNotFoundError:
            return Response(
                error_to_json(f"Resource file missing: {kind}/{resource_id}"),
                status=404,
                mimetype="application/json",
            )

        return Response(data, status=200, mimetype=entry.content_type)

    return flask_app


app = create_app()
