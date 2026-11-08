"""A server of another protocol id (SE-1273): the client ignores its presence
packet, stays in client-only mode and sends exactly what a vanilla client
sends. Anti-Cheat's projector build guard, which refuses any BuildInternal RPC
that isn't vanilla, lets every one through. The server pretends to be another
protocol through MGP_TEST_PROTOCOL_ID."""

from __future__ import annotations

import pytest

import compat
from fixtures import bench_ids, bench_index

pytestmark = compat.needs_anti_cheat

BENCHES = ["survival"]
WORLD_SETTINGS = {"GameMode": "Survival", "EnableResearch": "false"}
MGP_SERVER_CONFIG = compat.FAST_PRESENCE
SERVER_PLUGINS = [compat.ANTI_CHEAT]
SERVER_ENV = {"MGP_TEST_PROTOCOL_ID": "0f8e2c4d-6b1a-4e3f-9d2c-7a5b3e1f0c9d"}
ADMINS = False
STANDING = (3, 1, 1)


@pytest.fixture(scope="module")
def welded(game):
    game.require_ops("WeldProjection")
    # Several presence packets went by
    assert compat.wait_until(lambda: compat.client_lines(compat.IGNORED), 30)
    compat.stand_on(game, "survival", STANDING)
    projector = bench_ids(bench_index("survival"))["projector"]
    return compat.weld_passes(game, projector, instant=False)


def test_presence_is_ignored_once(game, welded):
    ignored = compat.client_lines(compat.IGNORED)
    assert len(ignored) == 1
    assert "0f8e2c4d-6b1a-4e3f-9d2c-7a5b3e1f0c9d" in ignored[0][1]
    assert not compat.client_lines(compat.FULL_MODE)
    assert not compat.client_lines(compat.PRESENCE)


def test_client_sends_only_vanilla_requests(game, welded):
    assert welded
    assert compat.server_lines(compat.VANILLA_RPC)
    assert not compat.server_lines(compat.LEGACY_RPC)
    assert not compat.server_lines(compat.MOD_MESSAGES)


def test_anti_cheat_refused_nothing(game, welded):
    assert not compat.anti_cheat_refusals()
