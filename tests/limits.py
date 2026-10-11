"""The projection limit tests (GitHub issue #86): a player whose PCU limit holds
one test projection but not two.

A station of its own, left of the control station, with two empty projectors.
Both were built by a player of their own, added to the world for this, so the
PCU of these two blocks is all the player uses. The tests load a plate of
armor blocks into the projectors through Remote, the way the blueprint screen
does it.

With PCU limits per player, MaxPlayers 4 and TotalPCU 1600 the player may use
400 PCU. The projectors take 2 x 50 PCU and the plate is 200 PCU. A server with
a projection limit of 100 percent takes one plate (300 PCU), but not a second
one (500 PCU), and takes it again once the first projector is gone (250 PCU).
"""

from __future__ import annotations

import time
from pathlib import Path

import world
from se_remote import CallOp

PLAYER = 144115188075899001
STATION = 777000600000000
PROJECTOR_A = STATION + 1
PROJECTOR_B = STATION + 2
CELL_A = (0, 1, 1)
CELL_B = (8, 1, 1)
STANDING = (4, 1, 0)
PLATE = (10, 20)

WORLD_SETTINGS = {
    "GameMode": "Creative",
    "BlockLimitsEnabled": "PER_PLAYER",
    "MaxPlayers": "4",
    "TotalPCU": "1600",
}


def _projector(cell, entity_id: int, name: str) -> str:
    return world.block(
        "Projector",
        "LargeProjector",
        cell,
        entity_id,
        f"<BuiltBy>{PLAYER}</BuiltBy>"
        f"<CustomName>{name}</CustomName><Enabled>true</Enabled>"
        "<KeepProjection>true</KeepProjection>"
        "<ShowOnlyBuildable>false</ShowOnlyBuildable>",
    )


def station() -> str:
    """The station as a sector object"""
    position, forward, up = world.frame(-1)
    blocks = "".join(world.armor((x, 0, z)) for x in range(9) for z in range(3))
    blocks += world.battery((4, 1, 1), STATION + 3)
    blocks += _projector(CELL_A, PROJECTOR_A, "Limit A")
    blocks += _projector(CELL_B, PROJECTOR_B, "Limit B")
    return world.grid("MGP Limits", STATION, blocks, position, forward, up, True)


def add_player(world_folder: Path) -> None:
    """The station's builder, a player identity without a character"""
    path = world_folder / "Sandbox.sbc"
    text = path.read_text(encoding="utf-8")
    identity = (
        "<MyObjectBuilder_Identity>"
        f"<IdentityId>{PLAYER}</IdentityId><DisplayName>MGP Limits</DisplayName>"
        "<CharacterEntityId>0</CharacterEntityId>"
        "<BlockLimitModifier>0</BlockLimitModifier>"
        "</MyObjectBuilder_Identity>"
    )
    assert "<Identities>" in text
    path.write_text(text.replace("<Identities>", "<Identities>" + identity, 1))


def plate_xml() -> str:
    """A blueprint of armor blocks in a flat plate"""
    width, depth = PLATE
    blocks = "".join(world.armor((x, 0, z)) for x in range(width) for z in range(depth))
    grid = world.grid(
        "Plate", 0, blocks, (0, 0, 0), (0, 0, -1), (0, 1, 0), False, tag="CubeGrid"
    )
    return world.blueprint_xml("Plate", grid)


def stand_on_station(game) -> None:
    """A server takes the new blueprint of a projector only from a client whose
    character is near the grid"""
    cell = game.api.call([CallOp.grid_to_world(STATION, STANDING)]).call(0)
    game.api.character_teleport(*cell["world"])
    time.sleep(3)


def load(game, projector: int) -> None:
    game.call(projector, "LoadProjection", {"xml": plate_xml()})


def projected(game, projector: int) -> bool:
    """Whether MGP projects in the server's view, from the report script"""
    return bool(game.report(projector).subgrids)


def wait_projected(game, projector: int, expected: bool, timeout: float) -> bool:
    """Waits up to timeout for the server to project (or stop projecting) and
    returns the last state"""
    deadline = time.monotonic() + timeout
    while True:
        state = projected(game, projector)
        if state == expected or time.monotonic() > deadline:
            return state


def client_projecting(game, cell) -> bool:
    """Whether the projector projects in this client's view"""
    return game.api.get_block(STATION, cell)["projector"]["isProjecting"]
