"""Shared pytest fixtures for sask tests.

All fixtures that involve file I/O write into pytest's ``tmp_path`` so that
tests are fully isolated and leave no artefacts behind.
"""

from pathlib import Path

import pytest

# Token used across auth and resource tests.
_VALID_TOKEN = "test-valid-token-abc123xyz"

_MANIFEST_TOML = """\
[[resource]]
kind = "image"
id = "splash"
path = "images/splash.png"
content_type = "image/png"

[[resource]]
kind = "json"
id = "scenario-001"
path = "json/scenario-001.json"
content_type = "application/json"

[[resource]]
kind = "audio"
id = "ambient-loop"
path = "audio/ambient-loop.mp3"
content_type = "audio/mpeg"

[[resource]]
kind = "audio"
id = "ambient-video"
path = "audio/ambient-video.mp4"
content_type = "video/mp4"
"""


@pytest.fixture
def valid_token() -> str:
    """Return the bearer token accepted by the test server."""
    return _VALID_TOKEN


@pytest.fixture
def tokens_file(tmp_path: Path) -> Path:
    """Write a temporary tokens TOML file containing one valid token.

    Args:
        tmp_path: Pytest-supplied temporary directory.

    Returns:
        Path to the written tokens file.
    """
    path = tmp_path / "tokens.toml"
    path.write_text(
        f'[[token]]\nid = "test"\ntoken = "{_VALID_TOKEN}"\n',
        encoding="utf-8",
    )
    return path


@pytest.fixture
def resource_files(tmp_path: Path) -> Path:
    """Create minimal placeholder resource files and a manifest in *tmp_path*.

    The files are not valid media files but are sufficient for testing HTTP
    delivery (status codes, content types, non-empty bodies).

    Args:
        tmp_path: Pytest-supplied temporary directory.

    Returns:
        Path to the ``resources/`` sub-directory containing the manifest and
        placeholder files.
    """
    resources = tmp_path / "resources"
    (resources / "images").mkdir(parents=True)
    (resources / "json").mkdir(parents=True)
    (resources / "audio").mkdir(parents=True)

    # Minimal placeholder bytes — content validity is not under test here.
    (resources / "images" / "splash.png").write_bytes(
        b"\x89PNG\r\n\x1a\n" + b"\x00" * 12
    )
    (resources / "json" / "scenario-001.json").write_text(
        '{"id": "scenario-001", "name": "Test Scenario"}', encoding="utf-8"
    )
    (resources / "audio" / "ambient-loop.mp3").write_bytes(
        b"\xff\xfb\x90\x00" + b"\x00" * 100
    )
    (resources / "audio" / "ambient-video.mp4").write_bytes(
        b"\x00\x00\x00\x20ftyp" + b"\x00" * 100
    )

    (resources / "manifest.toml").write_text(_MANIFEST_TOML, encoding="utf-8")
    return resources


@pytest.fixture
def client(
    tokens_file: Path,
    resource_files: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """Yield a Flask test client configured with test tokens and resources.

    Environment variables are patched for the duration of each test and
    restored automatically by ``monkeypatch``.

    Args:
        tokens_file: Temporary tokens TOML file.
        resource_files: Temporary resources directory containing the manifest.
        monkeypatch: Pytest monkeypatch fixture.

    Yields:
        A :class:`flask.testing.FlaskClient` ready for use in tests.
    """
    monkeypatch.setenv("SASK_TOKENS_PATH", str(tokens_file))
    monkeypatch.setenv("SASK_MANIFEST_PATH", str(resource_files / "manifest.toml"))

    from sask.app import create_app  # noqa: PLC0415

    flask_app = create_app()
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as test_client:
        yield test_client
