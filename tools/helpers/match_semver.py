"""Validate version strings against the Semantic Versioning 2.0.0 spec."""

from __future__ import annotations

import re

# The official regex suggested by semver.org for validating a SemVer 2.0.0
# string — see "Is there a suggested reg expression (RegEx) to check a
# SemVer string?" at https://semver.org/. Left as the canonical pattern
# rather than reformatted, since a manual rewrite risks subtly changing a
# well-known, already-correct regex.
_SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(-(0|[1-9A-Za-z-][0-9A-Za-z-]*)(\.[0-9A-Za-z-]+)*)?"
    r"(\+[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?$"
)


def match_semver(version: str) -> bool:
    """Return True if ``version`` is a valid SemVer 2.0.0 string.

    >>> match_semver("1.2.3")
    True
    >>> match_semver("1.2.3-alpha.1+build.5")
    True
    >>> match_semver("1.2")
    False
    """
    return _SEMVER_RE.match(version) is not None
