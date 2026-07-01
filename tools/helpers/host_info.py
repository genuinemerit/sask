"""Collect basic host/platform diagnostics as a JSON string.

Renamed from platform.py: that name shadowed the stdlib ``platform`` module
this file imports. Originally risky because ``tools/`` was on ``pythonpath``
(see pyproject.toml's pytest config); since the SPEC-029 tools/ reorg,
pythonpath only lists tools/ops and tools/dev, and this file lives in
tools/helpers/, so it's no longer pythonpath-exposed at all — the rename
stands as the correct name regardless.
"""

from __future__ import annotations

import json
import logging
import platform
import re
import socket
import uuid

import psutil

logger = logging.getLogger(__name__)


def sys_info() -> dict[str, str]:
    """Return host platform/network/hardware diagnostics.

    Keys: platform, platform-release, platform-version, architecture,
    python-version, hostname, ip-address, mac-address, processor, ram.
    Returns whatever was collected before any failure, logged via the
    module logger rather than raised — this is a best-effort diagnostic,
    not a contract callers should depend on completing fully.
    """
    info: dict[str, str] = {}
    try:
        info["platform"] = platform.system()
        info["platform-release"] = platform.release()
        info["platform-version"] = platform.version()
        info["architecture"] = platform.machine()
        info["python-version"] = platform.python_version()
        info["hostname"] = socket.gethostname()
        info["ip-address"] = socket.gethostbyname(socket.gethostname())
        # Format the 48-bit node id from uuid.getnode() as a colon-separated
        # MAC address, e.g. "aa:bb:cc:dd:ee:ff".
        info["mac-address"] = ":".join(re.findall("..", f"{uuid.getnode():012x}"))
        info["processor"] = platform.processor()
        ram_gb = round(psutil.virtual_memory().total / (1024.0**3))
        info["ram"] = f"{ram_gb} GB"
    except OSError:
        logger.exception("Failed to collect full host diagnostics")

    return info


if __name__ == "__main__":
    print(json.dumps(sys_info()))
