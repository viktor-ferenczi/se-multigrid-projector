"""Reading the bench blueprints, for what the tests expect"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache

from fixtures import block_min
from stations import blueprint_grids


@dataclass(frozen=True)
class Block:
    grid: int
    subtype: str
    min: tuple[int, int, int]
    entity_id: int
    top_id: int


@dataclass(frozen=True)
class Connection:
    base_grid: int
    base: str
    top_grid: int
    top: str
    # The combination's name, which the generator gave the top part's grid
    name: str


@cache
def blocks(bench: str) -> tuple[Block, ...]:
    result = []
    for index, grid in enumerate(blueprint_grids(bench)):
        for block in grid.find("CubeBlocks"):
            result.append(
                Block(
                    index,
                    block.findtext("SubtypeName"),
                    block_min(block),
                    int(block.findtext("EntityId") or 0),
                    int(block.findtext("TopBlockId") or 0),
                )
            )
    return tuple(result)


@cache
def grid_sizes(bench: str) -> tuple[str, ...]:
    return tuple(g.findtext("GridSizeEnum") for g in blueprint_grids(bench))


@cache
def connections(bench: str) -> tuple[Connection, ...]:
    by_id = {b.entity_id: b for b in blocks(bench) if b.entity_id}
    names = [g.findtext("DisplayName") for g in blueprint_grids(bench)]
    return tuple(
        Connection(
            b.grid,
            b.subtype,
            by_id[b.top_id].grid,
            by_id[b.top_id].subtype,
            names[by_id[b.top_id].grid],
        )
        for b in blocks(bench)
        if b.top_id
    )


def grid_block_count(bench: str, grid: int) -> int:
    return sum(1 for b in blocks(bench) if b.grid == grid)


def builder(bench: str, name: str):
    """The blueprint's object builder of the block with this custom name"""
    for grid in blueprint_grids(bench):
        for block in grid.find("CubeBlocks"):
            if block.findtext("CustomName") == name:
                return block
    raise KeyError(name)


@cache
def names_by_id(bench: str) -> dict[int, str]:
    return {
        int(block.findtext("EntityId")): block.findtext("CustomName")
        for grid in blueprint_grids(bench)
        for block in grid.find("CubeBlocks")
        if block.findtext("CustomName")
    }
