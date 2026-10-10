"""The projections as the world loads them, before anything is welded: MGP has
to find every subgrid of the blueprint, map each mechanical base to its top
part, and offer exactly the bases standing on the projector's grid for
welding."""

from __future__ import annotations

from collections import Counter

import pytest

import blueprint
import stations
from benches import BENCHES
from fixtures import bench_ids, bench_index


def projector(bench: str) -> int:
    return bench_ids(bench_index(bench))["projector"]


@pytest.fixture(scope="module")
def reports(game):
    return {
        name: game.wait_report(projector(name), lambda r: r.scan > 0)
        for name in BENCHES
    }


@pytest.mark.parametrize("bench", list(BENCHES))
def test_every_blueprint_grid_is_a_subgrid(reports, bench):
    report = reports[bench]
    assert report.scan > 0
    assert len(report.subgrids) == len(blueprint.grid_sizes(bench))
    for subgrid in report.subgrids:
        assert sum(subgrid.counts.values()) == blueprint.grid_block_count(
            bench, subgrid.index
        )


@pytest.mark.parametrize("bench", list(BENCHES))
def test_bases_map_to_their_top_parts(reports, bench):
    found = Counter(
        (subgrid.index, top)
        for subgrid in reports[bench].subgrids
        for top, _ in subgrid.bases.values()
    )
    expected = Counter((c.base_grid, c.top_grid) for c in blueprint.connections(bench))
    assert found == expected


@pytest.mark.parametrize("bench", list(BENCHES))
def test_only_the_projector_grid_is_built(reports, bench):
    report = reports[bench]
    main, *subgrids = report.subgrids
    assert main.built == bench_ids(bench_index(bench))["grid"]
    assert not main.complete
    for subgrid in subgrids:
        assert subgrid.built == 0
        assert not subgrid.complete
        assert set(subgrid.counts) == {"NotBuildable"}


@pytest.mark.parametrize("bench", list(BENCHES))
def test_the_station_blocks_to_weld_are_open(reports, bench):
    """Everything the test world left off the bench's station waits for
    welding. The bases on the floor are buildable; a block mounted on another
    block to weld (the group bench has one) is not, yet."""
    main = reports[bench].subgrids[0]
    ids = bench_ids(bench_index(bench))
    to_weld = [
        b
        for b in stations.blueprint_grids(bench)[0].find("CubeBlocks")
        if not stations.is_infrastructure(b, ids)
    ]
    assert len(main.states) == len(to_weld)
    assert set(main.states.values()) <= {"Buildable", "NotBuildable"}
    for base in main.bases:
        assert main.states[base] == "Buildable"


@pytest.mark.parametrize("bench", list(BENCHES))
def test_projector_counts_every_subgrid(game, reports, bench):
    """The projector's own statistics, which MGP replaces with the totals over
    all subgrids"""
    stats = game.projector_stats(bench)
    counts = reports[bench].counts()
    assert stats["isProjecting"]
    assert stats["totalBlocks"] == sum(counts.values())
    assert stats["remainingBlocks"] == sum(counts.values()) - counts["FullyBuilt"]
    assert stats["buildableBlocksCount"] == counts["Buildable"]
