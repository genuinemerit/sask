"""Asset retrieval engine: descriptor/payload split (DD-0016, SPEC-026).

Flask-free. resolve_descriptor() is a pure lookup over config and reads no
payload file; fetch_payload() is the single explicit I/O boundary.
"""

from __future__ import annotations

from sask.config_loader import AppConfig
from sask.logsetup import get_logger
from sask.message import AssetDescriptor, AssetPayload

logger = get_logger(__name__)


class AssetNotFoundError(Exception):
    """Raised when (kind, id) is not present in the asset catalog."""


def resolve_descriptor(kind: str, id: str, config: AppConfig) -> AssetDescriptor:
    """Resolve a typed descriptor for (kind, id); reads no payload file."""
    entry = config.asset_catalog.entries.get((kind, id))
    if entry is None:
        # DD-0020 level_rubric: a catalog miss is normal handled behavior,
        # not a WARNING/ERROR — it's logged as the request's INFO outcome.
        logger.info("asset catalog miss", extra={"kind": kind, "id": id})
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
        logger.info(
            "asset catalog miss",
            extra={"kind": descriptor.kind, "id": descriptor.id},
        )
        raise AssetNotFoundError(
            f"no such asset: kind={descriptor.kind!r} id={descriptor.id!r}"
        )
    payload = AssetPayload(descriptor=descriptor, data=entry.path.read_bytes())
    logger.info(
        "asset served",
        extra={"kind": descriptor.kind, "id": descriptor.id, "size": descriptor.size},
    )
    return payload
