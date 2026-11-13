"""Blocks beside a sibling subgrid mounted at an angle (SE-1402).

The bench has two rotors next to each other, each with an arm of three armor
blocks over its head. The second arm is turned by 30 degrees in the blueprint,
so its far end leans a little into the cells of the first arm. The game's
placement test rejects a block whose shape touches another grid that is not
axis aligned with the target grid, without looking at the cells. Whichever arm
got its far block first kept the other arm's block from being built, with
"something is in the way" and nothing visibly there.

MGP lets a projected block through when all it touches are built subgrids of
the same projection and none of them reaches into the inner half of the block.

A weld pass asks for every buildable block at once, so both far blocks go up in
the same pass, before either is there to be in the other's way. The test
therefore takes the far block of each arm away again and welds it back while
the other arm is complete.
"""

from __future__ import annotations

from fixtures import bench_ids, bench_index

BENCHES = ["angled"]
WORLD_SETTINGS = {"GameMode": "Creative"}


def _far_cell(game, grid_id: int) -> tuple:
    """The armor block at the end of an arm; its head is at the grid's origin"""
    return max(game.cubes(grid_id), key=lambda cell: sum(abs(c) for c in cell))


def test_blocks_beside_an_angled_sibling_subgrid_are_built(game):
    game.require_ops("WeldProjection")
    game.api.set_admin_flag("creativeTools", True)
    projector = bench_ids(bench_index("angled"))["projector"]
    report = game.weld(projector)
    assert report.complete, {s.index: s.states for s in report.subgrids if s.states}

    for arm in (1, 2):
        built = report.subgrids[arm].built
        game.remove_block(built, _far_cell(game, built))
        game.wait_report(projector, lambda r: not r.complete)
        report = game.weld(projector)
        assert report.complete, (
            arm,
            {s.index: s.states for s in report.subgrids if s.states},
        )
