"""Client setup: every test file is a session of its own.

Each file starts client 0 of the slot, loads a fresh copy of the test world with
the benches it names in a module level BENCHES list (all of them by default),
and stops the client at the end. WORLD_SETTINGS changes session settings of the
world by element name.

MGP_ATTACH=1 reuses a client of the slot that is already in the test world, and
MGP_KEEP=1 leaves the client running after the run; both help while iterating
on one file. The plugin's lines of the game log are copied to
tests/artifacts/<test file>.log.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

import rig
import stations
from benches import BENCHES
from harness import Game

ATTACH = os.environ.get("MGP_ATTACH") == "1"
KEEP = os.environ.get("MGP_KEEP") == "1"
CLIENT = rig.Client(0)
WORLD = CLIENT.saves / "MgpTest"


@pytest.fixture(scope="module")
def game(request):
    attach = ATTACH and rig.running_pid(CLIENT)
    try:
        if not attach:
            rig.stop(CLIENT)
            stations.prepare(
                WORLD,
                getattr(request.module, "BENCHES", list(BENCHES)),
                settings=getattr(request.module, "WORLD_SETTINGS", None),
            )
            rig.launch(CLIENT)
        remote = rig.wait_api(CLIENT)
        if not attach:
            rig.load_world(remote, WORLD)
        rig.ensure_character(remote)
        rig.focus_gameplay(remote)
        yield Game(remote)
    finally:
        if not KEEP:
            rig.stop(CLIENT)


def plugin_lines(log: Path, offset: int) -> tuple[list[str], int]:
    """MGP's lines in a game log from a byte offset on, and the new end"""
    try:
        data = log.read_bytes()
    except OSError:
        return [], offset
    text = data[offset if offset <= len(data) else 0 :].decode("utf-8", "replace")
    lines = [
        line.split(" ->  ", 1)[-1]
        for line in text.splitlines()
        if "Multigrid Projector:" in line
    ]
    return lines, len(data)


@pytest.fixture(autouse=True)
def log_what_the_plugin_did(request):
    _, offset = plugin_lines(CLIENT.log, 0)
    yield
    lines, _ = plugin_lines(CLIENT.log, offset)
    rig.ARTIFACTS.mkdir(parents=True, exist_ok=True)
    path = rig.ARTIFACTS / f"{request.module.__name__}.log"
    with open(path, "a", encoding="utf-8") as file:
        file.write(f"=== {request.node.name}\n" + "".join(f"{l}\n" for l in lines))
