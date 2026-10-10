"""The test world: a control station and the benches, ready to weld.

Each bench comes from its fixture blueprint (fixtures.py). In the test world the
bench keeps only its floor, projector and battery; everything else is in the
projection, which the projector loads with the world. The control station
carries the programmable block running MgpReport.cs, which reads MGP's PB API
for any projector by its entity id.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape
from pathlib import Path

import world
from benches import BENCHES
from fixtures import FIXTURES, XSI_NS, XSI_TYPE, bench_ids, bench_index, block_min

CONTROL_ID = 777000500000000
CONTROL_PB_ID = CONTROL_ID + 1
CONTROL_PB = (1, 1, 1)
# The template world's player. An unowned programmable block runs nothing, and a
# change of owner needs a recompile, which a client cannot ask for through Remote
# (its SetProgram does not reach the server). Shared with all, anyone may run it.
PB_OWNER = 144115188075855883
PB_SCRIPT = (Path(__file__).parent / "MgpReport.cs").read_text(encoding="utf-8")


def control_station(names) -> str:
    position, forward, up = world.frame(0)
    floor = [(x, 0, z) for x in range(3) for z in range(3)]
    blocks = "".join(world.armor(p) for p in floor)
    blocks += world.battery((0, 1, 0), CONTROL_ID + 2)
    # Turned so its keyboard faces the floor
    blocks += world.block(
        "MyProgrammableBlock",
        "LargeProgrammableBlock",
        CONTROL_PB,
        CONTROL_PB_ID,
        "<CustomName>MGP Report</CustomName><Enabled>true</Enabled>"
        f"<Owner>{PB_OWNER}</Owner><BuiltBy>{PB_OWNER}</BuiltBy><ShareMode>All</ShareMode>"
        f"<Program>{escape(report_script(names))}</Program>",
        forward="Backward",
    )
    return world.grid("MGP Control", CONTROL_ID, blocks, position, forward, up, True)


def report_script(names) -> str:
    ids = ", ".join(str(bench_ids(bench_index(n))["projector"]) for n in names)
    return PB_SCRIPT.replace("/*PROJECTORS*/", ids)


def blueprint_grids(name: str) -> list[ET.Element]:
    root = ET.parse(FIXTURES / f"{name}.sbc").getroot()
    return list(root.iter("CubeGrid"))


def is_infrastructure(block, ids) -> bool:
    """What a bench keeps in the test world: its projector, its batteries and
    the armor floor at y <= 0. Everything else is welded from the projection."""
    kind = block.get(XSI_TYPE)
    if int(block.findtext("EntityId") or 0) == ids["projector"]:
        return True
    if kind == "MyObjectBuilder_BatteryBlock":
        return True
    return kind == "MyObjectBuilder_CubeBlock" and block_min(block)[1] <= 0


def bench_station(name: str, projected: bool = True, extra: str = "") -> str:
    """The bench as a sector object, its projector loaded with the bench's
    blueprint (or empty). extra is more blocks for the station, as
    MyObjectBuilder_CubeBlock elements."""
    ids = bench_ids(bench_index(name))
    grids = blueprint_grids(name)
    station = ET.fromstring(ET.tostring(grids[0]))
    station.tag = "MyObjectBuilder_EntityBase"
    station.set(XSI_TYPE, "MyObjectBuilder_CubeGrid")
    blocks = station.find("CubeBlocks")
    for block in list(blocks):
        if not is_infrastructure(block, ids):
            blocks.remove(block)
    if projected:
        projector = next(
            b for b in blocks if int(b.findtext("EntityId")) == ids["projector"]
        )
        container = ET.SubElement(projector, "ProjectedGrids")
        for grid in grids:
            copy = ET.fromstring(ET.tostring(grid))
            copy.tag = "MyObjectBuilder_CubeGrid"
            container.append(copy)
    if extra:
        root = ET.fromstring(f'<root xmlns:xsi="{XSI_NS}">{extra}</root>')
        blocks.extend(root)
    return ET.tostring(station, encoding="unicode")


def sector_objects(names=None, projected: bool = True, extras=None) -> str:
    """extras gives a test file's own blocks per bench: bench name ->
    (blocks for the station, more sector objects), see survival.py"""
    names = names or list(BENCHES)
    extras = extras or {}
    objects = control_station(names)
    for name in names:
        blocks, more = extras.get(name, ("", ""))
        objects += bench_station(name, projected, blocks) + more
    return objects


def prepare(
    folder: Path, names=None, mode="Survival", settings=None, online=False, extras=None
):
    objects = sector_objects(names, extras=extras)
    world.prepare_world(folder, objects, mode, settings, online)
    return folder
