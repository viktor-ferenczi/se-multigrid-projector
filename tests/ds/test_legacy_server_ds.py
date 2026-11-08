"""An MGP 1.x client on a server with MGP 0.9.12 (SE-1273): the old server
sends its signature on the old channel only, so the client stays in
client-only mode and welds the first grid with vanilla requests, as on a
server without MGP."""

from __future__ import annotations

import time

import compat
import stations
from fixtures import bench_ids, bench_index, block_min

pytestmark = compat.needs_mgp_09

BENCHES = ["large"]
WORLD_SETTINGS = {"GameMode": "Creative"}
MGP_SERVER_REPO = compat.MGP_09_REPO


def test_client_stays_client_only(game):
    # The 0.9.x server sends its signature on PlayerConnected
    time.sleep(15)
    assert compat.client_lines("Comms: MultiplayerClient")
    assert not compat.client_lines(compat.PRESENCE)
    assert not compat.client_lines(compat.IGNORED)


def test_client_welds_the_first_grid(game):
    game.require_ops("WeldProjection")
    game.api.set_admin_flag("creativeTools", True)
    ids = bench_ids(bench_index("large"))
    compat.weld_passes(game, ids["projector"], instant=True, settle=10)
    cubes = game.cubes(ids["grid"])
    missing = [
        (block_min(b), b.findtext("SubtypeName"))
        for b in stations.blueprint_grids("large")[0].find("CubeBlocks")
        if not stations.is_infrastructure(b, ids)
        and cubes.get(block_min(b), {}).get("subtypeId") != b.findtext("SubtypeName")
    ]
    assert not missing
