"""Toolbar slots and block references of welded blocks (MGP's ReferenceFixer).

Two benches link blocks across subgrids. The references bench (refs.py) does
it in every way the fixer handles, on one rotor's subgrid. The group bench
(import_group.py) is a hand built mechanical group whose blocks point up to
three subgrids away. After a projection is welded, each welded block has to
point at the welded counterparts of the blocks its blueprint pointed at, as this
client sees them, and again after a block it points at is welded anew."""

from __future__ import annotations

import pytest

import blueprint
import import_group
import refs
from fixtures import XSI_TYPE, bench_ids, bench_index
from se_remote import GetOp

BENCHES = ["refs", "group"]
WORLD_SETTINGS = {"GameMode": "Creative"}
# Per bench, a block on a subgrid that others point at, to destroy and weld again
REWELD = {"refs": "Sub Light", "group": "Gatling Gun Solar 1a"}
GROUPS = {
    "refs": [(refs.GROUP, refs.GROUP_MEMBERS, 0)],
    "group": [(*import_group.STATION_GROUP, 0), (*import_group.SMALL_GROUP, 1)],
}

# On a dedicated server the server restores these right (its save says so), but
# the client keeps the projection's id for the target on the subgrid: the
# remote control's bound camera and the event controller's selected blocks
# (SE1-0111).
CLIENT_GAPS = {("refs", "Station Remote"), ("refs", "Station Events")}

# Not restored anywhere (SE1-0113): MGP reads no toolbar from a flight movement
# block's object builder, and a group item whose group isn't welded yet when
# its block is gets lost.
GAPS = {("group", "Group Flight"), ("group", "Button Panel SG")}


def mark_gaps(request, game, bench: str, block: str) -> None:
    if (bench, block) in GAPS:
        reason = "MGP does not restore this reference (SE1-0113)"
    elif (bench, block) in CLIENT_GAPS and game.api.get_state().get(
        "multiplayer"
    ) != "offline":
        reason = "MGP does not restore this reference on clients of a server (SE1-0111)"
    else:
        return
    request.applymarker(pytest.mark.xfail(strict=True, reason=reason))


REFERENCE_TAGS = ("BindedCamera", "CameraId")
NOT_REFERENCES = {"Toolbar", "SlotsGamepad"}


def links(builder, names: dict[int, str]) -> dict:
    """Every reference of an object builder, ids replaced by block names. An id
    of no block of the blueprint (or of the welded result) is "?", so a stale id
    never matches a name.

    Covers toolbar items wherever they are (toolbars, waypoint actions), the
    single id references in REFERENCE_TAGS and every list of ids (tools,
    selected blocks, weapons)."""

    def name(text) -> str:
        return names.get(int(text), "?")

    result: dict = {}
    items = []
    for node in builder.iter():
        kind = node.get(XSI_TYPE) or ""
        if kind.startswith("MyObjectBuilder_ToolbarItemTerminal"):
            items.append(
                (
                    kind,
                    node.findtext("Action"),
                    name(node.findtext("BlockEntityId")),
                    node.findtext("GroupName") or "",
                )
            )
        elif node.tag in REFERENCE_TAGS and node.text:
            result[node.tag] = name(node.text)
        elif len(node) and all(child.tag == "long" for child in node):
            result.setdefault(node.tag, []).extend(name(c.text) for c in node)
    result = {k: sorted(v) if isinstance(v, list) else v for k, v in result.items()}
    if items:
        result["toolbar items"] = sorted(items)
    return result


def linked_blocks() -> list:
    """(bench, block name) of every named block with a reference"""
    return [
        pytest.param(bench, name, id=f"{bench}-{name}")
        for bench in BENCHES
        for name in sorted(set(blueprint.names_by_id(bench).values()))
        if links(blueprint.builder(bench, name), blueprint.names_by_id(bench))
    ]


LINKED = linked_blocks()


def projector(bench: str) -> int:
    return bench_ids(bench_index(bench))["projector"]


def compare(game, built: dict, bench: str, block: str) -> None:
    expected = links(blueprint.builder(bench, block), blueprint.names_by_id(bench))
    actual = links(
        game.object_builder(built[bench][block]["entityId"]),
        {b["entityId"]: n for n, b in built[bench].items()},
    )
    assert actual == expected


@pytest.fixture(scope="module")
def welded(game):
    game.require_ops("WeldProjection", "GetObjectBuilder")
    game.api.set_admin_flag("creativeTools", True)
    reports = {b: game.weld(projector(b)) for b in BENCHES}
    for bench, report in reports.items():
        assert report.complete, (
            bench,
            {s.index: s.states for s in report.subgrids if s.states},
        )
    return reports


@pytest.fixture(scope="module")
def built(game, welded):
    return {b: game.built_blocks(r) for b, r in welded.items()}


@pytest.mark.parametrize("bench, block", LINKED)
def test_references_point_at_the_welded_blocks(request, game, built, bench, block):
    mark_gaps(request, game, bench, block)
    compare(game, built, bench, block)


@pytest.mark.parametrize(
    "bench, group, members, subgrid",
    [pytest.param(b, *g, id=f"{b}-{g[0]}") for b in BENCHES for g in GROUPS[b]],
)
def test_block_group_is_restored(game, welded, built, bench, group, members, subgrid):
    grid = welded[bench].subgrids[subgrid].built
    groups = game.api.batch(gets=[GetOp.block_groups(grid)]).get(0)
    groups = groups.get("groups", groups) if isinstance(groups, dict) else groups
    found = next(g for g in groups if g["name"] == group)
    names = {b["entityId"]: n for n, b in built[bench].items()}
    assert {names.get(i, i) for i in found["blocks"]} == set(members)


@pytest.fixture(scope="module")
def rebuilt(game, welded, built):
    """A block others point at destroyed and welded again, per bench. MGP welds
    a block with the projection's id for it when no entity holds that id, so the
    new block usually gets the old one's id; the references must hold either
    way."""
    result = {}
    for bench, name in REWELD.items():
        block = built[bench][name]
        game.remove_block(block["gridId"], block["min"])
        game.wait_report(projector(bench), lambda r: not r.complete)
        report = game.weld(projector(bench))
        assert report.complete, report.counts()
        result[bench] = game.built_blocks(report)
    return result


@pytest.mark.parametrize("bench, block", LINKED)
def test_references_follow_a_rewelded_block(request, game, rebuilt, bench, block):
    mark_gaps(request, game, bench, block)
    compare(game, rebuilt, bench, block)
