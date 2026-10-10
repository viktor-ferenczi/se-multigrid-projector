"""MGP's PB API while the projection changes, with and without block
highlighting (GitHub issue #114: a script reading the API crashes on
inconsistent data once the projector highlights blocks).

A second programmable block on the bench runs ApiConsistency.cs, which reads
the whole API on every tick and counts what doesn't hold together. The test
welds the large bench, then keeps taking subgrids away and welding them again
for a while, first with highlighting off, then on. Highlighting makes MGP
rescan the projection five times a second, with Havok intersection checks.

Single player only: highlighting is a client feature, while on a server the
script runs against the server's projection.
"""

from __future__ import annotations

import time
from pathlib import Path
from xml.sax.saxutils import escape

import pytest

import blueprint
import world
from fixtures import bench_ids, bench_index
from se_remote import SetOp
from stations import PB_OWNER

BENCH = "large"
BENCHES = [BENCH]
WORLD_SETTINGS = {"GameMode": "Creative"}
IDS = bench_ids(bench_index(BENCH))
PROJECTOR = IDS["projector"]
STATION = IDS["grid"]
PROJECTOR_CELL = (0, 1, 0)
CHECKER = (3, 1, 0)
CHECKER_ID = STATION + 900
CHURN_S = 60.0
SCRIPT = (Path(__file__).parent / "ApiConsistency.cs").read_text(encoding="utf-8")


def checker_xml() -> str:
    program = SCRIPT.replace("/*PROJECTOR*/", str(PROJECTOR))
    return world.block(
        "MyProgrammableBlock",
        "LargeProgrammableBlock",
        CHECKER,
        CHECKER_ID,
        "<CustomName>MGP API Check</CustomName><Enabled>true</Enabled>"
        f"<Owner>{PB_OWNER}</Owner><BuiltBy>{PB_OWNER}</BuiltBy>"
        f"<ShareMode>All</ShareMode><Program>{escape(program)}</Program>",
    )


STATION_EXTRAS = {BENCH: (checker_xml(), "")}


def checker(game) -> tuple[int, int, dict[str, tuple[int, str]]]:
    """What the script echoed: ticks checked, the scan number and the
    failures by kind (count, first example)"""
    text = game.api.get_block(STATION, CHECKER).get("detailedInfo") or ""
    ticks = scan = 0
    fails = {}
    for line in text.splitlines():
        kind, _, rest = line.partition(" ")
        if kind == "run":
            ticks = int(rest)
        elif kind == "scan":
            scan = int(rest)
        elif kind == "fail":
            name, number, example = (rest.split(" ", 2) + [""])[:3]
            fails[name] = (int(number), example)
    return ticks, scan, fails


@pytest.fixture(scope="module")
def welded(game):
    game.require_ops("WeldProjection")
    game.api.set_admin_flag("creativeTools", True)
    report = game.weld(PROJECTOR)
    assert report.complete, {s.index: s.states for s in report.subgrids if s.states}
    return report


def churn(game, seconds: float) -> int:
    """Takes the subgrids away one by one and welds each again, until the
    time is up. Returns the number of rebuilds."""
    deadline = time.monotonic() + seconds
    connections = blueprint.connections(BENCH)
    rebuilds = 0
    while time.monotonic() < deadline:
        connection = connections[rebuilds % len(connections)]
        built = game.report(PROJECTOR).subgrids[connection.top_grid].built
        game.api.batch(sets=[SetOp.grid_close(built)]).set(0)
        game.wait_report(
            PROJECTOR, lambda r: not r.subgrids[connection.top_grid].complete
        )
        report = game.weld(PROJECTOR)
        assert report.complete, {s.index: s.states for s in report.subgrids if s.states}
        rebuilds += 1
    return rebuilds


@pytest.mark.parametrize("highlight", [False, True], ids=["plain", "highlighted"])
def test_api_holds_together_while_the_projection_changes(game, welded, highlight):
    action = "BlockHighlightEnable" if highlight else "BlockHighlightDisable"
    game.api.apply_action(STATION, PROJECTOR_CELL, action)
    ticks, scan, before = checker(game)
    assert ticks, game.api.get_block(STATION, CHECKER).get("detailedInfo")
    assert churn(game, CHURN_S)
    ticks_after, scan_after, after = checker(game)
    assert ticks_after > ticks and scan_after > scan
    new = {
        kind: (count - before.get(kind, (0, ""))[0], example)
        for kind, (count, example) in after.items()
        if count > before.get(kind, (0, ""))[0]
    }
    assert not new
