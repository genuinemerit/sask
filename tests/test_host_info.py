"""Pytest suite for tools/helpers/host_info.py."""

from __future__ import annotations

import socket
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools" / "helpers"))
import host_info  # noqa: E402

_EXPECTED_KEYS = {
    "platform",
    "platform-release",
    "platform-version",
    "architecture",
    "python-version",
    "hostname",
    "ip-address",
    "mac-address",
    "processor",
    "ram",
}


# ── Happy path ──────────────────────────────────────────────────────────────


def test_returns_all_expected_keys():
    assert host_info.sys_info().keys() == _EXPECTED_KEYS


def test_values_are_non_empty_strings():
    # "processor" is exempt: platform.processor() legitimately returns ""
    # on many Linux distros (it doesn't parse /proc/cpuinfo).
    info = host_info.sys_info()
    for key, value in info.items():
        assert isinstance(value, str)
        if key == "processor":
            continue
        assert value != "", f"{key} was empty"


def test_mac_address_shape():
    info = host_info.sys_info()
    assert len(info["mac-address"].split(":")) == 6


def test_ram_shape():
    info = host_info.sys_info()
    assert info["ram"].endswith(" GB")


# ── Unhappy path ────────────────────────────────────────────────────────────


def test_socket_failure_is_caught_not_raised(monkeypatch):
    def boom(_hostname):
        raise OSError("network unreachable")

    monkeypatch.setattr(socket, "gethostbyname", boom)

    info = host_info.sys_info()  # must not raise

    assert "ip-address" not in info
    # fields collected before the failing call are still present
    assert info["platform"] == host_info.platform.system()


def test_partial_failure_logs_instead_of_raising(monkeypatch, caplog):
    monkeypatch.setattr(
        socket, "gethostbyname", lambda _h: (_ for _ in ()).throw(OSError("boom"))
    )

    with caplog.at_level("ERROR"):
        host_info.sys_info()

    assert "Failed to collect full host diagnostics" in caplog.text
