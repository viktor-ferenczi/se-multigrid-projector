"""Load Repair Projection while someone sits on the grid (DIS-0093)

The client's character sits in a cockpit of a station, then the client presses
Load Repair Projection on the station's projector. MGP took the grid's object
builder with the seated character in it. Cloning the blueprint before sending it
to the server drops the empty RegenEffects list of the character's suit battery,
and the multiplayer event serializer threw on the null list, which crashed the
client: "Error serializing MyObjectBuilder_Battery.RegenEffects, member contains
null". Vanilla blueprints never carry a pilot: the game clears them when it
copies a grid to the clipboard.

The repair-probe plugin next to this file adds a projector action that presses
the terminal button, so Remote can press it.
"""

from __future__ import annotations

import time
from pathlib import Path

import ds_rig
import rig
import world
from se_remote import CallOp
from stations import PB_OWNER

BENCHES: list[str] = []

PROBE = Path(__file__).parent / "repair-probe"
CLIENT_PLUGINS = [("repair-probe", "repair-probe", PROBE, "RepairProbe.xml")]
LOAD_REPAIR = "MgpTestLoadRepairProjection"

STATION = 777000930000000
PROJECTOR = STATION + 1
PROJECTOR_CELL = (0, 1, 0)
COCKPIT = STATION + 3
COCKPIT_CELL = (0, 1, 3)
STANDING = (1, 1, 3)

OWNED = (
    f"<Owner>{PB_OWNER}</Owner><BuiltBy>{PB_OWNER}</BuiltBy><ShareMode>All</ShareMode>"
)


def station() -> str:
    blocks = world.block(
        "Projector",
        "LargeProjector",
        PROJECTOR_CELL,
        PROJECTOR,
        OWNED + "<CustomName>Repair</CustomName><Enabled>true</Enabled>"
        "<ShowOnlyBuildable>false</ShowOnlyBuildable>",
    )
    blocks += world.battery((1, 1, 0), STATION + 2)
    blocks += world.block(
        "Cockpit", "LargeBlockCockpitSeat", COCKPIT_CELL, COCKPIT, OWNED
    )
    blocks += "".join(world.armor((x, 0, z)) for x in range(3) for z in range(5))
    return world.grid("Seated Ship", STATION, blocks, *world.frame(-2), True)


SECTOR_OBJECTS = station()


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


def client_log() -> str:
    return ds_rig.CLIENT.log.read_text(errors="replace")


def wait_probe(timeout: float = 60.0) -> None:
    deadline = time.monotonic() + timeout
    while "RepairProbe: action added" not in client_log():
        if time.monotonic() > deadline:
            raise TimeoutError("The repair-probe plugin did not add its action")
        time.sleep(1)


def test_load_repair_projection_while_seated(game):
    game.wait_grids([STATION])
    wait_probe()
    projector = game.api.get_block(STATION, PROJECTOR_CELL)
    assert projector["isWorking"]
    assert not projector["projector"]["isProjecting"]

    sit_in_cockpit(game)
    game.api.apply_action(STATION, PROJECTOR_CELL, LOAD_REPAIR)

    deadline = time.monotonic() + 30
    stats = {}
    while time.monotonic() < deadline:
        assert rig.running_pid(ds_rig.CLIENT), "The client crashed"
        stats = game.api.get_block(STATION, PROJECTOR_CELL)["projector"]
        if stats["isProjecting"]:
            break
        time.sleep(1)
    print(f"projector: {stats}")
    assert "Error serializing" not in client_log()
    assert stats["isProjecting"]
    # The character stays seated and the projection has no pilot of its own
    controlled = game.api.get_character().get("controlledEntity") or {}
    assert controlled.get("entityId") == COCKPIT
