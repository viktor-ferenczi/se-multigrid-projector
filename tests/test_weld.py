"""Welding every vanilla mechanical combination from a projection.

Each bench is welded by hand welder passes until nothing is left to build. MGP
has to build each base, create its top part of the right size, register the
new subgrid and weld the subgrid's blocks, down to subgrids on subgrids. The
world is creative, where the game creates top parts finished; with creative
tools every welded block is finished too."""

from __future__ import annotations

import pytest

import blueprint
from fixtures import bench_ids, bench_index
from se_remote import GetOp

BENCHES = ["large", "small", "wheels-large", "wheels-small", "chain"]
WORLD_SETTINGS = {"GameMode": "Creative"}
MECHANICAL = ("Stator", "Rotor", "Piston", "Suspension", "Wheel", "Hinge")

COMBOS = [
    pytest.param(bench, c, id=f"{bench}-{c.name}")
    for bench in BENCHES
    for c in blueprint.connections(bench)
]


@pytest.fixture(scope="module")
def welded(game):
    game.require_ops("WeldProjection")
    game.api.set_admin_flag("creativeTools", True)
    return {b: game.weld(bench_ids(bench_index(b))["projector"]) for b in BENCHES}


@pytest.fixture(scope="module")
def grids(game, welded):
    return {g["entityId"]: g for g in game.grids()}


@pytest.mark.parametrize("bench", BENCHES)
def test_projection_is_complete(welded, bench):
    report = welded[bench]
    assert report.complete, {s.index: s.states for s in report.subgrids if s.states}
    built = [s.built for s in report.subgrids]
    assert all(built) and len(set(built)) == len(built)


@pytest.mark.parametrize("bench, connection", COMBOS)
def test_subgrid_is_built_as_in_the_blueprint(game, welded, grids, bench, connection):
    built = welded[bench].subgrids[connection.top_grid].built
    assert grids[built]["gridSize"] == blueprint.grid_sizes(bench)[connection.top_grid]
    assert len(game.cubes(built)) == blueprint.grid_block_count(
        bench, connection.top_grid
    )


def _mechanical_blocks(game, grid_id: int) -> list[dict]:
    refs = [
        GetOp.block(grid_id, tuple(b["min"]))
        for b in game.blocks(grid_id)
        if any(k in b["blockType"] for k in MECHANICAL)
    ]
    batch = game.api.batch(gets=refs)
    return [batch.get(i) for i in range(len(refs))]


@pytest.mark.parametrize("bench, connection", COMBOS)
def test_base_holds_its_top_part(game, welded, bench, connection):
    """The welded base is attached to a top part of the blueprint's subtype, on
    the subgrid built for it"""
    game.require_ops("GetObjectBuilder")
    report = welded[bench]
    base_grid = report.subgrids[connection.base_grid].built
    top_grid = report.subgrids[connection.top_grid].built
    tops = {
        b["entityId"]: b["definition"]["subtypeId"]
        for b in _mechanical_blocks(game, top_grid)
    }
    holding = [
        b
        for b in _mechanical_blocks(game, base_grid)
        if b["definition"]["subtypeId"] == connection.base
        and int(game.object_builder(b["entityId"]).findtext("TopBlockId") or 0) in tops
    ]
    assert len(holding) == 1
    top_id = int(game.object_builder(holding[0]["entityId"]).findtext("TopBlockId"))
    assert tops[top_id] == connection.top
