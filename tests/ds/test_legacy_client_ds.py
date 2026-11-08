"""An MGP 0.9.12 client on a server with MGP 1.x (SE-1273). With the default
LegacyClientSupport the server still sends the old signature on the old
channel, so the 0.9.x client switches to full mode and sends the subgrid index
in BuildInternal's builtBy, which the 1.x server still takes: every subgrid
gets built."""

from __future__ import annotations

import time

import pytest

import compat
from fixtures import bench_ids, bench_index

pytestmark = compat.needs_mgp_09

BENCHES = ["large"]
WORLD_SETTINGS = {"GameMode": "Creative"}
MGP_SERVER_CONFIG = compat.FAST_PRESENCE
MGP_CLIENT_REPO = compat.MGP_09_REPO


@pytest.fixture(scope="module")
def welded(game):
    game.require_ops("WeldProjection")
    game.api.set_admin_flag("creativeTools", True)
    # The old signature goes out 1 s after the join
    time.sleep(5)
    return game.weld(bench_ids(bench_index("large"))["projector"])


def test_projection_is_complete(welded):
    assert welded.complete, {s.index: s.states for s in welded.subgrids if s.states}


def test_the_server_took_the_builtby_hack(welded):
    assert compat.server_lines(compat.LEGACY_RPC, wait=60)
    assert not compat.server_lines(compat.MOD_MESSAGES)
