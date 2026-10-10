"""What the tests use to look at the projections and the grids"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import xml.etree.ElementTree as ET

import pytest

from se_remote import CallOp, GetOp, OpError

import rig
import stations
from fixtures import bench_ids, bench_index

STATES = {
    0: "Unknown",
    1: "NotBuildable",
    2: "Buildable",
    4: "BeingBuilt",
    8: "FullyBuilt",
    128: "Mismatch",
}


def _cell(text: str) -> tuple[int, int, int]:
    x, y, z = map(int, text.split(","))
    return x, y, z


@dataclass
class Subgrid:
    index: int
    preview: int
    built: int
    complete: bool
    # Number of blocks per state
    counts: dict[str, int] = field(default_factory=dict)
    # The blocks not fully built, by preview cell
    states: dict[tuple[int, int, int], str] = field(default_factory=dict)
    # base position -> (top subgrid, top position)
    bases: dict[tuple, tuple[int, tuple]] = field(default_factory=dict)


@dataclass
class Report:
    """What MGP's PB API says about one projection"""

    version: str = ""
    scan: int = 0
    subgrids: list[Subgrid] = field(default_factory=list)

    @classmethod
    def parse(cls, text: str) -> "Report":
        report = cls()
        for line in text.splitlines():
            # The detailed info has more than the script's echo
            kind, *values = line.split() or [""]
            if kind == "version":
                report.version = values[0]
            elif kind == "scan":
                report.scan = int(values[0])
            elif kind == "subgrid":
                index, preview, built, complete = map(int, values)
                report.subgrids.append(Subgrid(index, preview, built, complete == 1))
            elif kind == "count":
                i, state, number = map(int, values)
                report.subgrids[i].counts[STATES.get(state, str(state))] = number
            elif kind == "open":
                i, state = int(values[0]), STATES.get(int(values[1]), values[1])
                for cell in values[2:]:
                    report.subgrids[i].states[_cell(cell)] = state
            elif kind == "base":
                report.subgrids[int(values[0])].bases[_cell(values[1])] = (
                    int(values[2]),
                    _cell(values[3]),
                )
        return report

    def counts(self) -> dict[str, int]:
        result: dict[str, int] = {}
        for subgrid in self.subgrids:
            for state, number in subgrid.counts.items():
                result[state] = result.get(state, 0) + number
        return result

    @property
    def complete(self) -> bool:
        return bool(self.subgrids) and all(s.complete for s in self.subgrids)


class Game:
    def __init__(self, api):
        self.api = api

    # --- MGP's view ------------------------------------------------------------

    def _read_reports(self) -> tuple[int, dict[int, Report]]:
        grid, pos = stations.CONTROL_ID, stations.CONTROL_PB
        text = self.api.get_block(grid, pos).get("detailedInfo") or ""
        run, reports, lines = 0, {}, []
        for line in text.splitlines():
            if line.startswith("run "):
                run = int(line.split()[1])
            elif line.startswith("no api"):
                # Before the plugin registered its PB API
                return run, {}
            elif line.startswith("projector "):
                lines = []
                reports[int(line.split()[1])] = lines
            else:
                lines.append(line)
        return run, {i: Report.parse("\n".join(l)) for i, l in reports.items()}

    def report(self, projector_id: int, timeout: float = 60.0) -> Report:
        """MGP's view of one projection, from a report the script wrote after
        this call. The script runs every 100 ticks by itself; on a server its
        output comes back by replication."""
        deadline = time.monotonic() + timeout
        first = None
        while time.monotonic() < deadline:
            try:
                run, reports = self._read_reports()
            except OpError:  # not streamed to this client yet
                time.sleep(1)
                continue
            if first is None:
                first = run
            time.sleep(0.5)
            # Two runs on: the one in progress may have started before the call
            if run >= first + 2 and projector_id in reports:
                return reports[projector_id]
        detail = self.api.get_block(stations.CONTROL_ID, stations.CONTROL_PB)
        raise TimeoutError(
            f"No report from the programmable block: {detail.get('detailedInfo')}"
        )

    def wait_report(self, projector_id: int, until, timeout: float = 60.0) -> Report:
        """Reads reports until until(report) holds, returns the last one"""
        deadline = time.monotonic() + timeout
        while True:
            report = self.report(projector_id)
            if until(report) or time.monotonic() > deadline:
                return report

    def wait_grids(self, grid_ids, timeout: float = 300.0) -> None:
        """Waits until the grids reached this client, which on a server takes
        a while after the join"""
        deadline = time.monotonic() + timeout
        missing = set(grid_ids)
        while missing:
            missing -= {g["entityId"] for g in self.grids()}
            if missing and time.monotonic() > deadline:
                raise TimeoutError(f"Grids not streamed: {sorted(missing)}")
            time.sleep(2)

    # --- acting on the projections ---------------------------------------------

    def call(self, entity_id: int, method: str, args: dict | None = None):
        result = self.api.call([CallOp.fat_block_method(entity_id, method, args)])
        return result.call(0)

    def has_op(self, method: str) -> bool:
        """Whether the Remote this client compiled has a fat block call op. The
        projection ops are proposed, not merged (notes/dis-0005-remote-ops in
        the workspace); tests that need them skip without them. Asked of the
        report block, which no op here accepts but GetObjectBuilder."""
        try:
            self.call(stations.CONTROL_PB_ID, method)
            return True
        except OpError as err:
            return "is not available" not in str(err)

    def require_ops(self, *methods: str) -> None:
        missing = [m for m in methods if not self.has_op(m)]
        if missing:
            pytest.skip(f"Remote lacks the {', '.join(missing)} call op")

    def built_blocks(self, report: Report) -> dict[str, dict]:
        """The named blocks of the built grids, by name"""
        result = {}
        for subgrid in report.subgrids:
            if not subgrid.built:
                continue
            refs = [
                GetOp.block(subgrid.built, tuple(b["min"]))
                for b in self.blocks(subgrid.built)
                if b.get("customName")
            ]
            batch = self.api.batch(gets=refs)
            for i in range(len(refs)):
                block = batch.get(i)
                result[block["customName"]] = block
        return result

    def remove_block(self, grid_id: int, cell) -> None:
        """Removes a block with the creative remove request the server carries
        out, the same in single player and on a server. Needs creative tools.
        (Damage sent from a client of a server never lands.)"""
        self.api.character_grid_event(grid_id, tuple(cell), "raze")

    def weld_pass(self, projector_id: int, instant: bool = True) -> int:
        """One hand welder pass over the projection; the number of build requests"""
        return self.call(projector_id, "WeldProjection", {"instant": instant})[
            "requested"
        ]

    def weld(
        self,
        projector_id: int,
        instant: bool = True,
        timeout: float = 180.0,
        settle: float = 20.0,
    ) -> Report:
        """Welds until nothing is left to build: each pass builds what is
        buildable now, MGP's next scans open up what that made buildable, like
        the subgrid behind a head that was just created. Gives up when passes
        request nothing and the states stop changing for settle seconds.
        Returns the last report."""
        deadline = time.monotonic() + timeout
        last, since = None, time.monotonic()
        while time.monotonic() < deadline:
            requested = self.weld_pass(projector_id, instant)
            report = self.report(projector_id)
            if report.complete:
                return report
            state = [(s.built, sorted(s.states.items())) for s in report.subgrids]
            if requested or state != last:
                last, since = state, time.monotonic()
            elif time.monotonic() - since > settle:
                return report
        return self.report(projector_id)

    def object_builder(self, entity_id: int) -> ET.Element:
        """A block's object builder as this client sees it"""
        return ET.fromstring(self.call(entity_id, "GetObjectBuilder")["xml"])

    def projector_stats(self, bench: str) -> dict:
        ids = bench_ids(bench_index(bench))
        return self.api.get_block(ids["grid"], (0, 1, 0))["projector"]

    def save_and_reload(self, timeout: float = 600.0) -> None:
        """Saves the single player world and loads it again from the save"""
        self.api.save()
        deadline = time.monotonic() + timeout
        time.sleep(2)
        while self.api.get_state().get("saving"):
            if time.monotonic() > deadline:
                raise TimeoutError("The world did not finish saving")
            time.sleep(1)
        try:
            self.api.reload(save=False)
        except Exception as err:  # noqa: BLE001 -- the load outlives the HTTP timeout
            print(f"reload request returned early ({type(err).__name__})")
        rig.wait_world(self.api, timeout)
        rig.ensure_character(self.api)
        rig.focus_gameplay(self.api)

    # --- the grids -------------------------------------------------------------

    def grids(self) -> list[dict]:
        return self.api.list_grids()

    def blocks(self, grid_id: int) -> list[dict]:
        result = self.api.batch(gets=[GetOp.block_list(grid_id, limit=5000)]).get(0)
        return result["blocks"]

    def cubes(self, grid_id: int) -> dict[tuple, dict]:
        """Every block of the grid by its min cell, armor included"""
        result = self.api.batch(gets=[GetOp.cube_list(grid_id, limit=5000)]).get(0)
        cubes = result.get("cubes", result) if isinstance(result, dict) else result
        return {tuple(c["cellMin"]): c for c in cubes}
