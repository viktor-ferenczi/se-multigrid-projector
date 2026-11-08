"""An MGP 0.9.12 client on a 1.x server with Anti-Cheat and LegacyClientSupport
off (SE-1273): the server doesn't tell the old client it has the plugin, so it
stays in client-only mode and sends vanilla requests, which the guard lets
through. With LegacyClientSupport on it would be kicked as in
test_anticheat_mgp09_ds.py."""

from __future__ import annotations

import compat
from fixtures import bench_ids, bench_index

pytestmark = [compat.needs_anti_cheat, compat.needs_mgp_09]

BENCHES = ["survival"]
WORLD_SETTINGS = {"GameMode": "Survival", "EnableResearch": "false"}
MGP_SERVER_CONFIG = {**compat.FAST_PRESENCE, "LegacyClientSupport": "false"}
SERVER_PLUGINS = [compat.ANTI_CHEAT]
EDIT_WORLD = compat.anti_cheat_config
ADMINS = False
STATION_EXTRAS = compat.medical_room_extras()
MGP_CLIENT_REPO = compat.MGP_09_REPO


def test_old_client_welds_without_a_kick(game):
    game.require_ops("WeldProjection")
    projector = bench_ids(bench_index("survival"))["projector"]
    compat.wait_until(lambda: False, 5)
    assert compat.weld_passes(game, projector, instant=False, timeout=60, settle=10)
    assert compat.server_lines(compat.VANILLA_RPC, wait=60)
    assert not compat.server_lines(compat.LEGACY_RPC)
    assert not compat.anti_cheat_refusals()
