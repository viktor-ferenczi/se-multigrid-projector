"""Object builder XML for the test worlds and blueprints.

The test world is a copy of the Remote suite's Earth world. The test stations
float above the saved character, upright against the planet's gravity, spaced
along a line. Each station carries a projector whose ProjectedGrids is a
blueprint of that same station with the blocks the test builds, so the projection
lands on the station itself: the projector is the first block of the blueprint's
first grid, and the vanilla clipboard puts that block onto the projector.
"""

from __future__ import annotations

import math
import re
import shutil
import zipfile
from pathlib import Path

import rig

TEMPLATE_ZIP = rig.REMOTE_REPO / "Worlds" / "RemoteAPITestEarthPlanet.zip"
TEMPLATE_NAME = "RemoteAPITestEarthPlanet"
ALTITUDE_M = 300.0
STATION_SPACING_M = 100.0
LARGE_M = 2.5
SMALL_M = 0.5

XSI = 'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'


def vec(tag: str, v) -> str:
    return f'<{tag} x="{v[0]}" y="{v[1]}" z="{v[2]}" />'


def block(
    xsi_type: str,
    subtype: str,
    pos,
    entity_id: int = 0,
    extra: str = "",
    forward: str = "Forward",
    up: str = "Up",
) -> str:
    entity = f"<EntityId>{entity_id}</EntityId>" if entity_id else ""
    return (
        f'<MyObjectBuilder_CubeBlock xsi:type="MyObjectBuilder_{xsi_type}">'
        f"<SubtypeName>{subtype}</SubtypeName>{entity}{vec('Min', pos)}"
        f'<BlockOrientation Forward="{forward}" Up="{up}" />'
        f'<ColorMaskHSV x="0" y="-0.8" z="0.55" />{extra}'
        "</MyObjectBuilder_CubeBlock>"
    )


def armor(pos, size: str = "Large") -> str:
    subtype = "LargeBlockArmorBlock" if size == "Large" else "SmallBlockArmorBlock"
    return block("CubeBlock", subtype, pos)


def battery(pos, entity_id: int = 0) -> str:
    return block(
        "BatteryBlock",
        "LargeBlockBatteryBlock",
        pos,
        entity_id,
        "<Enabled>true</Enabled><CurrentStoredPower>3</CurrentStoredPower>"
        "<ProducerEnabled>true</ProducerEnabled>",
    )


def projector(pos, entity_id: int, name: str, grids_xml: str = "") -> str:
    """A large projector; grids_xml is the blueprint it projects, as
    MyObjectBuilder_CubeGrid elements"""
    projected = f"<ProjectedGrids>{grids_xml}</ProjectedGrids>" if grids_xml else ""
    return block(
        "Projector",
        "LargeProjector",
        pos,
        entity_id,
        f"<CustomName>{name}</CustomName><Enabled>true</Enabled>"
        f"{projected}<KeepProjection>true</KeepProjection>"
        "<ShowOnlyBuildable>false</ShowOnlyBuildable>",
    )


def grid(
    name: str,
    entity_id: int,
    blocks: str,
    position,
    forward,
    up,
    static: bool,
    size: str = "Large",
    extra: str = "",
    tag: str = "MyObjectBuilder_EntityBase",
) -> str:
    """A grid as a sector object (tag MyObjectBuilder_EntityBase) or as a
    blueprint or projection grid (tag CubeGrid / MyObjectBuilder_CubeGrid)"""
    type_attr = (
        ' xsi:type="MyObjectBuilder_CubeGrid"'
        if tag == "MyObjectBuilder_EntityBase"
        else ""
    )
    return (
        f"<{tag}{type_attr}>"
        f"<SubtypeName /><EntityId>{entity_id}</EntityId>"
        "<PersistentFlags>CastShadows InScene</PersistentFlags>"
        "<PositionAndOrientation>"
        + vec("Position", position)
        + vec("Forward", forward)
        + vec("Up", up)
        + "</PositionAndOrientation>"
        f"<GridSizeEnum>{size}</GridSizeEnum>"
        f"<CubeBlocks>{blocks}</CubeBlocks>"
        f"<IsStatic>{'true' if static else 'false'}</IsStatic>"
        f"<IsUnsupportedStation>{'true' if static else 'false'}</IsUnsupportedStation>"
        f"{extra}<DisplayName>{name}</DisplayName>"
        "<DestructibleBlocks>true</DestructibleBlocks>"
        f"</{tag}>"
    )


# ---------------------------------------------------------------------------
# Geometry: the stations float above the saved character
# ---------------------------------------------------------------------------


def _normalize(v):
    length = math.sqrt(sum(c * c for c in v))
    return [c / length for c in v]


def _cross(a, b):
    return [
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    ]


def _template_sector() -> str:
    with zipfile.ZipFile(TEMPLATE_ZIP) as archive:
        return archive.read(f"{TEMPLATE_NAME}/SANDBOX_0_0_0_.sbs").decode("utf-8")


def frame(index: int = 0, sector_text: str | None = None):
    """Position, forward and up of station number index. Index 0 floats
    ALTITUDE_M above the saved character, the rest follow it along the right
    axis, STATION_SPACING_M apart."""
    sector_text = sector_text or _template_sector()
    start = sector_text.index(
        '<MyObjectBuilder_EntityBase xsi:type="MyObjectBuilder_Character">'
    )
    match = re.search(
        r'<Position x="([^"]+)" y="([^"]+)" z="([^"]+)"', sector_text[start:]
    )
    character = [float(c) for c in match.groups()]
    up = _normalize(character)
    right = _normalize(_cross(up, [1.0, 0.0, 0.0]))
    forward = _cross(up, right)
    position = [
        character[i] + up[i] * ALTITUDE_M + right[i] * STATION_SPACING_M * index
        for i in range(3)
    ]
    return position, forward, up


# ---------------------------------------------------------------------------
# World preparation
# ---------------------------------------------------------------------------


def prepare_world(
    world: Path,
    sector_objects: str,
    mode: str = "Survival",
    settings: dict | None = None,
    online: bool = False,
) -> Path:
    """A fresh copy of the Earth world with extra sector objects. settings
    changes session settings by element name. online makes the world public,
    for a dedicated server."""
    if world.exists():
        shutil.rmtree(world)
    world.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(TEMPLATE_ZIP) as archive:
        archive.extractall(world.parent)
    (world.parent / TEMPLATE_NAME).rename(world)

    base = {
        "GameMode": mode,
        "TrashRemovalEnabled": "false",
        "StationVoxelSupport": "true",
        "EnableCopyPaste": "true",
        "EnableIngameScripts": "true",
        "ExperimentalMode": "true",
    }
    if online:
        base["OnlineMode"] = "PUBLIC"
    for name in ("Sandbox.sbc", "Sandbox_config.sbc"):
        path = world / name
        text = path.read_text(encoding="utf-8")
        text = re.sub(
            r"<SessionName>.*?</SessionName>",
            f"<SessionName>{world.name}</SessionName>",
            text,
        )
        for key, value in {**base, **(settings or {})}.items():
            text, count = re.subn(
                rf"<{key}>[^<]*</{key}>", f"<{key}>{value}</{key}>", text
            )
            if not count:
                text = text.replace(
                    "</Settings>", f"<{key}>{value}</{key}></Settings>", 1
                )
        path.write_text(text, encoding="utf-8")

    sector = world / "SANDBOX_0_0_0_.sbs"
    text = sector.read_text(encoding="utf-8")
    text = text.replace("</SectorObjects>", sector_objects + "</SectorObjects>", 1)
    sector.write_text(text, encoding="utf-8")
    # The binary sector would win over the edited XML
    (world / "SANDBOX_0_0_0_.sbsB5").unlink(missing_ok=True)
    return world


def blueprint_xml(name: str, grids_xml: str) -> str:
    """A bp.sbc document of CubeGrid elements"""
    return (
        '<?xml version="1.0"?>'
        '<Definitions xmlns:xsd="http://www.w3.org/2001/XMLSchema" '
        f"{XSI}><ShipBlueprints>"
        '<ShipBlueprint xsi:type="MyObjectBuilder_ShipBlueprintDefinition">'
        f'<Id Type="MyObjectBuilder_ShipBlueprintDefinition" Subtype="{name}" />'
        f"<CubeGrids>{grids_xml}</CubeGrids>"
        "</ShipBlueprint></ShipBlueprints></Definitions>"
    )
