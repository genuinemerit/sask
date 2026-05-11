"""Resource manifest loading for sask."""

import os
from dataclasses import dataclass
from pathlib import Path

import tomllib

_DEFAULT_MANIFEST_PATH = Path("resources/manifest.toml")


@dataclass
class ResourceEntry:
    """A single resource record from the manifest.

    Attributes:
        kind: Resource kind string (``image``, ``json``, or ``audio``).
        id: Resource identifier used in the URL path.
        path: Absolute path to the resource file on disk.
        content_type: MIME type to set on the HTTP response.
    """

    kind: str
    id: str
    path: Path
    content_type: str


def load_manifest(path: Path | None = None) -> dict[tuple[str, str], ResourceEntry]:
    """Load the resource manifest from a TOML file.

    Args:
        path: Path to the manifest file. When ``None``, falls back to the
            ``SASK_MANIFEST_PATH`` environment variable, then to
            ``./resources/manifest.toml``.

    Returns:
        Mapping from ``(kind, id)`` tuples to :class:`ResourceEntry` objects.
        Resource entries whose files do not exist on disk are still included;
        the caller decides how to handle a missing file.

    Raises:
        FileNotFoundError: If the manifest file itself does not exist.
        tomllib.TOMLDecodeError: If the file is not valid TOML.
    """
    if path is None:
        env = os.environ.get("SASK_MANIFEST_PATH")
        path = Path(env) if env else _DEFAULT_MANIFEST_PATH
    with path.open("rb") as fh:
        data = tomllib.load(fh)
    base_dir = path.parent
    resources: dict[tuple[str, str], ResourceEntry] = {}
    for entry in data.get("resource", []):
        resource = ResourceEntry(
            kind=entry["kind"],
            id=entry["id"],
            path=base_dir / entry["path"],
            content_type=entry["content_type"],
        )
        resources[(resource.kind, resource.id)] = resource
    return resources
