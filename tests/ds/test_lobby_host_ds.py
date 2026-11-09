"""A client hosting a lobby game (SE-1273): client 1 hosts a creative world
with DirectTransport's lobby, client 2 joins it. The host's client plugin acts
as the server plugin: it sends the presence packet and builds the joiner's
full mode build requests, subgrids included."""

from __future__ import annotations

import os

import pytest

import compat
import ds_rig
import rig
import stations
from fixtures import bench_ids, bench_index
from harness import Game

BENCHES = ["large"]
HOST = ds_rig.CLIENT
JOINER = ds_rig.CLIENT2
WORLD = HOST.saves / "MgpLobby"
PORT = ds_rig.SERVER_PORT


@pytest.fixture(scope="module")
def game():
    """The joiner's view, once it is in full mode"""
    try:
        ds_rig.stop_clients()
        ds_rig.stop_server()
        stations.prepare(
            WORLD,
            BENCHES,
            settings={"GameMode": "Creative", "OnlineMode": "FRIENDS"},
        )
        rig.launch(HOST, ["--host-lobby", str(PORT)])
        host = rig.wait_api(HOST)
        rig.load_world(host, WORLD)
        rig.ensure_character(host)

        rig.launch(JOINER, ["--join-lobby", f"127.0.0.1:{PORT}"])
        joiner = rig.wait_api(JOINER)
        rig.wait_world(joiner, 900)
        rig.ensure_character(joiner)
        rig.focus_gameplay(joiner)
        game = Game(joiner)
        game.wait_grids(
            [stations.CONTROL_ID] + [bench_ids(bench_index(b))["grid"] for b in BENCHES]
        )
        yield game
    finally:
        if os.environ.get("MGP_KEEP") != "1":
            ds_rig.stop_clients()


def test_host_advertises_and_joiner_switches(game):
    assert compat.client_lines("Comms: MultiplayerServer", HOST)
    assert compat.wait_until(lambda: compat.client_lines(compat.FULL_MODE, JOINER), 60)


def test_joiner_welds_every_subgrid(game):
    game.require_ops("WeldProjection")
    assert compat.wait_until(lambda: compat.client_lines(compat.FULL_MODE, JOINER), 60)
    report = game.weld(bench_ids(bench_index("large"))["projector"])
    assert report.complete, {s.index: s.states for s in report.subgrids if s.states}
    # The game writes its log a while later
    assert compat.wait_until(lambda: compat.client_lines(compat.MOD_MESSAGES, HOST), 60)
    assert not compat.client_lines("BuildInternal RPC from", HOST)
