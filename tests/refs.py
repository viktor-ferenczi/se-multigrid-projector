"""The references bench: blocks whose toolbars and block references point across
subgrids, the links MGP's ReferenceFixer restores on welded blocks.

A rotor on the station carries a row of three armor blocks; on that row stand a
light, a camera and a timer. The station's row of functional blocks points at
them, and the subgrid's timer points back at the station. Every block has a
unique name, which is how the tests find the welded blocks.

fixtures.py adds these blocks to the generated bench, then lets the game load
and save them once more, so the blueprint holds them the way the game writes
them.
"""

from __future__ import annotations

import world

# Orientations that mount the block on the cell below it
ON_BACK = dict(forward="Up", up="Backward")

# Name -> (cell on the rotor's subgrid, xsi type, subtype, orientation)
SUBGRID = {
    "Sub Light": ((0, 2, 0), "InteriorLight", "SmallLight", ON_BACK),
    "Sub Camera": ((0, 2, 1), "CameraBlock", "LargeCameraBlock", ON_BACK),
    "Sub Timer": ((0, 2, 2), "TimerBlock", "TimerBlockLarge", {}),
}

# Name -> (cell on the station, xsi type, subtype, orientation)
STATION = {
    "Station Light": ((2, 1, 1), "InteriorLight", "SmallLight", ON_BACK),
    "Station Cockpit": ((3, 1, 1), "Cockpit", "LargeBlockCockpit", {}),
    "Station Timer": ((4, 1, 1), "TimerBlock", "TimerBlockLarge", {}),
    "Station Buttons": ((5, 1, 1), "ButtonPanel", "ButtonPanelLarge", {}),
    "Station Sensor": ((6, 1, 1), "SensorBlock", "LargeBlockSensor", ON_BACK),
    "Station Events": ((7, 1, 1), "EventControllerBlock", "EventControllerLarge", {}),
    "Station Remote": ((8, 1, 1), "RemoteControl", "LargeBlockRemoteControl", {}),
    "Station Turret": (
        (9, 1, 1),
        "TurretControlBlock",
        "LargeTurretControlBlock",
        dict(forward="Backward"),
    ),
    "Station Offensive": (
        (10, 1, 1),
        "OffensiveCombatBlock",
        "LargeOffensiveCombat",
        {},
    ),
    "Station Flight": ((11, 1, 1), "FlightMovementBlock", "LargeFlightMovement", {}),
}

GROUP = "Station Group"
GROUP_MEMBERS = ["Station Light", "Station Timer"]

# What points where: block name -> extra object builder XML, written with the
# entity ids of the names in braces
LINKS = {
    "Station Cockpit": "{toolbar_ship}",
    "Station Timer": "{toolbar:Sub Light}",
    "Station Buttons": "{toolbar:Sub Light}<AnyoneCanUse>true</AnyoneCanUse>",
    "Station Sensor": "{toolbar:Sub Light}<DetectPlayers>false</DetectPlayers>",
    "Station Events": "{toolbar:Station Light}"
    "<SelectedBlocks><long>{Sub Light}</long><long>{Station Light}</long></SelectedBlocks>",
    "Station Remote": "<BindedCamera>{Sub Camera}</BindedCamera>",
    "Station Turret": "<CameraId>{Sub Camera}</CameraId>"
    "<ToolIds><long>{Station Light}</long></ToolIds>",
    "Station Offensive": "{toolbar:Sub Light}",
    "Station Flight": "{toolbar:Station Light}",
    "Sub Timer": "{toolbar:Station Light}<Delay>3000</Delay>",
}


def _slot(index: int, entity_id: int, action: str = "OnOff") -> str:
    return (
        f"<Slot><Index>{index}</Index><Item />"
        '<Data xsi:type="MyObjectBuilder_ToolbarItemTerminalBlock">'
        f"<Action>{action}</Action><BlockEntityId>{entity_id}</BlockEntityId></Data></Slot>"
    )


def _group_slot(index: int, anchor: int) -> str:
    return (
        f"<Slot><Index>{index}</Index><Item />"
        '<Data xsi:type="MyObjectBuilder_ToolbarItemTerminalGroup">'
        f"<Action>OnOff</Action><BlockEntityId>{anchor}</BlockEntityId>"
        f"<GroupName>{GROUP}</GroupName></Data></Slot>"
    )


def _toolbar(kind: str, slots: str) -> str:
    return (
        f"<Toolbar><ToolbarType>{kind}</ToolbarType>"
        f'<SelectedSlot xsi:nil="true" /><Slots>{slots}</Slots></Toolbar>'
    )


def links_xml(name: str, ids: dict[str, int]) -> str:
    text = LINKS.get(name, "")
    if "{toolbar_ship}" in text:
        slots = (
            _slot(0, ids["Sub Light"])
            + _slot(1, ids["Station Light"])
            + _group_slot(2, ids["Station Cockpit"])
            + _slot(3, ids["Sub Camera"], "View")
        )
        text = text.replace("{toolbar_ship}", _toolbar("Ship", slots))
    for target, entity_id in ids.items():
        text = text.replace(
            f"{{toolbar:{target}}}", _toolbar("Character", _slot(0, entity_id))
        )
        text = text.replace(f"{{{target}}}", str(entity_id))
    return text


def blocks_xml(table: dict, ids: dict[str, int]) -> list[str]:
    return [
        world.block(
            xsi_type,
            subtype,
            cell,
            ids[name],
            f"<CustomName>{name}</CustomName>" + links_xml(name, ids),
            **orientation,
        )
        for name, (cell, xsi_type, subtype, orientation) in table.items()
    ]


def group_xml() -> str:
    cells = "".join(
        f"<Vector3I><X>{x}</X><Y>{y}</Y><Z>{z}</Z></Vector3I>"
        for x, y, z in (STATION[n][0] for n in GROUP_MEMBERS)
    )
    return (
        f"<BlockGroups><MyObjectBuilder_BlockGroup><Name>{GROUP}</Name>"
        f"<Blocks>{cells}</Blocks></MyObjectBuilder_BlockGroup></BlockGroups>"
    )


def entity_ids(base: int) -> dict[str, int]:
    return {name: base + 500 + i for i, name in enumerate([*SUBGRID, *STATION])}
