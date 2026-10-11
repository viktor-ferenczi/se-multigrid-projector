"""Projection limits on a server with the limit on (GitHub issue #86): an over
the limit projection is refused, and a removed projection gives its PCU back.
The tests build on each other and run in order."""

from __future__ import annotations

import time

import limits
from limits import CELL_A, CELL_B, PROJECTOR_A, PROJECTOR_B

BENCHES = ["refs"]
WORLD_SETTINGS = limits.WORLD_SETTINGS
STATION_EXTRAS = {"refs": ("", limits.station())}
REPORT_PROJECTORS = (PROJECTOR_A, PROJECTOR_B)
EDIT_WORLD = limits.add_player
MGP_SERVER_CONFIG = {"ProjectionPcuLimitPercent": 100}


def test_projection_within_the_limit_is_projected(game):
    game.require_ops("LoadProjection")
    game.wait_grids([limits.STATION])
    limits.stand_on_station(game)
    limits.load(game, PROJECTOR_A)
    assert limits.wait_projected(game, PROJECTOR_A, True, 60)


def test_projection_over_the_limit_is_refused(game):
    limits.load(game, PROJECTOR_B)
    assert not limits.wait_projected(game, PROJECTOR_B, True, 30)
    # The server takes it away from the client that loaded it
    deadline = time.monotonic() + 30
    while limits.client_projecting(game, CELL_B) and time.monotonic() < deadline:
        time.sleep(1)
    assert not limits.client_projecting(game, CELL_B)
    assert limits.projected(game, PROJECTOR_A)


def test_removed_projection_gives_its_pcu_back(game):
    game.api.set_admin_flag("creativeTools", True)
    game.remove_block(limits.STATION, CELL_A)
    deadline = time.monotonic() + 30
    while CELL_A in {tuple(b["min"]) for b in game.blocks(limits.STATION)}:
        assert time.monotonic() < deadline, "Projector A was not removed"
        time.sleep(1)
    limits.load(game, PROJECTOR_B)
    assert limits.wait_projected(game, PROJECTOR_B, True, 60)
