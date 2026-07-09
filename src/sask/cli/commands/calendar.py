"""`sask convert --pulse N` (DD-0021, REQ-FUN-014, SPEC-034).

Wraps sask.calendar.pulse.pulse_info() — the same function the web `/` route
calls — returning the same PulseInfo message unit. The message-seam proof
against the astronomy engine: a second, non-web consumer of the identical
clean-room function.
"""

from __future__ import annotations

import dataclasses

import typer

from sask.calendar.pulse import pulse_info

from .._config import resolve_and_load_config
from ..formatting import echo_dict


def convert(
    pulse: int = typer.Option(..., "--pulse", "-p", help="Raw pulse value"),
) -> None:
    """Show Astro day, day-pulse offset, and orbital position for a pulse.

    Example usage:
    `sask convert --pulse 0`
    `sask convert -p 12345`
    """
    cfg = resolve_and_load_config()
    info = pulse_info(pulse, cfg)
    echo_dict("Pulse info", dataclasses.asdict(info))
