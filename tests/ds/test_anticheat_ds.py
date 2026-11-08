"""Full mode builds pass Anti-Cheat (SE-1273, SE-1252): a survival player
without admin rights welds a projection with subgrids on a server with MGP and
Anti-Cheat's projector build guard. MGP 0.9.x put the subgrid index into the
vanilla BuildInternal RPC's builtBy, which the guard refuses with a kick. MGP
1.x sends full mode builds as mod messages and checks the player's identity,
character, reach and rate itself."""

from __future__ import annotations

import pytest

import compat
import stations
from fixtures import bench_ids, bench_index

pytestmark = compat.needs_anti_cheat

BENCHES = ["survival"]
WORLD_SETTINGS = {"GameMode": "Survival", "EnableResearch": "false"}
MGP_SERVER_CONFIG = compat.FAST_PRESENCE
SERVER_PLUGINS = [compat.ANTI_CHEAT]
EDIT_WORLD = compat.anti_cheat_config
ADMINS = False
# A plain player can't teleport: the character spawns in the middle of the bench
STATION_EXTRAS = compat.medical_room_extras()


@pytest.fixture(scope="module")
def welded(game):
    game.require_ops("WeldProjection")
    assert compat.wait_until(lambda: compat.client_lines(compat.FULL_MODE), 30)
    grids = compat.grid_count(game)
    projector = bench_ids(bench_index("survival"))["projector"]
    requested = compat.weld_passes(game, projector, instant=False)
    return grids, requested


def test_anti_cheat_is_loaded(game):
    assert "AntiCheat" in compat.ds_rig.server_log_text()


def test_subgrids_are_built(game, welded):
    grids_before, requested = welded
    assert requested
    # The rotor's and the piston's heads, each a subgrid of its own
    assert compat.grid_count(game) >= grids_before + 2


def test_builds_arrive_as_mod_messages(game, welded):
    assert compat.server_lines(compat.MOD_MESSAGES, wait=60)
    assert not compat.server_lines("BuildInternal RPC from")
    assert not compat.server_lines(compat.REFUSED)


def test_anti_cheat_refused_nothing(game, welded):
    assert not compat.anti_cheat_refusals()
    # Not kicked: the client still sees the world
    assert stations.CONTROL_ID in {g["entityId"] for g in game.grids()}
