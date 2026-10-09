"""Session setup of the dedicated server tests: a fresh server per test file,
and client 1 of the slot joining it as an administrator.

The test files here run the single player test files' tests again, imported
from the parent folder, against the server. A test file sets MGP_SERVER = False
for a server without the MGP server plugin, and BENCHES and WORLD_SETTINGS as in
single player.

MGP_ATTACH=1 reuses a running server and client, MGP_KEEP=1 leaves them running.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ds_rig  # noqa: E402
import rig  # noqa: E402
from benches import BENCHES  # noqa: E402
from fixtures import bench_ids, bench_index  # noqa: E402
from harness import Game  # noqa: E402
import stations  # noqa: E402

ATTACH = os.environ.get("MGP_ATTACH") == "1"
KEEP = os.environ.get("MGP_KEEP") == "1"


@pytest.fixture(scope="module")
def game(request):
    benches = getattr(request.module, "BENCHES", list(BENCHES))
    attach = ATTACH and ds_rig.server_pid() and rig.running_pid(ds_rig.CLIENT)
    try:
        if attach:
            remote = rig.api(ds_rig.CLIENT)
        else:
            ds_rig.stop_clients()
            ds_rig.stop_server()
            ds_rig.prepare_server(
                benches,
                mgp=getattr(request.module, "MGP_SERVER", True),
                settings=getattr(request.module, "WORLD_SETTINGS", None),
            )
            ds_rig.start_server()
            remote = ds_rig.start_client()
        game = Game(remote)
        game.wait_grids(
            [stations.CONTROL_ID] + [bench_ids(bench_index(b))["grid"] for b in benches]
        )
        yield game
    finally:
        if not KEEP:
            ds_rig.stop_clients()
            ds_rig.stop_server()
