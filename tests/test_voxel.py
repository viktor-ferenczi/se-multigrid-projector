"""Welding projected blocks that reach into the terrain.

Two stations stand on the ground beside the saved character, a large and a
small static grid. Each projects itself with a column of armor blocks hanging
from its floor down into the planet. The game checks every block built on a
grid, projected ones too, against the voxel rule of the grid's building
settings (MyCubeGrid.CanPlaceBlock on the server): a large static grid may
reach into voxels, a small static grid may not. MGP has to agree, so the large
station's column is welded whole and the small station's stops at the terrain.

The stations stand on measured ground: the first test checks that the columns
still start above the terrain and end in it.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

import world

WORLD_SETTINGS = {"GameMode": "Creative"}
BENCHES: list[str] = []

STATION_ID = 777000800000000


@dataclass
class Station:
    name: str
    size: str
    # From the saved character: along the stations' right axis, and the floor
    # cell's center above the character's feet. The character stands about
    # 15.5 m above the terrain there.
    right_m: float
    up_m: float
    # Armor blocks hanging from the floor
    depth: int
    grid_id: int

    @property
    def projector_id(self) -> int:
        return self.grid_id + 1

    @property
    def cell_m(self) -> float:
        return world.LARGE_M if self.size == "Large" else world.SMALL_M

    @property
    def column(self) -> list[tuple[int, int, int]]:
        return [(0, -k, 0) for k in range(1, self.depth + 1)]


STATIONS = [
    Station("large", "Large", -40.0, -13.75, 4, STATION_ID),
    Station("small", "Small", -60.0, -14.5, 10, STATION_ID + 10000),
]
REPORT_PROJECTORS = [s.projector_id for s in STATIONS]


def frame(station: Station):
    """Position, forward and up of the station's grid"""
    character, forward, up = world.frame(0)
    character = [character[i] - up[i] * world.ALTITUDE_M for i in range(3)]
    right = world._cross(forward, up)
    position = [
        character[i] + right[i] * station.right_m + up[i] * station.up_m
        for i in range(3)
    ]
    return position, forward, up


def station_xml(station: Station) -> str:
    small = station.size == "Small"
    floor = "".join(world.armor(p, station.size) for p in [(0, 0, 0), (1, 0, 0)])
    battery = world.block(
        "BatteryBlock",
        "SmallBlockSmallBatteryBlock" if small else "LargeBlockBatteryBlock",
        (1, 1, 0),
        station.grid_id + 2,
        "<Enabled>true</Enabled><CurrentStoredPower>3</CurrentStoredPower>"
        "<ProducerEnabled>true</ProducerEnabled>",
    )
    column = "".join(world.armor(p, station.size) for p in station.column)

    def projector(projected: str) -> str:
        return world.block(
            "Projector",
            "SmallProjector" if small else "LargeProjector",
            (0, 1, 0),
            station.projector_id,
            f"<CustomName>Projector {station.name}</CustomName><Enabled>true</Enabled>"
            f"{projected}<KeepProjection>true</KeepProjection>"
            "<ShowOnlyBuildable>false</ShowOnlyBuildable>",
        )

    position, forward, up = frame(station)
    blueprint = world.grid(
        f"Voxel {station.name}",
        station.grid_id,
        projector("") + battery + floor + column,
        position,
        forward,
        up,
        True,
        station.size,
        tag="MyObjectBuilder_CubeGrid",
    )
    return world.grid(
        f"Voxel {station.name}",
        station.grid_id,
        projector(f"<ProjectedGrids>{blueprint}</ProjectedGrids>") + battery + floor,
        position,
        forward,
        up,
        True,
        station.size,
    )


SECTOR_OBJECTS = "".join(station_xml(s) for s in STATIONS)


def elevation(game, station: Station, cell) -> float:
    """The cell center's height over the terrain, negative under it"""
    position, _, up = frame(station)
    point = [position[i] + up[i] * cell[1] * station.cell_m for i in range(3)]
    return game.api.get_planet_at(*point)["planet"]["elevation"]


@pytest.fixture(scope="module")
def welded(game):
    game.require_ops("WeldProjection")
    game.wait_grids([s.grid_id for s in STATIONS])
    game.api.set_admin_flag("creativeTools", True)
    return {s.name: game.weld(s.projector_id) for s in STATIONS}


@pytest.mark.parametrize("station", STATIONS, ids=lambda s: s.name)
def test_column_reaches_into_the_terrain(game, station):
    floor = elevation(game, station, (0, 0, 0))
    bottom = elevation(game, station, station.column[-1])
    print(f"{station.name}: floor {floor:.2f} m, bottom {bottom:.2f} m")
    assert floor > station.cell_m / 2
    assert bottom < -station.cell_m


def test_large_static_grid_welds_into_voxels(welded):
    report = welded["large"]
    assert report.complete, {s.index: s.states for s in report.subgrids if s.states}


def test_small_static_grid_stops_at_the_terrain(game, welded):
    station = STATIONS[1]
    report = welded["small"]
    # MGP's block states come from its scan, which skips the voxel check: the
    # first block in the terrain shows as buildable, but no weld builds it
    states = report.subgrids[0].states
    print(f"small: left open {states}")
    assert states, "the whole column was welded"
    assert station.column[-1] in states
    built = [c for c in station.column if c not in states]
    assert all(elevation(game, station, c) > -station.cell_m / 2 for c in built)
