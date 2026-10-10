"""The survival bench's ship welders, conveyors and stocked cargo containers.

The survival bench (benches.py) projects a rotor and a piston, each with an
armor block on its head, and an armor block on the floor strip. The test world
adds these to the bench's station, outside the projection:

- A column of large ship welders beside each base, one per level, pointing at
  the base and the head and payload above it. Behind each column a column of
  conveyor junctions runs down to a cargo container with the components.
- The welder on a piston of GitHub issue #136: a piston lying on the strip,
  pointing at the strip's armor block, with a ship welder on its head and a
  cargo container behind its base. Extending the piston pushes the welder into
  the armor block's cell; a shorter extension leaves the welder clear of the
  cell with the block still in its reach.

Every welder starts turned off. The station's blocks belong to the template
world's player, like the report block in stations.py.
"""

from __future__ import annotations

import math

import world
from fixtures import bench_ids, bench_index
from stations import PB_OWNER, blueprint_grids

BENCH = "survival"
IDS = bench_ids(bench_index(BENCH))
STATION = IDS["grid"]
PROJECTOR = IDS["projector"]

# Base cell -> welder levels, from the fixture: the rotor's head and payload sit
# 0.2 and 1.2 cells above its base, the piston's 1.1 and 2.1
COLUMNS = {(2, 1, 3): 3, (10, 1, 3): 4}

# The issue #136 rig: the armor block on the strip (benches.py), and the piston
# lying on the strip. The base is three cells long, its head 1.064 cells above
# the base's bottom cell when retracted.
OBSCURED = (4, 1, 1)
PISTON = (7, 1, 1)
PISTON_BOTTOM_X = PISTON[0] + 2
PISTON_HEAD_OFFSET = 1.064
# Extensions in meters. The welder's tip doesn't fill its cell: the game's
# Havok check finds the armor block's cell obstructed from 2.8 m on, when the
# cells overlap by 0.3 m, and free at 2.6 m. Overlapping just past that, deep
# into the cell, and 0.8 m clear of the cell.
OVERLAPPING_M = {"shallow": 2.9, "deep": 3.5}
CLEAR_M = 1.5

# Where the character stands while the tests turn the welders on and off: on
# the strip, clear of the welders and the projection
STANDING = (14, 1, 0)

PISTON_ID = STATION + 520
TOP_GRID_ID = STATION + 600
TOP_ID = TOP_GRID_ID + 1
PISTON_WELDER_ID = TOP_GRID_ID + 2
PISTON_WELDER = (0, 1, 0)
PISTON_CARGO = (PISTON_BOTTOM_X + 1, 1, 1)

# What the containers hold, plenty for the whole projection
STOCK = {
    "SteelPlate": 400,
    "Construction": 100,
    "LargeTube": 60,
    "Motor": 30,
    "Computer": 30,
}

# Components of the blocks the welders build, from the game's CubeBlocks
# definitions, and the first component, which the game gives a head created
# at construction stage for free
COSTS = {
    "LargeBlockArmorBlock": {"SteelPlate": 25},
    "LargeStator": {
        "SteelPlate": 30,
        "Construction": 20,
        "LargeTube": 5,
        "Motor": 5,
        "Computer": 5,
    },
    "LargeRotor": {"SteelPlate": 30, "LargeTube": 10},
    "LargePistonBase": {
        "SteelPlate": 50,
        "Construction": 30,
        "LargeTube": 10,
        "Motor": 10,
        "Computer": 5,
    },
    "LargePistonTop": {"SteelPlate": 10, "LargeTube": 8},
}
FREE_FIRST_COMPONENT = {"LargeRotor": "SteelPlate", "LargePistonTop": "SteelPlate"}

OWNED = (
    f"<Owner>{PB_OWNER}</Owner><BuiltBy>{PB_OWNER}</BuiltBy><ShareMode>All</ShareMode>"
)


def _inventory(items: dict[str, int]) -> str:
    entries = "".join(
        "<MyObjectBuilder_InventoryItem>"
        f"<Amount>{amount}</Amount>"
        '<PhysicalContent xsi:type="MyObjectBuilder_Component">'
        f"<SubtypeName>{subtype}</SubtypeName></PhysicalContent>"
        f"<ItemId>{i}</ItemId></MyObjectBuilder_InventoryItem>"
        for i, (subtype, amount) in enumerate(items.items())
    )
    return (
        "<ComponentContainer><Components><ComponentData>"
        "<TypeId>MyInventoryBase</TypeId>"
        '<Component xsi:type="MyObjectBuilder_Inventory">'
        f"<Items>{entries}</Items><nextItemId>{len(items)}</nextItemId>"
        "</Component></ComponentData></Components></ComponentContainer>"
    )


def cargo(pos, entity_id: int) -> str:
    return world.block(
        "CargoContainer",
        "LargeBlockSmallContainer",
        pos,
        entity_id,
        OWNED + _inventory(STOCK),
    )


def welder(pos, entity_id: int, forward: str, up: str) -> str:
    return world.block(
        "ShipWelder",
        "LargeShipWelder",
        pos,
        entity_id,
        OWNED + "<Enabled>false</Enabled><UseConveyorSystem>true</UseConveyorSystem>",
        forward=forward,
        up=up,
    )


def conveyor(pos, entity_id: int) -> str:
    return world.block("Conveyor", "LargeBlockConveyor", pos, entity_id, OWNED)


def columns() -> tuple[list[dict], str]:
    """The welder columns: (welders as {"id", "grid", "min"}, station blocks)"""
    welders, xml, n = [], "", 0
    for (x, _, z), levels in COLUMNS.items():
        for y in range(1, levels + 1):
            entity_id = STATION + 500 + n
            # Two cells long, pointing at the base column from its +x side
            xml += welder((x + 1, y, z), entity_id, "Left", "Up")
            xml += conveyor((x + 3, y, z), STATION + 700 + n)
            welders.append({"id": entity_id, "grid": STATION, "min": (x + 1, y, z)})
            n += 1
        cargo_pos = (x + 3, 0, z)
        xml += cargo(cargo_pos, STATION + 800 + x)
    return welders, xml


WELDERS, _COLUMNS_XML = columns()
CARGOS = [{"grid": STATION, "min": (x + 3, 0, z)} for x, _, z in COLUMNS]
PISTON_WELDER_REF = {"id": PISTON_WELDER_ID, "grid": TOP_GRID_ID, "min": PISTON_WELDER}
PISTON_CARGO_REF = {"grid": STATION, "min": PISTON_CARGO}


def _station_frame():
    """Position, forward and up of the station, as the fixture has it"""
    po = blueprint_grids(BENCH)[0].find("PositionAndOrientation")

    def vector(tag):
        return [float(po.find(tag).get(a)) for a in "xyz"]

    return vector("Position"), vector("Forward"), vector("Up")


def _cell_to_world(cell) -> list[float]:
    position, forward, up = _station_frame()
    right = [
        forward[1] * up[2] - forward[2] * up[1],
        forward[2] * up[0] - forward[0] * up[2],
        forward[0] * up[1] - forward[1] * up[0],
    ]
    size = world.LARGE_M
    return [
        position[i]
        + size * (cell[0] * right[i] + cell[1] * up[i] - cell[2] * forward[i])
        for i in range(3)
    ]


def piston_rig() -> tuple[str, str]:
    """The piston on the strip, pointing at the obscured block along -x, with a
    welder on its head: (station blocks, the head's grid)"""
    station = world.block(
        "ExtendedPistonBase",
        "LargePistonBase",
        PISTON,
        PISTON_ID,
        OWNED + f"<Enabled>true</Enabled><TopBlockId>{TOP_ID}</TopBlockId>"
        "<Velocity>0</Velocity><MaxLimit>10</MaxLimit><MinLimit>0</MinLimit>"
        "<CurrentPosition>0</CurrentPosition>",
        forward="Forward",
        up="Left",
    )
    station += cargo(PISTON_CARGO, STATION + 530)

    _, forward, _ = _station_frame()
    origin = _cell_to_world((0, 0, 0))
    unit_x = [a - b for a, b in zip(_cell_to_world((1, 0, 0)), origin)]
    left = [-c / world.LARGE_M for c in unit_x]
    head = _cell_to_world((PISTON_BOTTOM_X - PISTON_HEAD_OFFSET, PISTON[1], PISTON[2]))
    blocks = world.block(
        "PistonTop",
        "LargePistonTop",
        (0, 0, 0),
        TOP_ID,
        OWNED + f"<ParentEntityId>{PISTON_ID}</ParentEntityId>",
    )
    # On the head's top, pointing away from the piston
    blocks += welder(PISTON_WELDER, PISTON_WELDER_ID, "Up", "Forward")
    assert math.isclose(sum(c * c for c in left), 1.0, rel_tol=1e-4)
    grid = world.grid(
        "Survival Piston Head", TOP_GRID_ID, blocks, head, forward, left, False
    )
    return station, grid


def extras() -> dict[str, tuple[str, str]]:
    """STATION_EXTRAS of the test files (stations.sector_objects)"""
    station, grid = piston_rig()
    return {BENCH: (_COLUMNS_XML + station, grid)}


def installed(cost: dict[str, int], missing: dict[str, int]) -> dict[str, int]:
    return {k: v - missing.get(k, 0) for k, v in cost.items()}
