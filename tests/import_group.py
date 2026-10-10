"""Makes the "group" bench fixture from a hand built mechanical group.

A hand built block reference test world has a static station carrying a
small grid on an advanced rotor, two small rotors on that, a small hinge on
each and a hinge head grid on each hinge. Blocks point across all of them:
cockpit toolbar slots, event controllers, turret controllers aiming cameras and
guns two subgrids down, a remote control with its camera and waypoints, the
offensive combat block's weapons and the path recorder's waypoint actions.

This copies the group into tests/fixtures/group.sbc, in the same form as the
generated fixtures, and adds what it lacks:
- the two rotating lights, which are DLC blocks, are front lights;
- the station's projector stands in the identity orientation, so the projection
  lands on the station like on the other benches;
- a timer, a sensor, a flight movement block and a defensive combat block on
  the station, the timer's and the sensor's toolbars pointing at blocks on the
  subgrids. A flight movement block saves no toolbar, its object builder has
  no field for one;
- a toolbar on the small grid's button panel pointing back at the station;
- a block group on the station and one on the small grid, with group items on
  the cockpit's and the small grid remote control's toolbars. The small button
  panel has a single button, so its toolbar has no room for one.

Run it again only if the source world changes::

    uv run python tests/import_group.py <world folder> [station entity id]
"""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import refs
import world
from fixtures import FIXTURES, XSI_NS, XSI_TYPE, bench_ids, bench_index, block_min

BENCH = "group"
STATION_ID = 112045162718899088
ON_BACK = refs.ON_BACK

# Blocks added to the station: name -> (cell, type, subtype, orientation, the
# name of the block its toolbar's first slot switches)
ADDED = {
    "Group Timer": (
        (6, 1, 0),
        "TimerBlock",
        "TimerBlockLarge",
        {},
        "Gatling Gun Solar 1a",
    ),
    "Group Sensor": (
        (6, 1, 1),
        "SensorBlock",
        "LargeBlockSensor",
        ON_BACK,
        "Camera Solar 2",
    ),
    "Group Flight": (
        (6, 1, 2),
        "FlightMovementBlock",
        "LargeFlightMovement",
        {},
        None,
    ),
    "Group Defensive": (
        (6, 1, 3),
        "DefensiveCombatBlock",
        "LargeDefensiveCombat",
        {},
        None,
    ),
}
# DLC blocks of the source world and their stand-ins: the test clients play
# without Steam, so they own no DLC and the server refuses to weld these. Same
# type, size and mounting side.
DLC_SWAPS = {
    "RotatingLightLarge": "LargeBlockFrontLight",
    "RotatingLightSmall": "SmallBlockFrontLight",
}
STATION_GROUP = ("LG Group", ["Rotating Light LG", "Cockpit LG"])
SMALL_GROUP = ("SG Group", ["Rotating Light SG", "Camera RC SG"])
UNNAMED = {
    "MyObjectBuilder_ButtonPanel": "Button Panel SG",
    "MyObjectBuilder_OffensiveCombatBlock": "Offensive Combat SG",
    "MyObjectBuilder_PathRecorderBlock": "Path Recorder SG",
}


def blocks_by_type(grid, kind: str):
    return next(b for b in grid.find("CubeBlocks") if b.get(XSI_TYPE) == kind)


def _vector(element) -> list[float]:
    return [float(element.get(a)) for a in "xyz"]


def _cross(a, b):
    return [
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    ]


def _basis(placement):
    forward = _vector(placement.find("Forward"))
    up = _vector(placement.find("Up"))
    return _cross(forward, up), up, forward


def _local(v, basis):
    return [sum(v[i] * axis[i] for i in range(3)) for axis in basis]


def _world(v, basis):
    return [sum(v[k] * basis[k][i] for k in range(3)) for i in range(3)]


def _set(element, tag, v):
    node = element.find(tag)
    for axis, value in zip("xyz", v):
        node.set(axis, repr(value))


def move(grids, station, position, forward, up):
    """Moves the grids so the station stands at position, forward, up; the
    others keep their place relative to it"""
    old = station.find("PositionAndOrientation")
    origin = _vector(old.find("Position"))
    old_basis = _basis(old)
    new_basis = (_cross(forward, up), up, forward)
    for grid in grids:
        placement = grid.find("PositionAndOrientation")
        offset = [p - o for p, o in zip(_vector(placement.find("Position")), origin)]
        new_position = [
            p + d
            for p, d in zip(position, _world(_local(offset, old_basis), new_basis))
        ]
        new_forward = _world(
            _local(_vector(placement.find("Forward")), old_basis), new_basis
        )
        new_up = _world(_local(_vector(placement.find("Up")), old_basis), new_basis)
        _set(placement, "Position", new_position)
        _set(placement, "Forward", new_forward)
        _set(placement, "Up", new_up)
        # Derived from Forward and Up, would contradict them
        for child in placement.findall("Orientation"):
            placement.remove(child)


def group_grids(sector: ET.Element, station_id: int) -> list[ET.Element]:
    grids = [
        g
        for g in sector.find("SectorObjects")
        if g.get(XSI_TYPE) == "MyObjectBuilder_CubeGrid"
    ]
    owner = {
        int(b.findtext("EntityId") or 0): g for g in grids for b in g.find("CubeBlocks")
    }

    def walk(grid):
        result = [grid]
        for block in grid.find("CubeBlocks"):
            top = int(block.findtext("TopBlockId") or 0)
            if top:
                result += walk(owner[top])
        return result

    return walk(next(g for g in grids if int(g.findtext("EntityId")) == station_id))


def _by_name(grids) -> dict[str, tuple[ET.Element, ET.Element]]:
    return {
        b.findtext("CustomName"): (g, b)
        for g in grids
        for b in g.find("CubeBlocks")
        if b.findtext("CustomName")
    }


def _element(xml: str) -> ET.Element:
    return ET.fromstring(f'<root xmlns:xsi="{XSI_NS}">{xml}</root>')[0]


def _group(name: str, members, blocks) -> ET.Element:
    cells = "".join(
        "<Vector3I><X>{}</X><Y>{}</Y><Z>{}</Z></Vector3I>".format(
            *block_min(blocks[m][1])
        )
        for m in members
    )
    return _element(
        f"<MyObjectBuilder_BlockGroup><Name>{name}</Name><Blocks>{cells}</Blocks>"
        "</MyObjectBuilder_BlockGroup>"
    )


def _add_group(grid, group: ET.Element) -> None:
    groups = grid.find("BlockGroups")
    if groups is None:
        groups = ET.SubElement(grid, "BlockGroups")
    groups.append(group)


def _group_slot(index: int, anchor: int, group: str) -> ET.Element:
    return _element(
        f"<Slot><Index>{index}</Index><Item />"
        '<Data xsi:type="MyObjectBuilder_ToolbarItemTerminalGroup">'
        f"<Action>OnOff</Action><BlockEntityId>{anchor}</BlockEntityId>"
        f"<GroupName>{group}</GroupName></Data></Slot>"
    )


def extend(grids) -> None:
    station = grids[0]
    small = grids[1]
    blocks = _by_name(grids)
    ids = {n: int(b.findtext("EntityId")) for n, (_, b) in blocks.items()}

    # The projector upright in its cell, no projection settings of its own
    projector = blocks["Repair Projector"][1]
    projector.find("BlockOrientation").attrib.update(Forward="Forward", Up="Up")
    for tag in ("ProjectedGrids", "ProjectionOffset", "ProjectionRotation"):
        for child in projector.findall(tag):
            projector.remove(child)
    projector.find("Enabled").text = "true"

    for grid in grids:
        for block in grid.find("CubeBlocks"):
            subtype = block.find("SubtypeName")
            if subtype is not None and subtype.text in DLC_SWAPS:
                subtype.text = DLC_SWAPS[subtype.text]

    # Nobody owns anything: the source world's players don't exist in the test
    # world, and a welded block gets its owner from the welder anyway
    for grid in grids:
        for block in grid.find("CubeBlocks"):
            for tag in ("Owner", "ShareMode"):
                for child in block.findall(tag):
                    block.remove(child)

    next_id = max(ids.values()) + 1
    for name, (cell, xsi_type, subtype, orientation, target) in ADDED.items():
        toolbar = (
            refs._toolbar("Character", refs._slot(0, ids[target])) if target else ""
        )
        station.find("CubeBlocks").append(
            _element(
                world.block(
                    xsi_type,
                    subtype,
                    cell,
                    next_id,
                    f"<CustomName>{name}</CustomName>{toolbar}",
                    **orientation,
                )
            )
        )
        next_id += 1

    _add_group(station, _group(*STATION_GROUP, blocks))
    _add_group(small, _group(*SMALL_GROUP, blocks))

    cockpit = blocks["Cockpit LG"][1]
    cockpit.find("Toolbar").find("Slots").append(
        _group_slot(2, ids["Cockpit LG"], STATION_GROUP[0])
    )

    # Names for the blocks the source world left unnamed, by which the tests
    # find them
    for kind, name in UNNAMED.items():
        block = next(b for b in small.find("CubeBlocks") if b.get(XSI_TYPE) == kind)
        if block.find("CustomName") is None:
            ET.SubElement(block, "CustomName").text = name
    panel = blocks_by_type(small, "MyObjectBuilder_ButtonPanel")
    for old in panel.findall("Toolbar"):
        panel.remove(old)
    panel.append(
        _element(refs._toolbar("Character", refs._slot(0, ids["Rotating Light LG"])))
    )

    remote = blocks["Remote Control SG"][1]
    remote.find("Toolbar").find("Slots").append(
        _group_slot(0, ids["Remote Control SG"], SMALL_GROUP[0])
    )


def renumber(grids, station) -> None:
    """The bench's ids for the station and its projector, everywhere they occur"""
    ids = bench_ids(bench_index(BENCH))
    projector = next(
        b for b in station.find("CubeBlocks") if b.get(XSI_TYPE).endswith("_Projector")
    )
    swaps = {
        station.findtext("EntityId"): str(ids["grid"]),
        projector.findtext("EntityId"): str(ids["projector"]),
    }
    for grid in grids:
        for node in grid.iter():
            if node.text in swaps:
                node.text = swaps[node.text]
    blocks = station.find("CubeBlocks")
    blocks.remove(projector)
    blocks.insert(0, projector)


def main(folder: Path, station_id: int = STATION_ID) -> Path:
    sector = ET.parse(folder / "SANDBOX_0_0_0_.sbs").getroot()
    grids = [ET.fromstring(ET.tostring(g)) for g in group_grids(sector, station_id)]
    extend(grids)
    renumber(grids, grids[0])
    move(grids, grids[0], *world.frame(bench_index(BENCH) + 1))
    texts = []
    for grid in grids:
        for node in grid.iter():
            if node.text is not None and not node.text.strip():
                node.text = None
            node.tail = None
        grid.tag = "CubeGrid"
        grid.attrib.pop(XSI_TYPE, None)
        texts.append(ET.tostring(grid, encoding="unicode"))
    path = FIXTURES / f"{BENCH}.sbc"
    path.write_text(
        world.blueprint_xml("Bench group", "".join(texts)), encoding="utf-8"
    )
    print(f"{path}: {len(grids)} grids")
    return path


if __name__ == "__main__":
    main(Path(sys.argv[1]), *(int(a) for a in sys.argv[2:]))
