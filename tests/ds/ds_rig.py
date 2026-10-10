"""Dedicated server rig of the MGP tests: an isolated Magnetar server with
DirectTransport and the MGP server plugin compiled from this working copy, and
clients of the slot that join it.

Server 0 of the slot: Magnetar config folder ~/.se-test/<task>-ds0/magnetar, DS
data folder ~/.se-test/<task>-ds0/data, ServerPort and SteamPort from the slot.
The clients are clients 1 and 2 of the slot (rig.Client), so a dedicated server
run can share the slot with the single player tests.

Also usable from the command line while iterating::

    MGP_TASK=<task> uv run python tests/ds/ds_rig.py start [--no-mgp-server]
    MGP_TASK=<task> uv run python tests/ds/ds_rig.py stop
"""

from __future__ import annotations

import os
import re
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import rig  # noqa: E402
import stations  # noqa: E402

HOME = Path.home()
ROOT = rig.TEST_ROOT / f"{rig.TASK}-ds0"
MAGNETAR = Path(os.environ.get("MGP_MAGNETAR_DIR", HOME / ".config/Magnetar"))
MAGNETAR_TEMPLATE = MAGNETAR / "Magnetar"
DS64 = Path(
    os.environ.get(
        "MGP_DS64",
        HOME
        / ".steam/debian-installation/steamapps/common"
        / "SpaceEngineersDedicatedServer/DedicatedServer64",
    )
)
DS_CONFIG_TEMPLATE = (
    HOME / ".config/SpaceEngineersDedicated/SpaceEngineers-Dedicated.cfg"
)
SERVER_PORT = rig.SLOT["DS_SERVER_PORT_BASE"]
STEAM_PORT = rig.SLOT["DS_STEAM_PORT_BASE"]
SERVER_CONFIG = ROOT / "magnetar"
SERVER_DATA = ROOT / "data"
SERVER_PID = ROOT / "server.pid"
SERVER_LOG = ROOT / "server.log"
GAME_LOG_GLOB = "SpaceEngineersDedicated*.log"
WORLD_NAME = "MgpTestServer"
WORLD = SERVER_DATA / "Saves" / WORLD_NAME
# Not measured yet, the figure of notes/parallel-test-work/NOTE.md
SERVER_GIB = 4.0

CLIENT = rig.Client(1)
CLIENT2 = rig.Client(2)


def prepare_server(benches=None, mgp: bool = True, settings=None, extras=None) -> None:
    """A fresh copy of the test world and the server's configs. Without mgp the
    server runs DirectTransport only, as a vanilla server would."""
    stations.prepare(WORLD, benches, settings=settings, online=True, extras=extras)

    if not (SERVER_CONFIG / "Sources").exists():
        SERVER_CONFIG.mkdir(parents=True, exist_ok=True)
        shutil.copytree(MAGNETAR_TEMPLATE / "Sources", SERVER_CONFIG / "Sources")
        shutil.copy(MAGNETAR_TEMPLATE / "config.xml", SERVER_CONFIG / "config.xml")
    sources = SERVER_CONFIG / "Sources" / "sources.xml"
    rig.register_source(
        sources, "se-multigrid-projector", rig.REPO, "MultigridProjectorServer.xml"
    )
    rig.register_source(
        sources,
        "direct-transport",
        rig.DIRECT_TRANSPORT_REPO,
        "DirectTransportServer.xml",
    )
    (SERVER_CONFIG / "Profiles").mkdir(exist_ok=True)
    plugins = ["direct-transport"] + ([rig.MGP_SERVER_ID] if mgp else [])
    (SERVER_CONFIG / "Profiles" / "Current.xml").write_text(
        rig.profile_xml(plugins), encoding="utf-8"
    )

    text = DS_CONFIG_TEMPLATE.read_text(encoding="utf-8")
    admins = "".join(
        f"<unsignedLong>{c.steam_id}</unsignedLong>" for c in (CLIENT, CLIENT2)
    )
    for tag, value in {
        "IP": "127.0.0.1",
        "ServerPort": SERVER_PORT,
        "SteamPort": STEAM_PORT,
        "Administrators": admins,
        "ServerName": f"MGP Test Server {rig.TASK}",
        "WorldName": WORLD_NAME,
        "PauseGameWhenEmpty": "false",
        "AutoRestartEnabled": "false",
        "IgnoreLastSession": "true",
        "RemoteApiEnabled": "false",
        "LoadWorld": WORLD,
    }.items():
        text, count = re.subn(
            rf"<{tag}>.*?</{tag}>|<{tag} />",
            f"<{tag}>{value}</{tag}>",
            text,
            flags=re.S,
        )
        assert count == 1, tag
    SERVER_DATA.mkdir(parents=True, exist_ok=True)
    (SERVER_DATA / "SpaceEngineers-Dedicated.cfg").write_text(text, encoding="utf-8")


def server_pid() -> int | None:
    return rig._alive(SERVER_PID, str(SERVER_CONFIG))


def start_server(timeout: float = 2400.0) -> None:
    """Starts the server and waits for its world. The RAM guard may hold the
    start for a while."""
    if server_pid():
        raise RuntimeError(f"The test server is already running, pid {server_pid()}")
    rig.start_process(
        [
            str(MAGNETAR / "MagnetarInterim.bin"),
            "-multiInstance",
            "-stableLogs",
            "-noimplicitmod",
            "-consent",
            "deny",
            "-config",
            str(SERVER_CONFIG),
            "-ds64",
            str(DS64),
            "-path",
            str(SERVER_DATA),
        ],
        SERVER_GIB,
        MAGNETAR,
        SERVER_LOG,
        SERVER_PID,
        {"SE_DIRECT_TRANSPORT": "1"},
    )
    deadline = time.monotonic() + timeout
    while "Game ready" not in SERVER_LOG.read_text(errors="replace"):
        if server_pid() is None:
            raise RuntimeError(f"The server exited, see {SERVER_LOG}")
        if time.monotonic() > deadline:
            raise TimeoutError(f"The server did not get ready, see {SERVER_LOG}")
        time.sleep(2)


def stop_server() -> None:
    """SIGTERM makes Magnetar save the world and quit"""
    rig.stop_process(SERVER_PID, str(SERVER_CONFIG), timeout=120)


def server_log_text() -> str:
    logs = sorted(SERVER_DATA.glob(GAME_LOG_GLOB))
    return logs[-1].read_text(errors="replace") if logs else ""


def start_client(client: rig.Client = CLIENT, mgp: bool = True):
    """Starts a client, which joins on its own, and returns its API once the
    character stands in the world"""
    rig.launch(client, ["--connect", f"127.0.0.1:{SERVER_PORT}"], mgp=mgp)
    remote = rig.wait_api(client)
    rig.wait_world(remote, 900)
    rig.ensure_character(remote)
    rig.focus_gameplay(remote)
    return remote


def stop_clients() -> None:
    rig.stop(CLIENT)
    rig.stop(CLIENT2)


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    if command == "start":
        stop_clients()
        stop_server()
        prepare_server(mgp="--no-mgp-server" not in sys.argv)
        start_server()
        start_client()
        print(f"Joined. Remote API on port {CLIENT.port}, server log {SERVER_LOG}")
    elif command == "stop":
        stop_clients()
        stop_server()
    else:
        sys.exit(__doc__)
