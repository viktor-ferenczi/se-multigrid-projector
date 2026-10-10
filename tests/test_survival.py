"""Welding in survival with ship welders that take their components from the
conveyor system (survival.py has the bench's welders and containers).

Outside creative every block starts at construction stage, a head too: MGP
creates the head of a welded base unfinished, and the welders have to finish
it and the payload on it. Every component that leaves the containers and the
welders has to end up in a welded block. The only components that come from
nowhere are the first ones of the heads, which the game gives any head it
creates at construction stage.

The welder on a piston is GitHub issue #136: a welder whose body reaches into
the cell of a projected block must not build it, nor use up components on it,
and once it is clear of the cell it has to build the block for exactly the
block's components.
"""

from __future__ import annotations

import re
import time
from collections import Counter

import pytest

import blueprint
import stations
import survival
from fixtures import block_min
from se_remote import CallOp, GetOp

BENCH = survival.BENCH
BENCHES = [BENCH]
# With progression on, a server refuses to build blocks from a projection for
# an owner who hasn't researched them (MyCubeGrid.BuildBlockRequestInternal);
# single player lets its local player through anyway
WORLD_SETTINGS = {"EnableResearch": "false"}
STATION_EXTRAS = survival.extras()
PROJECTOR = survival.PROJECTOR
STATION = survival.STATION
PROJECTOR_CELL = (0, 1, 0)
# The welders of the columns reach the rotor and the piston, not the strip
COMBO_SUBGRIDS = [c.top_grid for c in blueprint.connections(BENCH)]


def _stock(game, refs) -> Counter:
    batch = game.api.batch(gets=[GetOp.inventory(r["grid"], r["min"]) for r in refs])
    total = Counter()
    for i in range(len(refs)):
        for item in batch.get(i)["items"]:
            if item["typeId"].endswith("Component"):
                total[item["subtypeId"]] += item["amountRaw"] // 1_000_000
    return total


def stock(game, refs, timeout: float = 30.0) -> Counter:
    """Components in the inventories of these blocks, once two reads agree. A
    server's client gets each inventory's changes on its own, so a single read
    can catch an item that has left one inventory and not yet reached the
    other."""
    deadline = time.monotonic() + timeout
    last = _stock(game, refs)
    while True:
        time.sleep(3)
        total = _stock(game, refs)
        if total == last or time.monotonic() > deadline:
            return total
        last = total


def installed(game, grid_id: int, cells) -> Counter:
    """Components in these blocks of a grid, from the game's own count of
    what each still misses. A head's free first component doesn't count."""
    cubes = game.cubes(grid_id)
    calls = [
        CallOp.slim_block_method(grid_id, cell, "GetMissingComponents")
        for cell in cells
    ]
    result = game.api.call(calls)
    total = Counter()
    for i, cell in enumerate(cells):
        subtype = cubes[cell]["subtypeId"]
        missing = result.call(i)["components"]
        total.update(survival.installed(survival.COSTS[subtype], missing))
        free = survival.FREE_FIRST_COMPONENT.get(subtype)
        if free:
            total[free] -= 1
    return total


def projected_cells() -> list[tuple[int, int, int]]:
    """The cells of the station's blocks in the projection"""
    ids = {"projector": PROJECTOR}
    return [
        block_min(b)
        for b in stations.blueprint_grids(BENCH)[0].find("CubeBlocks")
        if not stations.is_infrastructure(b, ids)
    ]


def set_welders(game, welders, on: bool) -> None:
    for welder in welders:
        game.api.set_enabled(welder["grid"], welder["min"], on)


def wait_until(check, timeout: float, interval: float = 2.0):
    deadline = time.monotonic() + timeout
    while True:
        result = check()
        if result or time.monotonic() > deadline:
            return result
        time.sleep(interval)


def stand_on_station(game) -> None:
    """Puts the character on the station's strip. A server takes block changes
    from a client only from a character within 15 m of the grid."""
    cell = game.api.call([CallOp.grid_to_world(STATION, survival.STANDING)]).call(0)
    game.api.character_teleport(*cell["world"])
    time.sleep(3)


@pytest.fixture(scope="module")
def welded(game):
    """Turns the welder columns on until the rotor and the piston with their
    payloads are built and finished. Returns (report, stock before, stock
    after)."""
    stand_on_station(game)
    refs = survival.WELDERS + survival.CARGOS
    game.wait_report(PROJECTOR, lambda r: r.scan > 0)
    before = stock(game, refs)
    set_welders(game, survival.WELDERS, True)

    def done():
        report = game.report(PROJECTOR)
        combos = all(report.subgrids[i].complete for i in COMBO_SUBGRIDS)
        only_obscured = set(report.subgrids[0].states) == {survival.OBSCURED}
        return report if combos and only_obscured else None

    report = wait_until(done, 600, 5) or game.report(PROJECTOR)
    set_welders(game, survival.WELDERS, False)
    # Components still on their way through the conveyors
    time.sleep(5)
    return report, before, stock(game, refs)


def test_combos_are_built_and_finished(game, welded):
    report, _, _ = welded
    for index in COMBO_SUBGRIDS:
        subgrid = report.subgrids[index]
        assert subgrid.complete, subgrid.states
        cubes = game.cubes(subgrid.built)
        assert len(cubes) == blueprint.grid_block_count(BENCH, index)
        assert all(c["isFullIntegrity"] for c in cubes.values()), cubes
    station = game.cubes(STATION)
    for cell in projected_cells():
        if cell != survival.OBSCURED:
            assert station[cell]["isFullIntegrity"], station[cell]


def test_components_go_into_the_blocks(game, welded):
    report, before, after = welded
    used = Counter(before)
    used.subtract(after)
    built = installed(
        game, STATION, [c for c in projected_cells() if c != survival.OBSCURED]
    )
    for index in COMBO_SUBGRIDS:
        grid_id = report.subgrids[index].built
        built.update(installed(game, grid_id, list(game.cubes(grid_id))))
    assert +used == +built


def piston_position(game) -> float:
    """The piston's extension in meters, from its detailed info"""
    info = game.api.get_block(STATION, survival.PISTON)["detailedInfo"]
    return float(re.search(r"Current position: ([\d.]+)m", info).group(1))


def piston_to(game, meters: float, timeout: float = 60.0) -> None:
    """Moves the piston of the issue #136 rig and waits until it stops there"""
    grid, cell = STATION, survival.PISTON
    speed = 1.0 if meters > piston_position(game) else -1.0
    game.api.set_property(grid, cell, "UpperLimit", meters)
    game.api.set_property(grid, cell, "LowerLimit", meters)
    game.api.set_property(grid, cell, "Velocity", speed)
    arrived = wait_until(lambda: abs(piston_position(game) - meters) < 0.05, timeout, 1)
    assert arrived, game.api.get_block(grid, cell)["detailedInfo"]


def obstructed(game) -> bool:
    """Whether the game's Havok check finds the armor block's cell obstructed.
    MGP checks it only while the projector highlights blocks, and only on its
    scans, so this turns highlighting on for one scan."""
    game.api.apply_action(STATION, PROJECTOR_CELL, "BlockHighlightEnable")
    try:
        state = game.report(PROJECTOR).subgrids[0].states.get(survival.OBSCURED)
    finally:
        game.api.apply_action(STATION, PROJECTOR_CELL, "BlockHighlightDisable")
    # Back to MGP's usual scan without the check before the welder gets to
    # work, so the welder takes the path it takes in the issue
    game.wait_report(
        PROJECTOR,
        lambda r: r.subgrids[0].states.get(survival.OBSCURED) == "Buildable",
    )
    return state == "NotBuildable"


PISTON_REFS = [survival.PISTON_WELDER_REF, survival.PISTON_CARGO_REF]
OVERLAPS = list(survival.OVERLAPPING_M)


@pytest.fixture(scope="module")
def obscured(game, welded):
    """The piston's welder turned on for a while with its body in the armor
    block's cell, at each depth: depth -> (stock before, stock after, the
    cell's cube or None)"""
    results = {}
    for depth in OVERLAPS:
        piston_to(game, survival.OVERLAPPING_M[depth])
        # A server runs no Havok check for MGP's highlighting, which is a
        # client feature; the geometry is the same as in single player
        if game.api.get_state().get("multiplayer") == "offline":
            assert obstructed(game), depth
        before = stock(game, PISTON_REFS)
        set_welders(game, [survival.PISTON_WELDER_REF], True)
        time.sleep(30)
        set_welders(game, [survival.PISTON_WELDER_REF], False)
        after = stock(game, PISTON_REFS)
        results[depth] = before, after, game.cubes(STATION).get(survival.OBSCURED)
    return results


@pytest.mark.parametrize("depth", OVERLAPS)
def test_welder_in_the_block_cell_builds_nothing(obscured, depth):
    _, _, cube = obscured[depth]
    assert cube is None


@pytest.mark.parametrize("depth", OVERLAPS)
def test_welder_in_the_block_cell_uses_up_nothing(obscured, depth):
    before, after, _ = obscured[depth]
    assert after == before


def test_welder_clear_of_the_block_builds_it_for_its_components(game, obscured):
    piston_to(game, survival.CLEAR_M)
    before = stock(game, PISTON_REFS)
    set_welders(game, [survival.PISTON_WELDER_REF], True)

    def finished():
        cube = game.cubes(STATION).get(survival.OBSCURED)
        return cube if cube and cube["isFullIntegrity"] else None

    cube = wait_until(finished, 120)
    set_welders(game, [survival.PISTON_WELDER_REF], False)
    assert cube, game.cubes(STATION).get(survival.OBSCURED)
    time.sleep(5)
    used = Counter(before)
    used.subtract(stock(game, PISTON_REFS))
    assert +used == Counter(survival.COSTS[cube["subtypeId"]])
