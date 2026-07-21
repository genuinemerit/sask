"""`sask asset list` / `sask asset info <kind> <id>` (DD-0021, REQ-FUN-014, SPEC-034).

Descriptor-only (DD-0016's descriptor/payload split): these commands never
call fetch_payload() — no payload bytes are read for inventory/examination.
"""

from __future__ import annotations

import dataclasses

import typer
from rich.console import Console
from rich.table import Table

from sask.asset.retrieval import AssetNotFoundError, resolve_descriptor
from sask.message import AssetDescriptor

from .._config import resolve_and_load_config
from ..formatting import echo_dict

app = typer.Typer(help="Asset catalog inspection (descriptor-only, no payload reads)")

_console = Console()


@app.command("list")
def list_assets() -> None:
    """List every asset in the catalog (descriptor fields only, no payload reads).

    Example usage:
    `sask asset list`
    """
    cfg = resolve_and_load_config()
    entries = cfg.asset_catalog.entries
    if not entries:
        typer.echo("No assets in the catalog.")
        return
    descriptors = [
        AssetDescriptor(
            kind=entry.kind,
            id=entry.id,
            content_type=entry.content_type,
            size=entry.size,
        )
        for entry in sorted(entries.values(), key=lambda e: (e.kind, e.id))
    ]

    if not _console.is_terminal:
        for d in descriptors:
            typer.echo(f"{d.kind}/{d.id}  ({d.content_type}, {d.size}B)")
        return

    table = Table(title="Assets")
    table.add_column("kind/id", style="bold cyan")
    table.add_column("content type")
    table.add_column("size", justify="right")
    for d in descriptors:
        table.add_row(f"{d.kind}/{d.id}", d.content_type, f"{d.size}B")
    _console.print(table)


@app.command("info")
def asset_info(kind: str, id: str) -> None:
    """Show descriptor fields for one asset (no payload read).

    Example usage:
    `sask asset info image splash.bg`
    """
    cfg = resolve_and_load_config()
    try:
        descriptor = resolve_descriptor(kind, id, cfg)
    except AssetNotFoundError:
        typer.echo(f"Error: no such asset: kind={kind!r} id={id!r}", err=True)
        raise typer.Exit(1) from None
    echo_dict(f"Asset {kind}/{id}", dataclasses.asdict(descriptor))
