"""The client's warning about a missing Bugfixes plugin (SE-1548).

The game leaks Havok memory in its block placement test, and only the Bugfixes
plugin fixes that (ds/test_havok_leak_ds.py). Without Bugfixes the client logs a
warning on every start and shows a dialog on the main menu, at most once a week.
It keeps the time of the dialog in its config file, which the tests set instead
of waiting.

Every test starts the client anew and stays on the main menu. With MGP_RENDER=1
the dialog is saved to tests/artifacts/bugfixes-dialog.png.

Remove this file with the warning, see Shared/Utilities/BugfixesCheck.cs.
"""

from __future__ import annotations

import json
import os
import re
import time

import pytest

import rig
from bugfixes_warning import BUGFIXES, MISSING, OLD_BUGFIXES, TOO_OLD, plugin, warnings

CLIENT = rig.Client(0)
CONFIG = CLIENT.appdata / "Storage" / "MultigridProjector.cfg"
CAPTION = "Bugfixes Plugin Needed"
WEEK = 7 * 24 * 3600


def start(shown: int | None, plugins=()):
    """Starts the client with the dialog last shown at that Unix time, None for
    a client without a config file, and waits for the main menu"""
    rig.stop(CLIENT)
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    if shown is None:
        CONFIG.unlink(missing_ok=True)
    else:
        CONFIG.write_text(
            '<?xml version="1.0" encoding="utf-8"?><Config>'
            f"<BugfixesWarningShownUnixTime>{shown}</BugfixesWarningShownUnixTime>"
            "</Config>",
            encoding="utf-8",
        )
    rig.launch(CLIENT, plugins=plugins)
    remote = rig.wait_api(CLIENT)
    deadline = time.monotonic() + 300
    while not any("MainMenu" in s.get("type", "") for s in screens(remote)):
        assert time.monotonic() < deadline, "No main menu"
        time.sleep(1)
    return remote


def screens(remote) -> list[dict]:
    try:
        return remote.list_screens()
    except Exception:  # noqa: BLE001 -- the game is still starting
        return []


def dialog(remote) -> int | None:
    """Index of the dialog's screen"""
    for screen in screens(remote):
        if screen.get("type") == "MyGuiScreenMessageBox" and CAPTION in json.dumps(
            remote.get_controls(screen["index"])
        ):
            return screen["index"]
    return None


def wait_dialog(remote, timeout: float = 60.0) -> int:
    deadline = time.monotonic() + timeout
    while (index := dialog(remote)) is None:
        assert time.monotonic() < deadline, "The dialog did not come up"
        time.sleep(1)
    return index


def no_dialog(remote, seconds: float = 10.0) -> bool:
    """The main menu stays free of the dialog. It comes up within a frame of
    the main menu getting the focus, so a few seconds are plenty."""
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if dialog(remote) is not None:
            return False
        time.sleep(1)
    return "MainMenu" in remote.get_focused_screen().get("type", "")


def shown_time() -> int:
    match = re.search(r"<BugfixesWarningShownUnixTime>(\d+)<", CONFIG.read_text())
    return int(match.group(1)) if match else 0


def log_warnings() -> list[str]:
    return warnings(CLIENT.log.read_text(errors="replace"))


@pytest.fixture(autouse=True)
def stop_the_client():
    yield
    if os.environ.get("MGP_KEEP") != "1":
        rig.stop(CLIENT)


def test_first_start_without_bugfixes_warns_and_shows_the_dialog():
    before = int(time.time())
    remote = start(None)
    index = wait_dialog(remote)

    lines = log_warnings()
    assert len(lines) == 1 and MISSING in lines[0], lines
    assert "Warning" in lines[0] or "WARNING" in lines[0], lines[0]
    assert before <= shown_time() <= int(time.time())
    text = json.dumps(remote.get_controls(index))
    assert "The Bugfixes plugin is not enabled" in text

    if rig.RENDER:
        time.sleep(2)
        rig.ARTIFACTS.mkdir(parents=True, exist_ok=True)
        (rig.ARTIFACTS / "bugfixes-dialog.png").write_bytes(remote.screenshot_bytes())

    remote.control_click(text="OK", screen=index)
    assert no_dialog(remote, 5)


def test_next_start_warns_without_the_dialog():
    shown = int(time.time()) - 3600
    remote = start(shown)
    assert no_dialog(remote)
    lines = log_warnings()
    assert len(lines) == 1 and MISSING in lines[0], lines
    assert shown_time() == shown


def test_dialog_comes_back_after_a_week():
    before = int(time.time())
    remote = start(before - WEEK - 60)
    wait_dialog(remote)
    assert shown_time() >= before


def test_no_dialog_a_bit_less_than_a_week_later():
    shown = int(time.time()) - WEEK + 600
    remote = start(shown)
    assert no_dialog(remote)
    assert shown_time() == shown


def test_with_bugfixes_neither_warning_nor_dialog():
    if not BUGFIXES.exists():
        pytest.skip("No Bugfixes working copy, set MGP_BUGFIXES_REPO")
    remote = start(None, plugins=[plugin(BUGFIXES, "Client")])
    assert no_dialog(remote)
    assert rig.plugin_loaded(CLIENT.log, "Bugfixes: Loading")
    assert log_warnings() == []
    assert not CONFIG.exists() or shown_time() == 0


def test_bugfixes_without_the_fix_warns_and_shows_the_dialog():
    if not OLD_BUGFIXES:
        pytest.skip("MGP_OLD_BUGFIXES_REPO: a Bugfixes working copy before 1.19.0")
    remote = start(None, plugins=[plugin(OLD_BUGFIXES, "Client")])
    index = wait_dialog(remote)
    lines = log_warnings()
    assert len(lines) == 1 and TOO_OLD in lines[0], lines
    assert "its fix of the memory leak" in json.dumps(remote.get_controls(index))
