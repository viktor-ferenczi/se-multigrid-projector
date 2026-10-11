"""Projection limits on a server without the setting (GitHub issue #86): MGP
checks nothing, both projections load although together they are over the
player's PCU limit."""

from __future__ import annotations

import limits
from limits import PROJECTOR_A, PROJECTOR_B

BENCHES = ["refs"]
WORLD_SETTINGS = limits.WORLD_SETTINGS
STATION_EXTRAS = {"refs": ("", limits.station())}
REPORT_PROJECTORS = (PROJECTOR_A, PROJECTOR_B)
EDIT_WORLD = limits.add_player


def test_projections_are_not_limited(game):
    game.require_ops("LoadProjection")
    game.wait_grids([limits.STATION])
    limits.stand_on_station(game)
    limits.load(game, PROJECTOR_A)
    assert limits.wait_projected(game, PROJECTOR_A, True, 60)
    limits.load(game, PROJECTOR_B)
    assert limits.wait_projected(game, PROJECTOR_B, True, 60)
    assert limits.projected(game, PROJECTOR_A)
