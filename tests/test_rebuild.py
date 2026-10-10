"""Rebuilding from a projection after parts of the welded result are lost.

The large bench is welded first. Each test then takes something away, a whole
top subgrid, a mechanical base or a block on a subgrid, and welds the
projection again: MGP has to notice the loss, offer what is missing for welding
(creating a top part for a base that lost its own, building a new base for a
subgrid that fell off) and end up with the complete projection again.
"""

from __future__ import annotations

import pytest

import blueprint
from fixtures import bench_ids, bench_index
from se_remote import SetOp

BENCH = "large"
BENCHES = [BENCH]
WORLD_SETTINGS = {"GameMode": "Creative"}
PROJECTOR = bench_ids(bench_index(BENCH))["projector"]
STATION = bench_ids(bench_index(BENCH))["grid"]
CONNECTIONS = [pytest.param(c, id=c.name) for c in blueprint.connections(BENCH)]


@pytest.fixture(scope="module")
def welded(game):
    game.require_ops("WeldProjection")
    game.api.set_admin_flag("creativeTools", True)
    report = game.weld(PROJECTOR)
    assert report.complete, {s.index: s.states for s in report.subgrids if s.states}
    return report


def wait_for(game, until, timeout: float = 60.0):
    """The report once until(report) holds"""
    report = game.wait_report(PROJECTOR, until, timeout)
    assert until(report), report.counts()
    return report


def base_cell(connection) -> tuple[int, int, int]:
    """Where the base stands on the station, which the projection covers cell
    for cell"""
    return next(
        b.min
        for b in blueprint.blocks(BENCH)
        if b.grid == connection.base_grid
        and b.top_id
        and next(t for t in blueprint.blocks(BENCH) if t.entity_id == b.top_id).grid
        == connection.top_grid
    )


@pytest.mark.parametrize("connection", CONNECTIONS)
def test_lost_subgrid_is_welded_again(game, welded, connection):
    report = game.report(PROJECTOR)
    old = report.subgrids[connection.top_grid].built
    closed = game.api.batch(sets=[SetOp.grid_close(old)])
    closed.set(0)
    wait_for(game, lambda r: not r.subgrids[connection.top_grid].complete)
    report = game.weld(PROJECTOR)
    assert report.complete, {s.index: s.states for s in report.subgrids if s.states}
    assert report.subgrids[connection.top_grid].built not in (0, old)


@pytest.mark.parametrize("connection", CONNECTIONS)
def test_lost_base_is_welded_again(game, welded, connection):
    """The top part and its subgrid fall off with the base, under gravity onto
    the base's cell, so they are cleared away before welding: the new base gets
    a new top part."""
    old = game.report(PROJECTOR).subgrids[connection.top_grid].built
    game.remove_block(STATION, base_cell(connection))
    wait_for(game, lambda r: not r.subgrids[0].complete)
    game.api.batch(sets=[SetOp.grid_close(old)]).set(0)
    report = game.weld(PROJECTOR)
    assert report.complete, {s.index: s.states for s in report.subgrids if s.states}
    assert report.subgrids[connection.top_grid].built not in (0, old)


@pytest.mark.parametrize("connection", CONNECTIONS)
def test_lost_payload_block_is_welded_again(game, welded, connection):
    report = game.report(PROJECTOR)
    subgrid = report.subgrids[connection.top_grid].built
    payload = [
        cell
        for cell, cube in game.cubes(subgrid).items()
        if "Armor" in cube["subtypeId"]
    ]
    assert payload, game.cubes(subgrid)
    game.remove_block(subgrid, payload[0])
    wait_for(game, lambda r: not r.subgrids[connection.top_grid].complete)
    report = game.weld(PROJECTOR)
    assert report.complete, {s.index: s.states for s in report.subgrids if s.states}
    assert report.subgrids[connection.top_grid].built == subgrid


def test_projection_survives_a_reload(game, welded):
    """A projection welded halfway, saved and loaded again, keeps what was
    built and welds the rest. Single player only: a dedicated server would
    have to be restarted."""
    if game.api.get_state().get("multiplayer") != "offline":
        pytest.skip("single player only")
    closed = [s.built for s in game.report(PROJECTOR).subgrids[1:4]]
    for grid_id in closed:
        game.api.batch(sets=[SetOp.grid_close(grid_id)]).set(0)
    wait_for(game, lambda r: sum(not s.complete for s in r.subgrids) >= 3)
    game.save_and_reload()
    game.api.set_admin_flag("creativeTools", True)
    report = wait_for(game, lambda r: r.scan > 0, timeout=120)
    assert sum(not s.complete for s in report.subgrids) >= 3
    report = game.weld(PROJECTOR)
    assert report.complete, {s.index: s.states for s in report.subgrids if s.states}
