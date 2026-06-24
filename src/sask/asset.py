"""Asset retrieval engine: descriptor/payload split (DD-0016, SPEC-026).

Flask-free. resolve_descriptor() is a pure lookup over config and reads no
payload file; fetch_payload() is the single explicit I/O boundary.
"""

from __future__ import annotations

from .config_loader import AppConfig
from .message import AssetDescriptor, AssetPayload


class AssetNotFoundError(Exception):
    """Raised when (kind, id) is not present in the asset catalog."""


def resolve_descriptor(kind: str, id: str, config: AppConfig) -> AssetDescriptor:
    """Resolve a typed descriptor for (kind, id); reads no payload file."""
    entry = config.asset_catalog.entries.get((kind, id))
    if entry is None:
        raise AssetNotFoundError(f"no such asset: kind={kind!r} id={id!r}")
    return AssetDescriptor(
        kind=entry.kind,
        id=entry.id,
        content_type=entry.content_type,
        size=entry.size,
    )


def fetch_payload(descriptor: AssetDescriptor, config: AppConfig) -> AssetPayload:
    """Re-resolve the catalog entry and read its payload bytes (the one I/O call)."""
    entry = config.asset_catalog.entries.get((descriptor.kind, descriptor.id))
    if entry is None:
        raise AssetNotFoundError(
            f"no such asset: kind={descriptor.kind!r} id={descriptor.id!r}"
        )
    return AssetPayload(descriptor=descriptor, data=entry.path.read_bytes())
