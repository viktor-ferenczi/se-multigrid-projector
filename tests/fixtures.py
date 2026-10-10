"""Generates the bench blueprints in tests/fixtures from the game itself.

The geometry of a mechanical connection (where the head sits, in which grid)
comes from the game: the generator puts the bases of every bench into a world,
lets the game add their top parts through the blocks' own "add top part"
actions, adds the payload blocks to the saved world, and repeats for bases that
stand on subgrids. The finished benches are written as blueprints, one per
bench, with the bench's own grid first and its projector as that grid's first
block (world.py explains why).

Run it on a free client of the slot when the game changes::

    MGP_TASK=<task> uv run python tests/fixtures.py [bench ...]
"""

from __future__ import annotations

import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import rig
import refs
import world
from benches import BENCHES, Bench, Combo

FIXTURES = rig.REPO / "tests" / "fixtures"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"
XSI_TYPE = f"{{{XSI_NS}}}type"
ET.register_namespace("xsi", XSI_NS)
ET.register_namespace("xsd", "http://www.w3.org/2001/XMLSchema")

# Entity ids of bench k: BENCH_ID + k * 10000 + n
BENCH_ID = 777000600000000
# Head extents (x, y, z) in their own grid, where larger than one cell
HEAD_SIZE = {"SmallAdvancedRotor": (3, 2, 3), "MediumHingeHead": (3, 3, 3)}
# Cells a base spans from its mounting side to its top part, where more than one
BASE_LENGTH = {
    "LargePistonBase": 3,
    "SmallPistonBase": 3,
    "LargeStator": 2,
    "SmallStator": 2,
    "LargeAdvancedStator": 2,
    "SmallAdvancedStator": 2,
    "SmallAdvancedStatorSmall": 2,
    "MediumHinge": 3,
}


def bench_ids(index: int) -> dict[str, int]:
    base = BENCH_ID + index * 10000
    return {"grid": base, "projector": base + 1, "battery": base + 2}


def bench_station(bench: Bench, index: int, position, forward, up) -> str:
    """The bench as a sector object: floor, projector, battery and the bases
    standing on the floor, all without top parts"""
    ids = bench_ids(index)
    small = bench.size == "Small"
    blocks = world.block(
        "Projector",
        "SmallProjector" if small else "LargeProjector",
        (0, 1, 0),
        ids["projector"],
        f"<CustomName>Projector {bench.name}</CustomName><Enabled>true</Enabled>"
        "<KeepProjection>true</KeepProjection>",
    )
    blocks += world.block(
        "BatteryBlock",
        "SmallBlockSmallBatteryBlock" if small else "LargeBlockBatteryBlock",
        (1, 1, 0),
        ids["battery"],
        "<Enabled>true</Enabled><CurrentStoredPower>3</CurrentStoredPower>"
        "<ProducerEnabled>true</ProducerEnabled>",
    )
    blocks += "".join(world.armor(p, bench.size) for p in bench.floor + bench.armor)
    for n, combo in enumerate(bench.combos):
        blocks += base_xml(combo, combo.min, ids["grid"] + 100 + n)
    return world.grid(
        f"Bench {bench.name}",
        ids["grid"],
        blocks,
        position,
        forward,
        up,
        True,
        bench.size,
    )


def base_xml(combo: Combo, pos, entity_id: int, forward="Forward", up=None) -> str:
    """A mechanical base without its top part. Rotors and hinges are locked:
    the benches float in gravity, which would swing an unlocked head around
    before its payload is added."""
    lock = (
        "<RotorLock>true</RotorLock>"
        if combo.base_type.startswith("Motor") and "Suspension" not in combo.base_type
        else ""
    )
    return world.block(
        combo.base_type,
        combo.base,
        pos,
        entity_id,
        lock,
        forward=forward,
        up=up or combo.up,
    )


def bench_index(name: str) -> int:
    """A fixed index per bench, so each bench keeps its place and its ids when
    only some are generated again"""
    return list(BENCHES).index(name)


def world_xml(names: list[str]) -> str:
    # Station 0 of the test world is the control station
    return "".join(
        bench_station(
            BENCHES[name], bench_index(name), *world.frame(bench_index(name) + 1)
        )
        for name in names
    )


# ---------------------------------------------------------------------------
# The saved world
# ---------------------------------------------------------------------------


class Sector:
    def __init__(self, path: Path):
        self.path = path
        self.tree = ET.parse(path)
        self.objects = self.tree.getroot().find("SectorObjects")

    def grids(self):
        return [
            g for g in self.objects if g.get(XSI_TYPE) == "MyObjectBuilder_CubeGrid"
        ]

    def grid(self, entity_id: int):
        return next(g for g in self.grids() if int(g.findtext("EntityId")) == entity_id)

    def block_grid(self, entity_id: int):
        """The grid holding a block, and the block"""
        for grid in self.grids():
            for block in grid.find("CubeBlocks"):
                if int(block.findtext("EntityId") or 0) == entity_id:
                    return grid, block
        raise KeyError(entity_id)

    def save(self):
        self.tree.write(self.path, encoding="utf-8", xml_declaration=True)
        (self.path.parent / "SANDBOX_0_0_0_.sbsB5").unlink(missing_ok=True)


def block_min(block) -> tuple[int, int, int]:
    """A block's Min; the game leaves it out of the save at the origin"""
    m = block.find("Min")
    if m is None:
        return (0, 0, 0)
    return tuple(int(m.get(a)) for a in "xyz")


def _add_block(grid, xml: str) -> None:
    element = ET.fromstring(f'<root xmlns:xsi="{XSI_NS}">{xml}</root>')[0]
    grid.find("CubeBlocks").append(element)


AXES = {
    "Forward": (0, 0, -1),
    "Backward": (0, 0, 1),
    "Left": (-1, 0, 0),
    "Right": (1, 0, 0),
    "Up": (0, 1, 0),
    "Down": (0, -1, 0),
}
AXIS_NAMES = {v: k for k, v in AXES.items()}


def free_side(head: str) -> tuple[int, int, int]:
    """The side of a head that takes blocks, from the MountPoints of its
    definition: hinge heads mount on their left, the others on their top. A head
    sits in its grid in the identity orientation."""
    return AXES["Left"] if "HingeHead" in head else AXES["Up"]


def base_orientation(base: str, direction) -> tuple[str, str]:
    """Forward and Up of a base whose top part goes along direction. Hinges mount
    with their right side, the others with their bottom."""
    mount = tuple(-c for c in direction)
    forward = next(v for v in AXES.values() if v != direction and v != mount)
    if "Hinge" in base:
        up = tuple(_cross(mount, forward))
    else:
        up = tuple(direction)
    return AXIS_NAMES[forward], AXIS_NAMES[up]


def add_payload(grid, head, combo: Combo, size: str, next_id):
    """Armor on the free side of the head, children on top of it. Returns
    (child combo, entity id, min) for each child base added."""
    hmin = block_min(head)
    extent = HEAD_SIZE.get(combo.head, (1, 1, 1))
    center = [hmin[i] + (extent[i] - 1) / 2 for i in range(3)]
    direction = free_side(combo.head)
    k = next(i for i in range(3) if direction[i])
    # The cell next to the head on its free side, then a row sideways
    first = [round(c) if i != k else 0 for i, c in enumerate(center)]
    first[k] = hmin[k] + (extent[k] if direction[k] > 0 else -1)
    side = [0, 0, 0]
    side[(k + 1) % 3] = 1
    count = max(combo.payload, 2 * len(combo.children) - 1)
    for i in range(count):
        _add_block(grid, world.armor([first[a] + i * side[a] for a in range(3)], size))
    pending = []
    for j, child in enumerate(combo.children):
        # Min is the low corner, so a base reaching into the negative direction
        # starts its full length away
        step = 1 if direction[k] > 0 else -BASE_LENGTH.get(child.base, 1)
        child_min = tuple(
            first[a] + 2 * j * side[a] + (step if a == k else 0) for a in range(3)
        )
        forward, up = base_orientation(child.base, direction)
        entity_id = next_id()
        _add_block(grid, base_xml(child, child_min, entity_id, forward, up))
        pending.append((child, entity_id, child_min))
    return pending


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------


def wait_saved(remote, folder: Path, since: float, timeout: float = 300.0) -> None:
    sector = folder / "SANDBOX_0_0_0_.sbs"
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if (
            sector.exists()
            and sector.stat().st_mtime > since
            and not (folder / ".new").exists()
        ):
            time.sleep(2)
            return
        time.sleep(1)
    raise TimeoutError("The world was not saved")


def save(remote, folder: Path) -> None:
    since = time.time()
    remote.save()
    wait_saved(remote, folder, since)


def generate(names: list[str], client: rig.Client) -> None:
    folder = client.saves / "MgpFixtures"
    world.prepare_world(folder, world_xml(names), mode="Creative")
    remote = rig.wait_api(client)
    rig.load_world(remote, folder)
    rig.ensure_character(remote)
    rig.focus_gameplay(remote)

    counter = iter(range(BENCH_ID + 9000, BENCH_ID + 9999))
    # (combo, grid id, base min, base entity id, bench size)
    pending = []
    for name in names:
        bench = BENCHES[name]
        ids = bench_ids(bench_index(name))
        for n, combo in enumerate(bench.combos):
            pending.append((combo, ids["grid"], combo.min, ids["grid"] + 100 + n))

    while pending:
        for combo, grid_id, base_min, _ in pending:
            remote.apply_action(grid_id, base_min, combo.action)
        time.sleep(5)
        save(remote, folder)
        sector = Sector(folder / "SANDBOX_0_0_0_.sbs")
        following = []
        for combo, grid_id, base_min, base_id in pending:
            _, base = sector.block_grid(base_id)
            top_id = int(base.findtext("TopBlockId") or 0)
            if not top_id:
                raise RuntimeError(f"{combo.name}: {combo.action} added no top part")
            head_grid, head = sector.block_grid(top_id)
            if head.findtext("SubtypeName") != combo.head:
                raise RuntimeError(
                    f"{combo.name}: got {head.findtext('SubtypeName')}, expected {combo.head}"
                )
            size = head_grid.findtext("GridSizeEnum")
            for child, child_id, child_min in add_payload(
                head_grid, head, combo, size, lambda: next(counter)
            ):
                head_grid_id = int(head_grid.findtext("EntityId"))
                following.append((child, head_grid_id, child_min, child_id))
            # Easier to read in the blueprint
            head_grid.find("DisplayName").text = combo.name
        sector.save()
        _reload(remote)
        pending = following

    if "refs" in names:
        add_refs(Sector(folder / "SANDBOX_0_0_0_.sbs"), bench_ids(bench_index("refs")))
        _reload(remote)

    save(remote, folder)
    sector = Sector(folder / "SANDBOX_0_0_0_.sbs")
    FIXTURES.mkdir(exist_ok=True)
    for name in names:
        write_blueprint(sector, BENCHES[name], bench_index(name))


def add_refs(sector: Sector, ids: dict[str, int]) -> None:
    """The references bench's linked blocks, on the station and on the rotor's
    subgrid (refs.py)"""
    station = sector.grid(ids["grid"])
    base = next(b for b in station.find("CubeBlocks") if b.findtext("TopBlockId"))
    subgrid, _ = sector.block_grid(int(base.findtext("TopBlockId")))
    names = refs.entity_ids(ids["grid"])
    for xml in refs.blocks_xml(refs.STATION, names):
        _add_block(station, xml)
    for xml in refs.blocks_xml(refs.SUBGRID, names):
        _add_block(subgrid, xml)
    for old in station.findall("BlockGroups"):
        station.remove(old)
    station.append(ET.fromstring(refs.group_xml()))
    sector.save()


def _reload(remote) -> None:
    try:
        remote.reload(save=False)
    except Exception as err:  # noqa: BLE001 -- the load outlives the HTTP timeout
        print(f"reload request returned early ({type(err).__name__})")
    rig.wait_world(remote)
    rig.ensure_character(remote)
    rig.focus_gameplay(remote)


def connected_grids(sector: Sector, grid) -> list:
    """The grid and every grid hanging on its mechanical bases, depth first"""
    result = [grid]
    for block in grid.find("CubeBlocks"):
        top_id = int(block.findtext("TopBlockId") or 0)
        if top_id:
            top_grid, _ = sector.block_grid(top_id)
            result += connected_grids(sector, top_grid)
    return result


def write_blueprint(sector: Sector, bench: Bench, index: int) -> Path:
    ids = bench_ids(index)
    grids = []
    for grid in connected_grids(sector, sector.grid(ids["grid"])):
        element = ET.fromstring(ET.tostring(grid))
        for node in element.iter():
            if node.text is not None and not node.text.strip():
                node.text = None
            node.tail = None
        element.tag = "CubeGrid"
        element.attrib.pop(XSI_TYPE, None)
        blocks = element.find("CubeBlocks")
        projector = next(
            (b for b in blocks if int(b.findtext("EntityId") or 0) == ids["projector"]),
            None,
        )
        if projector is not None:
            # The projector first: the clipboard puts the first block onto it
            blocks.remove(projector)
            blocks.insert(0, projector)
            for tag in ("ProjectedGrids", "ProjectedGrid"):
                for child in projector.findall(tag):
                    projector.remove(child)
        grids.append(ET.tostring(element, encoding="unicode"))
    text = world.blueprint_xml(f"Bench {bench.name}", "".join(grids))
    # ET writes the xsi prefix declaration on each element it was parsed from
    path = FIXTURES / f"{bench.name}.sbc"
    path.write_text(text, encoding="utf-8")
    print(f"{path}: {len(grids)} grids")
    return path


if __name__ == "__main__":
    names = sys.argv[1:] or [n for n, b in BENCHES.items() if b.combos]
    client = rig.Client(0)
    if not rig.running_pid(client):
        rig.launch(client)
    generate(names, client)
