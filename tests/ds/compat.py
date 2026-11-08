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
# What Anti-Cheat's projector guard says when it refuses
ANTI_CHEAT_REFUSALS = ("projector-build request", "area-build request")

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


def server_lines(text: str) -> list[str]:
    return [l for l in ds_rig.server_log_text().splitlines() if text in l]


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


def anti_cheat_refusals() -> list[str]:
    return [
        l
        for l in ds_rig.server_log_text().splitlines()
        if any(r in l for r in ANTI_CHEAT_REFUSALS)
    ]
