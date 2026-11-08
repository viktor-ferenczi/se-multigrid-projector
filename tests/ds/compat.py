"""Helpers of the client/server compatibility tests (SE-1273): the presence
packet, client-only and full mode, Anti-Cheat on the server and MGP 0.9.x on
either side.

MGP_ANTI_CHEAT_REPO is a working copy of CometWorks/anti-cheat (its projector
build guard), MGP_09_REPO one of MGP 0.9.12. Tests needing one skip without it.
"""

from __future__ import annotations

import os
import re
import time
from datetime import datetime
from pathlib import Path

import pytest

import ds_rig
import stations
import world
from fixtures import bench_ids, bench_index
from se_remote import CallOp

ANTI_CHEAT_REPO = Path(os.environ.get("MGP_ANTI_CHEAT_REPO", "/nonexistent"))
ANTI_CHEAT = (
    "2671944D-7664-4AFE-8FD8-6FCAB63A0EFB",
    "anti-cheat",
    ANTI_CHEAT_REPO,
    "AntiCheatServer.xml",
)
MGP_09_REPO = Path(os.environ.get("MGP_09_REPO", "/nonexistent"))

# Seconds, short for the tests; production is 5 and 300
FAST_PRESENCE = {"PresenceDelaySeconds": 1, "PresenceIntervalSeconds": 3}

FULL_MODE = "server plugin present, full feature set"
PRESENCE = "Presence packet from the server"
IGNORED = "Ignored the server's presence packet"
MOD_MESSAGES = "arrive as mod messages"
VANILLA_RPC = "with vanilla arguments"
LEGACY_RPC = "with the subgrid index in builtBy"
REFUSED = "Refused a build request"
# Anti-Cheat logs a refusal only when it kicks, which anti_cheat_config makes
# it do on the first one
ANTI_CHEAT_KICK = "AntiCheat: Kicking"

needs_anti_cheat = pytest.mark.skipif(
    not (ANTI_CHEAT_REPO / "AntiCheatServer.xml").exists(),
    reason="MGP_ANTI_CHEAT_REPO is not an anti-cheat working copy",
)
needs_mgp_09 = pytest.mark.skipif(
    not (MGP_09_REPO / "MultigridProjectorClient.xml").exists(),
    reason="MGP_09_REPO is not an MGP 0.9.x working copy",
)

_STAMP = re.compile(r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\.\d+) - ")


def client_lines(text: str, client=ds_rig.CLIENT) -> list[tuple[datetime, str]]:
    """The client's MGP log lines containing text, with their times"""
    found = []
    for line in client.log.read_text(errors="replace").splitlines():
        stamp = _STAMP.match(line)
        if stamp and "Multigrid Projector:" in line and text in line:
            found.append((datetime.fromisoformat(stamp.group(1)), line))
    return found


def server_lines(text: str, wait: float = 0) -> list[str]:
    """The server's log lines containing text. The game writes its log a
    while later: wait is how long to wait for the first one."""

    def lines():
        return [l for l in ds_rig.server_log_text().splitlines() if text in l]

    return wait_until(lines, wait) if wait else lines()


def medical_room_extras(bench: str = "survival", cell=(6, 1, 0)) -> dict:
    """STATION_EXTRAS: a medical room shared with all on the bench's floor
    strip, in the middle, so a player who isn't an admin (and so can't use the
    admin teleport) spawns within reach of every projected block"""
    room = world.block(
        "MedicalRoom",
        "LargeMedicalRoom",
        cell,
        bench_ids(bench_index(bench))["grid"] + 900,
        stations_owned() + "<Enabled>true</Enabled>",
    )
    return {bench: (room, "")}


def stations_owned() -> str:
    owner = stations.PB_OWNER
    return f"<Owner>{owner}</Owner><BuiltBy>{owner}</BuiltBy><ShareMode>All</ShareMode>"


def wait_until(check, timeout: float, interval: float = 0.5):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = check()
        if result:
            return result
        time.sleep(interval)
    return check()


def stand_on(game, bench: str, cell) -> None:
    """The character on the bench's floor strip, within reach of its blocks"""
    grid = bench_ids(bench_index(bench))["grid"]
    world = game.api.call([CallOp.grid_to_world(grid, cell)]).call(0)["world"]
    game.api.character_teleport(*world)
    time.sleep(3)


def weld_passes(game, projector_id: int, instant: bool, timeout=120.0, settle=15.0):
    """Hand welder passes until none requests anything for settle seconds,
    without MGP's PB report (a 0.9.x or no server plugin has none)"""
    deadline = time.monotonic() + timeout
    quiet_since = time.monotonic()
    total = 0
    while time.monotonic() < deadline:
        requested = game.weld_pass(projector_id, instant)
        total += requested
        if requested:
            quiet_since = time.monotonic()
        elif time.monotonic() - quiet_since > settle:
            break
        time.sleep(1)
    return total


def grid_count(game) -> int:
    return len(game.grids())


def anti_cheat_config(_world=None) -> None:
    """EDIT_WORLD of the Anti-Cheat tests: the plugin on, kicking on the first
    refusal, so every refusal shows in the server log with its reason. The
    other options keep their defaults (all guards on)."""
    ds_rig.SERVER_DATA.mkdir(parents=True, exist_ok=True)
    (ds_rig.SERVER_DATA / "AntiCheat.cfg").write_text(
        '<?xml version="1.0" encoding="utf-8"?>'
        '<PluginConfig xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
        'xmlns:xsd="http://www.w3.org/2001/XMLSchema">'
        "<Enabled>true</Enabled><KickOnValidationFailure>true</KickOnValidationFailure>"
        "<ValidationFailuresBeforeKick>1</ValidationFailuresBeforeKick>"
        "<EnforceBuildRequestAuthority>true</EnforceBuildRequestAuthority>"
        "</PluginConfig>",
        encoding="utf-8",
    )


def anti_cheat_refusals() -> list[str]:
    return server_lines(ANTI_CHEAT_KICK)
