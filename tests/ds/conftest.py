"""Session setup of the dedicated server tests: a fresh server per test file,
and client 1 of the slot joining it as an administrator.

The test files here run the single player test files' tests again, imported
from the parent folder, against the server. A test file sets MGP_SERVER = False
for a server without the MGP server plugin, and BENCHES, WORLD_SETTINGS,
STATION_EXTRAS, SECTOR_OBJECTS and REPORT_PROJECTORS as in single player.
MGP_SERVER_CONFIG sets server plugin options and EDIT_WORLD is called with the
world folder before the server starts. MGP_CLIENT = False joins with a vanilla
client. MGP_SERVER_REPO and MGP_CLIENT_REPO point a side at another MGP working
copy, SERVER_PLUGINS adds server plugins (see ds_rig.prepare_server),
SERVER_ENV sets server environment variables and ADMINS = False joins as a
plain player.

MGP_ATTACH=1 reuses a running server and client, MGP_KEEP=1 leaves them running.
"""

from __future__ import annotations

import os
import sys
import time
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


def wait_full_mode(timeout: float = 60.0) -> None:
    """Until the client got the server's presence packet: welding before it
    would go the client-only way"""
    deadline = time.monotonic() + timeout
    while "full feature set" not in ds_rig.CLIENT.log.read_text(errors="replace"):
        if time.monotonic() > deadline:
            raise TimeoutError("The client did not switch to full mode")
        time.sleep(0.5)


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
                extras=getattr(request.module, "STATION_EXTRAS", None),
                report=getattr(request.module, "REPORT_PROJECTORS", ()),
                # The presence packet 1 s after the join, not 5 s
                plugin_config={
                    "PresenceDelaySeconds": 1,
                    **getattr(request.module, "MGP_SERVER_CONFIG", {}),
                },
                others=getattr(request.module, "SECTOR_OBJECTS", ""),
                mgp_repo=getattr(request.module, "MGP_SERVER_REPO", rig.REPO),
                plugins=getattr(request.module, "SERVER_PLUGINS", ()),
                admins=getattr(request.module, "ADMINS", True),
            )
            edit_world = getattr(request.module, "EDIT_WORLD", None)
            if edit_world:
                edit_world(ds_rig.WORLD)
            ds_rig.start_server(env=getattr(request.module, "SERVER_ENV", None))
            remote = ds_rig.start_client(
                mgp=getattr(request.module, "MGP_CLIENT", True),
                mgp_repo=getattr(request.module, "MGP_CLIENT_REPO", rig.REPO),
            )
            if (
                getattr(request.module, "MGP_SERVER", True)
                and getattr(request.module, "MGP_CLIENT", True)
                and getattr(request.module, "MGP_CLIENT_REPO", rig.REPO) == rig.REPO
                and getattr(request.module, "MGP_SERVER_REPO", rig.REPO) == rig.REPO
                and not getattr(request.module, "SERVER_ENV", None)
            ):
                wait_full_mode()
        game = Game(remote)
        game.wait_grids(
            [stations.CONTROL_ID] + [bench_ids(bench_index(b))["grid"] for b in benches]
        )
        yield game
    finally:
        # The server's game log of this file, for the record
        rig.ARTIFACTS.mkdir(parents=True, exist_ok=True)
        (rig.ARTIFACTS / f"{request.module.__name__}.server.log").write_text(
            ds_rig.server_log_text(), encoding="utf-8"
        )
        if not KEEP:
            ds_rig.stop_clients()
            ds_rig.stop_server()
