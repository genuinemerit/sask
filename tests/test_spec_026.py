"""SPEC-026 tests — asset retrieval engine, catalog config, HTML adapter.

Covers:
  - asset catalog load success; ConfigError on a missing payload file, a
    malformed entry, a duplicate (kind, id), and a path with no top-level
    subdirectory to derive kind from
  - accurate size captured from the stat
  - resolve_descriptor returns the right descriptor, reads no payload file,
    raises AssetNotFoundError on a miss
  - fetch_payload returns correct bytes/content_type, round-trips with the
    descriptor, raises AssetNotFoundError on a miss
  - AssetDescriptor/AssetPayload pass message.validate()
  - layer-purity: asset/retrieval.py imports no flask
  - HTML adapter: 200 + content_type for a real (kind, id); 404 for unknown
"""

from __future__ import annotations

import ast
import shutil
from pathlib import Path

import pytest

from sask.asset.retrieval import AssetNotFoundError, fetch_payload, resolve_descriptor
from sask.config_loader import ConfigError, load_config
from sask.message import AssetDescriptor, AssetPayload, validate
from sask.web import create_app

PROJECT_ROOT = Path(__file__).parent.parent
REAL_CONFIG = PROJECT_ROOT / "config"


# ── Fixtures ──────────────────────────────────────────────────────────────────


def _write_toml(path: Path, content: str) -> None:
    path.write_text(content)


def _minimal_catalog_dirs(tmp_path: Path) -> tuple[Path, Path]:
    """Real config copied into tmp_path/config, plus a tmp_path/assets tree
    with a few tiny synthetic payload files and a catalog overriding
    config/asset_catalog_data.toml. Returns (config_dir, assets_dir).
    """
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    for f in REAL_CONFIG.glob("*.toml"):
        shutil.copy(f, config_dir / f.name)

    assets_dir = tmp_path / "assets"
    (assets_dir / "image").mkdir(parents=True)
    (assets_dir / "audio").mkdir(parents=True)
    (assets_dir / "image" / "a.bin").write_bytes(b"AAAA")
    (assets_dir / "image" / "b.bin").write_bytes(b"BBBBBB")
    # .jpg extension, content_type text/plain — deliberately mismatched, to
    # exercise content_type independence from extension without lying to a
    # real client (see SPEC-026's config_data deliverable note).
    (assets_dir / "audio" / "c.jpg").write_bytes(b"CC")

    _write_toml(
        config_dir / "asset_catalog_data.toml",
        """
[[asset]]
id = "a"
content_type = "application/octet-stream"
path = "image/a.bin"

[[asset]]
id = "b"
content_type = "application/octet-stream"
path = "image/b.bin"

[[asset]]
id = "c"
content_type = "text/plain"
path = "audio/c.jpg"
""",
    )
    return config_dir, assets_dir


@pytest.fixture
def catalog_dirs(tmp_path):
    return _minimal_catalog_dirs(tmp_path)


@pytest.fixture(scope="module")
def app():
    return create_app(config_dir=REAL_CONFIG)


@pytest.fixture(scope="module")
def client(app):
    return app.test_client()


# ── Catalog loading and validation ─────────────────────────────────────────────


def test_catalog_load_success(catalog_dirs):
    config_dir, assets_dir = catalog_dirs
    cfg = load_config(config_dir, assets_dir)
    assert len(cfg.asset_catalog.entries) == 3
    assert ("image", "a") in cfg.asset_catalog.entries


def test_two_ids_share_a_kind(catalog_dirs):
    config_dir, assets_dir = catalog_dirs
    cfg = load_config(config_dir, assets_dir)
    assert cfg.asset_catalog.entries[("image", "a")].kind == "image"
    assert cfg.asset_catalog.entries[("image", "b")].kind == "image"


def test_content_type_independent_of_extension(catalog_dirs):
    config_dir, assets_dir = catalog_dirs
    cfg = load_config(config_dir, assets_dir)
    entry = cfg.asset_catalog.entries[("audio", "c")]
    assert entry.content_type == "text/plain"  # path is audio/c.jpg


def test_accurate_size_from_stat(catalog_dirs):
    config_dir, assets_dir = catalog_dirs
    cfg = load_config(config_dir, assets_dir)
    assert cfg.asset_catalog.entries[("image", "a")].size == 4  # b"AAAA"


def test_missing_payload_file_raises(catalog_dirs):
    config_dir, assets_dir = catalog_dirs
    (assets_dir / "image" / "a.bin").unlink()
    with pytest.raises(ConfigError, match="not found"):
        load_config(config_dir, assets_dir)


def test_malformed_entry_missing_required_field_raises(catalog_dirs):
    config_dir, assets_dir = catalog_dirs
    _write_toml(
        config_dir / "asset_catalog_data.toml",
        '[[asset]]\nid = "a"\npath = "image/a.bin"\n',  # missing content_type
    )
    with pytest.raises(ConfigError, match="content_type"):
        load_config(config_dir, assets_dir)


def test_duplicate_kind_id_raises(catalog_dirs):
    config_dir, assets_dir = catalog_dirs
    _write_toml(
        config_dir / "asset_catalog_data.toml",
        """
[[asset]]
id = "a"
content_type = "application/octet-stream"
path = "image/a.bin"

[[asset]]
id = "a"
content_type = "application/octet-stream"
path = "image/b.bin"
""",
    )
    with pytest.raises(ConfigError, match="duplicate"):
        load_config(config_dir, assets_dir)


def test_path_with_no_subdirectory_raises(catalog_dirs):
    config_dir, assets_dir = catalog_dirs
    (assets_dir / "flat.bin").write_bytes(b"X")
    _write_toml(
        config_dir / "asset_catalog_data.toml",
        '[[asset]]\nid = "flat"\ncontent_type = "application/octet-stream"\n'
        'path = "flat.bin"\n',
    )
    with pytest.raises(ConfigError, match="top-level subdirectory"):
        load_config(config_dir, assets_dir)


# ── resolve_descriptor / fetch_payload ─────────────────────────────────────────


def test_resolve_descriptor_returns_correct_descriptor(catalog_dirs):
    config_dir, assets_dir = catalog_dirs
    cfg = load_config(config_dir, assets_dir)
    d = resolve_descriptor("image", "a", cfg)
    assert d.kind == "image"
    assert d.id == "a"
    assert d.content_type == "application/octet-stream"
    assert d.size == 4


def test_resolve_descriptor_reads_no_payload_file(catalog_dirs):
    config_dir, assets_dir = catalog_dirs
    cfg = load_config(config_dir, assets_dir)
    # Delete the payload file *after* catalog load: if resolve_descriptor
    # tried to read it, this would raise FileNotFoundError instead.
    (assets_dir / "image" / "a.bin").unlink()
    d = resolve_descriptor("image", "a", cfg)
    assert d.size == 4  # captured at load time, not re-read


def test_resolve_descriptor_raises_on_miss(catalog_dirs):
    config_dir, assets_dir = catalog_dirs
    cfg = load_config(config_dir, assets_dir)
    with pytest.raises(AssetNotFoundError):
        resolve_descriptor("image", "nope", cfg)


def test_fetch_payload_round_trips(catalog_dirs):
    config_dir, assets_dir = catalog_dirs
    cfg = load_config(config_dir, assets_dir)
    d = resolve_descriptor("image", "a", cfg)
    p = fetch_payload(d, cfg)
    assert p.data == b"AAAA"
    assert p.descriptor == d


def test_fetch_payload_raises_on_miss(catalog_dirs):
    config_dir, assets_dir = catalog_dirs
    cfg = load_config(config_dir, assets_dir)
    bogus = AssetDescriptor(kind="image", id="ghost", content_type="x", size=0)
    with pytest.raises(AssetNotFoundError):
        fetch_payload(bogus, cfg)


# ── Message-unit validate() ────────────────────────────────────────────────────


def test_asset_descriptor_passes_validate():
    d = AssetDescriptor(kind="image", id="a", content_type="image/webp", size=10)
    assert validate(d) == []


def test_asset_payload_passes_validate():
    d = AssetDescriptor(kind="image", id="a", content_type="image/webp", size=10)
    p = AssetPayload(descriptor=d, data=b"x" * 10)
    assert validate(p) == []


# ── Layer-purity: asset/retrieval.py must not import flask ─────────────────────


def _flask_imports_in(path: Path) -> list[str]:
    """Return a list of flask-related import lines found in path."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if "flask" in alias.name.lower():
                    found.append(f"import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if "flask" in module.lower():
                found.append(f"from {module} import ...")
    return found


def test_asset_module_has_no_flask_import():
    hits = _flask_imports_in(PROJECT_ROOT / "src" / "sask" / "asset" / "retrieval.py")
    assert hits == [], f"src/sask/asset/retrieval.py contains flask imports: {hits}"


# ── HTML adapter ────────────────────────────────────────────────────────────────


def test_get_asset_returns_200_with_content_type(client):
    resp = client.get("/asset/image/splash.bg")
    assert resp.status_code == 200
    assert resp.content_type == "image/webp"
    assert len(resp.data) > 0


def test_get_unknown_asset_returns_404(client):
    resp = client.get("/asset/image/does-not-exist")
    assert resp.status_code == 404
