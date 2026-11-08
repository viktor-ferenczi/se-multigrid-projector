"""Before SE-1273: MGP 0.9.12 on both sides with Anti-Cheat's projector build
guard. The 0.9.x client puts the subgrid index into BuildInternal's builtBy,
the guard takes that for a spoofed request and kicks the player on the first
hand weld (SE-1252). Kept as the reference the 1.x tests are compared with."""

from __future__ import annotations

import pytest

import compat
from fixtures import bench_ids, bench_index

pytestmark = [compat.needs_anti_cheat, compat.needs_mgp_09]

BENCHES = ["survival"]
WORLD_SETTINGS = {"GameMode": "Survival", "EnableResearch": "false"}
SERVER_PLUGINS = [compat.ANTI_CHEAT]
EDIT_WORLD = compat.anti_cheat_config
ADMINS = False
STATION_EXTRAS = compat.medical_room_extras()
MGP_SERVER_REPO = compat.MGP_09_REPO
MGP_CLIENT_REPO = compat.MGP_09_REPO


def test_anti_cheat_kicks_the_mgp_09_welder(game):
    game.require_ops("WeldProjection")
    projector = bench_ids(bench_index("survival"))["projector"]
    # The 0.9.x server sends its signature on PlayerConnected
    compat.wait_until(lambda: False, 10)
    try:
        compat.weld_passes(game, projector, instant=False, timeout=60, settle=10)
    except Exception:  # noqa: BLE001 -- the kicked client loses its world
        pass
    kicks = compat.wait_until(compat.anti_cheat_refusals, 30)
    assert kicks and "projector-build request" in kicks[0], kicks
