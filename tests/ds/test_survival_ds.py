"""Survival welding with ship welders on a dedicated server with the MGP server
plugin.

On the test server the ship welders turn on, take components from the
conveyors and build nothing from the projection, with the MGP server plugin
and without it (SE1-0117). Until that is understood, this file checks only that
the welders start building. The rest of test_survival.py needs them to.
"""

from __future__ import annotations

import time

import pytest

import survival
from test_survival import BENCHES, STATION_EXTRAS  # noqa: F401
from test_survival import set_welders, stand_on_station


@pytest.mark.xfail(
    strict=True, reason="ship welders build nothing on the test server (SE1-0117)"
)
def test_ship_welders_build_the_bases(game):
    def built():
        return set(survival.COLUMNS) <= set(game.cubes(survival.STATION))

    stand_on_station(game)
    set_welders(game, survival.WELDERS, True)
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline and not built():
        time.sleep(5)
    set_welders(game, survival.WELDERS, False)
    assert built()
