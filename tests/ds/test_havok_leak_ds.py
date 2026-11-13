"""Havok memory with a repair projection on a damaged ship (SE-1381).

A client of a server without the MGP server plugin sits in the cockpit of a
station whose projector shows the station with blocks missing next to its ship
welders, the way a repair projection of a damaged ship does. Ship Welding (on by
default) checks the missing blocks with the game's Havok placement test, which
leaked the convex shapes of every block that is not a plain box: the game wraps
them into an HkListShape with HkReferencePolicy.None and releases only the list.
The client's Havok memory grew by tens of MB a minute until Havok ran out.

The welders have no components, so nothing gets built and the checks go on for
the whole test. The game logs the Havok memory in the Physics column of its
MEMORY VALUES lines, once a minute. The stats-probe plugin next to this file
makes the client log them every 2 seconds, so 40 seconds of them are enough.

The leak is the game's and the Bugfixes plugin fixes it. With MGP_BUGFIXES_REPO
set to a working copy of CometWorks/bugfixes the client and the server run with
Bugfixes and the memory must stay flat. Without it the memory must grow: that
run shows that Ship Welding still does its checks, and it fails once the game
or MGP stops leaking, when the test has nothing left to guard.

The station has one damaged block in the welders' reach. A vanilla ship
welder searches the projection only while it has a target, as on a damaged ship.

The client starts with the config file of an MGP before 0.9.2, as the report's
player had. MGP failed to read it and silently used the defaults; now it
converts the file and keeps its options.
"""

from __future__ import annotations

import os
import re
import time
from pathlib import Path
import xml.etree.ElementTree as ET

import ds_rig
import world
from se_remote import CallOp
from stations import PB_OWNER

MGP_SERVER = False
BENCHES: list[str] = []

PROBE = Path(__file__).parent / "stats-probe"
CLIENT_PLUGINS = [("stats-probe", "stats-probe", PROBE, "StatsProbe.xml")]
BUGFIXES = os.environ.get("MGP_BUGFIXES_REPO")
if BUGFIXES:
    CLIENT_PLUGINS += [("bugfixes", "bugfixes", Path(BUGFIXES), "BugfixesClient.xml")]
    SERVER_PLUGINS = [("bugfixes", "bugfixes", Path(BUGFIXES), "BugfixesServer.xml")]

STATION = 777000900000000
PROJECTOR = STATION + 1
COCKPIT = STATION + 3
COCKPIT_CELL = (0, 1, 6)
STANDING = (1, 1, 6)
# A long row of welders: the leak grows with the welders and the blocks in reach.
# Havok takes the first 40 MB or so from the free space of its pool, where the
# Physics value does not show it. This many welders leak that in seconds.
LENGTH = 100
WELDER_ROWS = range(1, LENGTH - 1)
# The missing blocks: on the floor in front of the welders, every kind the
# game builds the Havok shape of from the block's topology
MISSING_KINDS = (
    "LargeBlockArmorSlope",
    "LargeBlockArmorCorner",
    "LargeBlockArmorCornerInv",
    "LargeBlockArmorBlock",
)
# Built, but damaged: the vanilla welders' target
DAMAGED = (4, 1, 3)
MISSING = [(x, 1, z) for x in (2, 3, 4) for z in WELDER_ROWS if (x, 1, z) != DAMAGED]

# The stats-probe plugin's log interval
LOG_SECONDS = 2
# MEMORY VALUES lines after the character sat down: 40 seconds
SAMPLES = 21
# Havok's pooled memory moves by a megabyte or two on its own
MAX_GROWTH_MB = 2
# Without the game fix
MIN_LEAK_MB = 10

OWNED = (
    f"<Owner>{PB_OWNER}</Owner><BuiltBy>{PB_OWNER}</BuiltBy><ShareMode>All</ShareMode>"
)


def _blocks(projection: str | None) -> str:
    """The station's blocks. With a projection (the built station) the
    projector shows it; without one (the blueprint) the missing blocks are in."""
    # The projector first: the projection lands on the station itself
    projected = f"<ProjectedGrids>{projection}</ProjectedGrids>" if projection else ""
    xml = world.block(
        "Projector",
        "LargeProjector",
        (0, 1, 0),
        PROJECTOR,
        OWNED + "<CustomName>Repair</CustomName><Enabled>true</Enabled>"
        f"{projected}<KeepProjection>true</KeepProjection>"
        "<ShowOnlyBuildable>false</ShowOnlyBuildable>",
    )
    xml += world.battery((1, 1, 0), STATION + 2)
    xml += world.block("Cockpit", "LargeBlockCockpitSeat", COCKPIT_CELL, COCKPIT, OWNED)
    for z in WELDER_ROWS:
        # Two cells long, pointing at the missing blocks along -x
        xml += world.block(
            "ShipWelder",
            "LargeShipWelder",
            (5, 1, z),
            STATION + 10 + z,
            OWNED
            + "<Enabled>true</Enabled><UseConveyorSystem>true</UseConveyorSystem>",
            forward="Left",
        )
    xml += "".join(world.armor((x, 0, z)) for x in range(7) for z in range(LENGTH))
    damaged = "<IntegrityPercent>0.3</IntegrityPercent><BuildPercent>0.3</BuildPercent>"
    xml += world.block(
        "CubeBlock", "LargeBlockArmorBlock", DAMAGED, 0, damaged if projection else ""
    )
    if projection is None:
        xml += "".join(
            world.block("CubeBlock", MISSING_KINDS[i % len(MISSING_KINDS)], cell)
            for i, cell in enumerate(MISSING)
        )
    return xml


def station() -> str:
    frame = world.frame(-2)
    blueprint = world.grid(
        "Damaged Ship",
        STATION,
        _blocks(None),
        *frame,
        True,
        tag="MyObjectBuilder_CubeGrid",
    )
    return world.grid("Damaged Ship", STATION, _blocks(blueprint), *frame, True)


SECTOR_OBJECTS = station()

CONFIG = ds_rig.CLIENT.appdata / "Storage" / "MultigridProjector.cfg"
# As MGP 0.9.1 wrote it, Block Highlight off
OLD_CONFIG = """<?xml version="1.0" encoding="utf-8"?>
<ConfigObject xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <ShowDialogs>true</ShowDialogs>
  <ClientWelding>true</ClientWelding>
  <ShipWelding>true</ShipWelding>
  <ConnectSubgrids>true</ConnectSubgrids>
  <RepairProjection>true</RepairProjection>
  <ProjectorAligner>true</ProjectorAligner>
  <BlockHighlight>false</BlockHighlight>
  <CraftProjection>true</CraftProjection>
</ConfigObject>
"""


def EDIT_WORLD(_world) -> None:
    """Called before the server and the client start: the client's old config"""
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(OLD_CONFIG, encoding="utf-8")


def physics_mb(log_text: str) -> list[int]:
    """The Physics column of every MEMORY VALUES line of a game log, in MB"""
    legend = re.search(r"MEMORY LEGEND,(.*)", log_text)
    if not legend:
        return []
    column = legend.group(1).strip().split(",").index("Physics") + 1
    return [
        int(line.split(",")[column])
        for line in re.findall(r"MEMORY VALUES,[\d,]+", log_text)
    ]


def sit_in_cockpit(game) -> None:
    cells = game.api.call(
        [
            CallOp.grid_to_world(STATION, STANDING),
            CallOp.grid_to_world(STATION, COCKPIT_CELL),
        ]
    )
    game.api.character_teleport(*cells.call(0)["world"])
    time.sleep(3)
    controlled = {}
    for _ in range(10):
        game.api.character_look_at(*cells.call(1)["world"])
        game.api.character_use()
        time.sleep(2)
        controlled = game.api.get_character().get("controlledEntity") or {}
        if controlled.get("entityId") == COCKPIT:
            return
    raise AssertionError(f"The character did not sit down in the cockpit: {controlled}")


def client_physics_mb() -> list[int]:
    return physics_mb(ds_rig.CLIENT.log.read_text(errors="replace"))


def wait_samples(count: int, after: int, timeout: float) -> list[int]:
    deadline = time.monotonic() + timeout
    while True:
        values = client_physics_mb()[after:]
        if len(values) >= count:
            return values[:count]
        if time.monotonic() > deadline:
            raise TimeoutError(f"Only {len(values)} MEMORY VALUES lines: {values}")
        time.sleep(5)


def test_havok_memory_with_ship_welding(game):
    game.wait_grids([STATION])
    stats = game.api.get_block(STATION, (0, 1, 0))["projector"]
    print(f"projector: {stats}")
    assert stats["isProjecting"]

    welders = [game.api.get_block(STATION, (5, 1, z)) for z in WELDER_ROWS]
    assert all(welder["isWorking"] for welder in welders)
    before = client_physics_mb()
    sit_in_cockpit(game)
    values = wait_samples(SAMPLES, len(before), timeout=LOG_SECONDS * SAMPLES * 4)

    growth = values[-1] - values[0]
    seconds = LOG_SECONDS * (len(values) - 1)
    print(f"client Physics MB before sitting down: {before[-3:]}")
    print(f"client Physics MB, every {LOG_SECONDS} s in the cockpit: {values}")
    print(
        f"client growth: {growth} MB in {seconds} s ({growth * 60 / seconds:.1f} MB/min)"
    )
    if BUGFIXES:
        assert growth <= MAX_GROWTH_MB, values
    else:
        assert growth >= MIN_LEAK_MB, values


def test_old_config_is_converted(game):
    root = ET.parse(CONFIG).getroot()
    assert root.tag == "Config"
    assert root.findtext("ShipWelding") == "true"
    assert root.findtext("BlockHighlight") == "false"
