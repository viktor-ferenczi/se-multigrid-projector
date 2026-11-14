"""What the missing Bugfixes plugin tests share (SE-1548). Remove it with the
warning, see Shared/Utilities/BugfixesCheck.cs."""

from __future__ import annotations

import os
from pathlib import Path

import rig

# Working copies of CometWorks/bugfixes: one with the fix of the block placement
# test (1.19.0 or newer), and optionally an older one
BUGFIXES = Path(os.environ.get("MGP_BUGFIXES_REPO", rig.REPO.parent / "bugfixes"))
OLD_BUGFIXES = os.environ.get("MGP_OLD_BUGFIXES_REPO")

MISSING = "Multigrid Projector: The Bugfixes plugin is not loaded."
TOO_OLD = "Multigrid Projector: The Bugfixes plugin is loaded without its fix"


def plugin(repo, side: str):
    """Bugfixes as a plugin of the rig, side is Client or Server"""
    return ("bugfixes", "bugfixes", Path(repo), f"Bugfixes{side}.xml")


def warnings(log_text: str) -> list[str]:
    return [line for line in log_text.splitlines() if "The Bugfixes plugin" in line]
