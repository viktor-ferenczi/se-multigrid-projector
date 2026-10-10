"""A blueprint loaded into a projector during the session, the way the blueprint
screen hands it over when it closes. That path goes through MGP's patch of
MyProjectorBase.InitFromObjectBuilder, which prepares and remaps the blueprint
on the client before the projector sends it to the server."""

from __future__ import annotations

import blueprint
from fixtures import FIXTURES, bench_ids, bench_index

BENCH = "chain"
BENCHES = [BENCH]
WORLD_SETTINGS = {"GameMode": "Creative"}
PROJECTOR = bench_ids(bench_index(BENCH))["projector"]


def test_loaded_blueprint_is_projected_and_welded(game):
    game.require_ops("LoadProjection", "WeldProjection")
    before = game.report(PROJECTOR)
    xml = (FIXTURES / f"{BENCH}.sbc").read_text(encoding="utf-8")
    assert game.call(PROJECTOR, "LoadProjection", {"xml": xml})["grids"] == len(
        blueprint.grid_sizes(BENCH)
    )
    # A new blueprint restarts the scan count
    report = game.wait_report(
        PROJECTOR,
        lambda r: r.subgrids and r.subgrids[0].preview != before.subgrids[0].preview,
    )
    assert len(report.subgrids) == len(blueprint.grid_sizes(BENCH))
    game.api.set_admin_flag("creativeTools", True)
    report = game.weld(PROJECTOR)
    assert report.complete, {s.index: s.states for s in report.subgrids if s.states}
