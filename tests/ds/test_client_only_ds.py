"""Client-only mode: a dedicated server without the MGP server plugin, joined by
a client that has it.

The server's vanilla projector knows only the projection's first grid. The
client's MGP still projects every subgrid, and its client welding places what
the server can't build: mechanical bases, the right heads and the blocks of the
subgrids. MGP's PB API isn't there (the script runs on the server), so the
tests look at the projector's statistics and the welded grids through Remote,
following each welded base to its head.
"""

from __future__ import annotations

import time
from collections import Counter

import pytest

import blueprint
import stations
from fixtures import bench_ids, bench_index, block_min
from se_remote import CallOp

MGP_SERVER = False
BENCHES = ["large", "small", "chain"]
WORLD_SETTINGS = {"GameMode": "Creative"}
MECHANICAL = ("Stator", "Rotor", "Piston", "Suspension", "Wheel", "Hinge")
# On the floor strip, past the projector and the battery
STANDING = (3, 1, 1)

COMBOS = [
    pytest.param(bench, c, id=f"{bench}-{c.name}")
    for bench in BENCHES
    for c in blueprint.connections(bench)
]


def projector(bench: str) -> int:
    return bench_ids(bench_index(bench))["projector"]


def weld(game, projector_id: int, timeout: float = 300.0, settle: float = 20.0):
    """Hand welder passes until none has requested anything for settle
    seconds. Client welding places blocks over several frames and the server's
    replies, so a pass with no request may come before the next is possible."""
    deadline = time.monotonic() + timeout
    quiet_since = time.monotonic()
    while time.monotonic() < deadline:
        if game.weld_pass(projector_id):
            quiet_since = time.monotonic()
        elif time.monotonic() - quiet_since > settle:
            return
        time.sleep(1)


@pytest.fixture(scope="module")
def stats(game):
    """The projectors' statistics before welding, once the client scanned"""
    time.sleep(10)
    return {bench: game.projector_stats(bench) for bench in BENCHES}


def stand_on_bench(game, bench: str) -> None:
    """Puts the character on the bench's floor strip. Client welding asks the
    server for a small head with a request it takes only from a character
    within about 15 m of the grid."""
    grid = bench_ids(bench_index(bench))["grid"]
    cell = game.api.call([CallOp.grid_to_world(grid, STANDING)]).call(0)
    game.api.character_teleport(*cell["world"])
    time.sleep(3)


@pytest.fixture(scope="module")
def welded(game, stats):
    game.require_ops("WeldProjection", "GetObjectBuilder")
    game.api.set_admin_flag("creativeTools", True)
    for bench in BENCHES:
        stand_on_bench(game, bench)
        weld(game, projector(bench))
    return True


@pytest.fixture(scope="module")
def tree(game, welded):
    """Per bench, every welded mechanical connection reachable from its
    station: (base subtype, head subtype, head grid size, head grid blocks)"""
    grids = {g["entityId"]: g for g in game.grids()}
    cubes = {grid_id: game.cubes(grid_id) for grid_id in grids}
    owner = {
        cube["fatEntityId"]: (grid_id, cube)
        for grid_id, grid_cubes in cubes.items()
        for cube in grid_cubes.values()
        if cube.get("fatEntityId")
    }

    def walk(grid_id, seen):
        found = []
        for cube in cubes[grid_id].values():
            if not any(k in cube["subtypeId"] for k in MECHANICAL):
                continue
            builder = game.object_builder(cube["fatEntityId"])
            top_grid, top = owner.get(
                int(builder.findtext("TopBlockId") or 0), (0, None)
            )
            if not top_grid or top_grid in seen:
                continue
            seen.add(top_grid)
            found.append(
                (
                    cube["subtypeId"],
                    top["subtypeId"],
                    grids[top_grid]["gridSize"],
                    len(cubes[top_grid]),
                )
            )
            found += walk(top_grid, seen)
        return found

    return {
        bench: Counter(walk(bench_ids(bench_index(bench))["grid"], set()))
        for bench in BENCHES
    }


@pytest.mark.parametrize("bench", BENCHES)
def test_projector_counts_every_subgrid(stats, bench):
    total = sum(
        blueprint.grid_block_count(bench, i)
        for i in range(len(blueprint.grid_sizes(bench)))
    )
    assert stats[bench]["isProjecting"]
    assert stats[bench]["totalBlocks"] == total


@pytest.mark.parametrize("bench", BENCHES)
def test_station_blocks_are_welded(game, welded, bench):
    ids = bench_ids(bench_index(bench))
    cubes = game.cubes(ids["grid"])
    missing = [
        (block_min(b), b.findtext("SubtypeName"))
        for b in stations.blueprint_grids(bench)[0].find("CubeBlocks")
        if not stations.is_infrastructure(b, ids)
        and cubes.get(block_min(b), {}).get("subtypeId") != b.findtext("SubtypeName")
    ]
    assert not missing


@pytest.mark.parametrize("bench, connection", COMBOS)
def test_subgrid_is_built_as_in_the_blueprint(tree, bench, connection):
    """The base holds a head of the blueprint's subtype, on a grid of the
    blueprint's size and block count"""
    expected = (
        connection.base,
        connection.top,
        blueprint.grid_sizes(bench)[connection.top_grid],
        blueprint.grid_block_count(bench, connection.top_grid),
    )
    welded = [c for c in tree[bench] if c[:2] == expected[:2]]
    assert tree[bench][expected], welded
