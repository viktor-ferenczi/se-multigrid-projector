"""A client without MGP on a server with MGP 1.x (SE-1273): the presence
packet goes to a channel nobody listens on, and the vanilla client welds the
projection's first grid with vanilla BuildInternal RPCs."""

from __future__ import annotations

import compat
import stations
from fixtures import bench_ids, bench_index, block_min

BENCHES = ["large"]
WORLD_SETTINGS = {"GameMode": "Creative"}
MGP_SERVER_CONFIG = compat.FAST_PRESENCE
MGP_CLIENT = False


def test_vanilla_client_welds_the_first_grid(game):
    game.require_ops("WeldProjection")
    game.api.set_admin_flag("creativeTools", True)
    ids = bench_ids(bench_index("large"))
    compat.weld_passes(game, ids["projector"], instant=True, settle=10)
    cubes = game.cubes(ids["grid"])
    blocks = [
        b
        for b in stations.blueprint_grids("large")[0].find("CubeBlocks")
        if not stations.is_infrastructure(b, ids)
    ]
    built = [
        b
        for b in blocks
        if cubes.get(block_min(b), {}).get("subtypeId") == b.findtext("SubtypeName")
    ]
    assert built
    assert compat.server_lines(compat.VANILLA_RPC)
    assert not compat.server_lines(compat.MOD_MESSAGES)
    assert not compat.server_lines(compat.LEGACY_RPC)
