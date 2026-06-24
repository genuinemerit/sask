"""Asset build tool: generates hashed image variants and updates the manifest.

Compiles source artwork under ``assets/local/image`` into publish-ready variants
stored under ``assets/<version>/image/``. Enforces a size budget (<= 1 MiB
per file), maintains a 16:9 aspect for splash assets, embeds a content hash
into filenames for cache-busting, and updates the per-world JSON manifest
with URLs pointing at the generated variants.

Used during asset authoring/publishing, not at application runtime — see
DD-0016 for how the live app actually serves assets (it reads the catalog
under config/, not this manifest).

Example, from the repo root:
    python tools/candidates/build_assets.py --name SmokingHouse.splash.webp
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

from PIL import Image

# --- paths -------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[2]
ASSETS = (REPO_ROOT / "assets").resolve()

VERSION = os.getenv("SASK_ASSETS_VERSION", "v0")
WORLD = os.getenv("SASK_ASSETS_WORLD", "saskantinon")
# Placeholder default — not a guarantee this path is live; override with
# SASK_ASSETS_BASE for a real publish target.
BASE_URL = os.getenv("SASK_ASSETS_BASE", "https://sask.davidstitt.net/assets")

IMAGES_OUT = ASSETS / VERSION / "images"
MANIFEST = ASSETS / f"{WORLD}.manifest.json"

# --- limits --------------------------------------------------------------------
MAX_BYTES = 1_000_000  # 1 MiB budget per generated file

SPLASH_W_H = (1920, 1080)
SPLASH_SIZES = [
    SPLASH_W_H,
    (SPLASH_W_H[0] // 2, SPLASH_W_H[1] // 2),
    (SPLASH_W_H[0] // 4, SPLASH_W_H[1] // 4),
]
SPLASH_THUMB_SIZE = (SPLASH_W_H[0] // 8, SPLASH_W_H[1] // 8)

# Tile/sprite sizes — defined for a future sprite-sheet builder; no caller
# in this file uses them yet.
TILE_W_H = (64, 64)
SPRITE_SIZES = [
    TILE_W_H,
    (TILE_W_H[0] * 2, TILE_W_H[1] * 2),
    (TILE_W_H[0] * 4, TILE_W_H[1] * 4),
]


# --- helpers -------------------------------------------------------------------
def _hash_bytes(p: Path) -> str:
    """Return the first eight characters of the file's SHA-256 digest."""
    return hashlib.sha256(p.read_bytes()).hexdigest()[:8]


def _is_16_9(w: int, h: int) -> bool:
    """Check whether the width/height pair is within ~1% of a 16:9 aspect."""
    return abs((w / h) - (16 / 9)) < 0.01


def _ensure_manifest() -> dict[str, str]:
    """Load the world manifest if readable; fall back to an empty mapping."""
    if MANIFEST.exists():
        try:
            return json.loads(MANIFEST.read_text())
        except (OSError, json.JSONDecodeError):
            pass
    return {}


def _write_manifest(manifest: dict[str, str]) -> None:
    """Persist the manifest mapping to disk with stable formatting."""
    MANIFEST.write_text(json.dumps(manifest, indent=2))


def _finalize_with_hash(tmp: Path, base: str, out_dir: Path) -> str:
    """Rename ``tmp`` to a content-hashed filename and return that name."""
    tag = _hash_bytes(tmp)
    out = out_dir / f"{base}.{tag}.webp"
    tmp.replace(out)
    return out.name


def _webp_save_under_1mb(
    img: Image.Image,
    dst: Path,
    start_q: int = 85,
    min_q: int = 50,
    step: int = 5,
    last_resort_q: int = 40,
) -> tuple[int, int]:
    """Save ``img`` to WebP at ``dst``, lowering quality until it fits the budget.

    Tries ``start_q`` down to ``min_q`` in steps of ``step``, then one final
    attempt at ``last_resort_q`` (below the normal floor) before giving up.
    Returns (quality_used, byte_size); raises RuntimeError if even the last
    resort exceeds MAX_BYTES.
    """
    tmp = dst.with_suffix(".tmp.webp")
    qualities = list(range(start_q, min_q - 1, -step))
    if last_resort_q not in qualities:
        qualities.append(last_resort_q)

    for q in qualities:
        img.save(tmp, format="WEBP", quality=q, method=6)
        size = tmp.stat().st_size
        if size <= MAX_BYTES:
            tmp.replace(dst)
            return q, size

    tmp.unlink(missing_ok=True)
    raise RuntimeError(
        f"{dst.name} exceeds 1MB even at quality {last_resort_q}; "
        "consider using a smaller/cleaner source."
    )


def _save_variant(img: Image.Image, base: str, size: tuple[int, int]) -> str:
    """Resize ``img`` to ``size``, enforce the WebP budget, return the hashed name.

    Thumbs are treated like any other variant and stored under images/.
    """
    variant = img.copy().resize(size, Image.LANCZOS)
    tmp = IMAGES_OUT / f"{base}.webp"
    _webp_save_under_1mb(variant, tmp)
    return _finalize_with_hash(tmp, base, IMAGES_OUT)


def _copy_or_reencode_1x(src: Path, base: str) -> str:
    """Return the hashed 1920x1080 splash variant, reusing or re-encoding ``src``."""
    try:
        if src.suffix.lower() == ".webp" and src.stat().st_size <= MAX_BYTES:
            with Image.open(src) as im:
                size_matches = im.size == SPLASH_SIZES[0]
            if size_matches:
                tmp = IMAGES_OUT / f"{base}.webp"
                tmp.write_bytes(src.read_bytes())
                return _finalize_with_hash(tmp, base, IMAGES_OUT)
    except OSError:
        pass  # fall through to re-encode path

    with Image.open(src) as im:
        im = im.convert("RGBA").convert("RGB")  # drop alpha for splash
        if not _is_16_9(*im.size):
            print(
                f"warn: source aspect {im.size} not 16:9; resizing will distort.",
                file=sys.stderr,
            )
        return _save_variant(im, base, SPLASH_SIZES[0])


# --- build ---------------------------------------------------------------------
def build_splash(src: Path, logical_id: str = "splash.bg") -> None:
    """Create splash derivatives from ``src`` and register them in the manifest."""
    if not src.exists():
        raise FileNotFoundError(src)

    IMAGES_OUT.mkdir(parents=True, exist_ok=True)
    base = f"splash.default.{VERSION}"

    # 1x (1920x1080): reuse an optimized WebP if it already qualifies, else re-encode.
    one_x_name = _copy_or_reencode_1x(src, f"{base}.1920x1080")

    # Open the 1x product as the master for downscales (avoids re-reading src).
    with Image.open(IMAGES_OUT / one_x_name) as master_im:
        master = master_im.convert("RGB")
        half_name = _save_variant(master, f"{base}.960x540", SPLASH_SIZES[1])
        quart_name = _save_variant(master, f"{base}.480x270", SPLASH_SIZES[2])
        thumb_name = _save_variant(master, f"{base}.thumb.320x180", SPLASH_THUMB_SIZE)

    manifest = _ensure_manifest()
    manifest[logical_id] = f"{BASE_URL}/{VERSION}/images/{one_x_name}"
    manifest[f"{logical_id}.960"] = f"{BASE_URL}/{VERSION}/images/{half_name}"
    manifest[f"{logical_id}.480"] = f"{BASE_URL}/{VERSION}/images/{quart_name}"
    manifest[f"{logical_id}.thumb"] = f"{BASE_URL}/{VERSION}/images/{thumb_name}"
    _write_manifest(manifest)

    print("✔ splash variants:")
    print("  1920:", one_x_name)
    print("   960:", half_name)
    print("   480:", quart_name)
    print(" thumb:", thumb_name)
    print("manifest updated:", MANIFEST)


# --- cli -------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    """Configure and return the CLI arguments for the asset builder."""
    parser = argparse.ArgumentParser(
        description="Build splash assets and update the manifest."
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--src",
        type=Path,
        help="Path to source image (any format readable by Pillow).",
    )
    source.add_argument(
        "--name",
        type=str,
        help="Filename under assets/local/ (e.g., splash.webp).",
    )
    parser.add_argument(
        "--logical-id",
        default="splash.bg",
        help="Manifest logical id (default: splash.bg).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source = args.src if args.src else (ASSETS / "local" / args.name).resolve()
    build_splash(source, logical_id=args.logical_id)


if __name__ == "__main__":
    main()
