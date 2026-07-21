"""`sask host_info` (DD-0021, DD-0025, REQ-FUN-017, REQ-SEC-006, SPEC-038).

Player-tier: broadly accessible, so scope is deliberately NON-SENSITIVE
host/platform diagnostics only. A separate, independent implementation from
tools/helpers/host_info.py (which stays untouched for its own callers/tests)
— that script also collects hostname/IP/MAC via psutil/socket/uuid, which
REQ-SEC-006 forbids for a player-tier command ("no internal addresses...").
Those fields are never collected here, not filtered out after the fact.
"""

from __future__ import annotations

import platform

import psutil

from ..formatting import echo_dict


def _collect() -> dict[str, str]:
    ram_gb = round(psutil.virtual_memory().total / (1024.0**3))
    return {
        "platform": platform.system(),
        "platform-release": platform.release(),
        "platform-version": platform.version(),
        "architecture": platform.machine(),
        "python-version": platform.python_version(),
        "processor": platform.processor(),
        "ram": f"{ram_gb} GB",
    }


def host_info() -> None:
    """Show non-sensitive host/platform diagnostics.

    Example usage:
    `sask host_info`
    """
    echo_dict("Host info", _collect())
