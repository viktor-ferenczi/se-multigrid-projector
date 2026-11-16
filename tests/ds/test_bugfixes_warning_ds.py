"""The server's warning about a missing Bugfixes plugin (SE-1548): a line in
the server's log on every start without Bugfixes, none with it. No client
joins. See ../test_bugfixes_warning.py for the client's side.

Remove this file with the warning, see Shared/Utilities/BugfixesCheck.cs.
"""

from __future__ import annotations

import time

import pytest

import ds_rig
import rig
from bugfixes_warning import BUGFIXES, MISSING, OLD_BUGFIXES, TOO_OLD, plugin, warnings


def server_warnings(plugins=()) -> list[str]:
    """Starts the server and gives the warnings of its first seconds. The
    plugin checks on its first update, which comes with the world running."""
    ds_rig.stop_server()
    ds_rig.prepare_server(["small"], plugins=plugins)
    for log in ds_rig.SERVER_DATA.glob(ds_rig.GAME_LOG_GLOB):
        log.unlink()
    ds_rig.start_server()
    try:
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if lines := warnings(ds_rig.server_log_text()):
                return lines
            time.sleep(1)
        assert "Multigrid Projector: Loaded" in ds_rig.server_log_text()
        return []
    finally:
        rig.ARTIFACTS.mkdir(parents=True, exist_ok=True)
        with open(rig.ARTIFACTS / "test_bugfixes_warning_ds.server.log", "a") as file:
            file.write(ds_rig.server_log_text())
        ds_rig.stop_server()


def test_server_without_bugfixes_warns():
    lines = server_warnings()
    assert len(lines) == 1 and MISSING in lines[0], lines
    assert "Warning" in lines[0] or "WARNING" in lines[0], lines[0]


def test_server_with_bugfixes_is_quiet():
    if not BUGFIXES.exists():
        pytest.skip("No Bugfixes working copy, set MGP_BUGFIXES_REPO")
    assert server_warnings([plugin(BUGFIXES, "Server")]) == []


def test_server_with_bugfixes_without_the_fix_warns():
    if not OLD_BUGFIXES:
        pytest.skip("MGP_OLD_BUGFIXES_REPO: a Bugfixes working copy before 1.19.0")
    lines = server_warnings([plugin(OLD_BUGFIXES, "Server")])
    assert len(lines) == 1 and TOO_OLD in lines[0], lines
