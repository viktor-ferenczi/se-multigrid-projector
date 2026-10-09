"""Isolated headless game clients and dedicated servers for the MGP tests.

Every port, client id and folder comes from a test slot of the workspace
(notes/parallel-test-work/NOTE.md), so the suite runs next to other tests
without sharing anything with them. MGP_TASK names the slot; it is claimed on
first use and the claim is kept until someone releases it::

    notes/parallel-test-work/slot.sh claim mgp-tests     # what the rig does
    notes/parallel-test-work/slot.sh release <n>         # when you are done

Client i gets its own Pulsar folder ~/.se-test/<task>-c<i>, created on first use
with notes/pulsar-dev-instances/new-pulsar-instance.sh, its own game user data
folder <task>-c<i>-data and Remote port REMOTE_PORT_BASE + i. Every launch writes
the client's profile and plugin sources: Remote, DirectTransport and this working
copy of MGP, compiled as dev folders. Every process starts under run-test.sh, which
waits for the RAM floor and holds the shared test lock.
"""

from __future__ import annotations

import os
import re
import shutil
import signal
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

HOME = Path.home()
REPO = Path(__file__).resolve().parent.parent
WORKSPACE = Path(os.environ.get("MGP_WORKSPACE", REPO.parents[2]))
PARALLEL = WORKSPACE / "notes" / "parallel-test-work"
# The Remote plugin, compiled by the clients from this working copy
REMOTE_REPO = Path(os.environ.get("MGP_REMOTE_REPO", REPO.parent / "remote"))
DIRECT_TRANSPORT_REPO = Path(
    os.environ.get("MGP_DIRECT_TRANSPORT_REPO", WORKSPACE / "se1" / "direct-transport")
)
PULSAR_TEMPLATE = Path(os.environ.get("MGP_PULSAR_TEMPLATE", HOME / ".config/Pulsar"))

sys.path.insert(0, str(REMOTE_REPO / "skills" / "se-remote"))

from se_remote import RemoteAPI  # noqa: E402

TASK = os.environ.get("MGP_TASK", "mgp-tests")
TEST_ROOT = HOME / ".se-test"
ARTIFACTS = REPO / "tests" / "artifacts"
WINDOWED = os.environ.get("MGP_WINDOWED") == "1"

MGP_CLIENT_ID = "viktor-ferenczi/se-multigrid-projector"
MGP_SERVER_ID = "B91FD7B3-E1AC-4B57-8765-C677A7AC1F5F"

# Measured RSS of a settled client (notes/parallel-test-work/NOTE.md)
CLIENT_GIB = 3.7 if not WINDOWED else 5.5


def _claim_slot() -> dict[str, int]:
    """The slot of MGP_TASK: its number and the bases of its resources"""
    slot = (
        os.environ.get("MGP_SLOT")
        or subprocess.run(
            [str(PARALLEL / "slot.sh"), "claim", TASK],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    )
    text = subprocess.run(
        [str(PARALLEL / "slot.sh"), "env", slot],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    values = {k: int(v) for k, v in re.findall(r"(\w+_BASE)=(\d+)", text)}
    values["SLOT"] = int(slot)
    return values


SLOT = _claim_slot()


class Client:
    """Client i of the slot: Pulsar folder, game user data folder, Remote port
    and the id it plays with"""

    def __init__(self, index: int):
        self.index = index
        self.pulsar = TEST_ROOT / f"{TASK}-c{index}"
        self.launcher = self.pulsar / "Interim.bin"
        self.appdata = TEST_ROOT / f"{TASK}-c{index}-data"
        self.port = SLOT["REMOTE_PORT_BASE"] + index
        self.steam_id = SLOT["CLIENT_ID_BASE"] + index
        self.name = f"MgpTester{index}"
        self.pid_file = self.appdata / "game.pid"
        self.launch_log = self.appdata / "launch.log"
        self.log = self.appdata / "SpaceEngineers.log"
        self.saves = self.appdata / "Saves" / str(self.steam_id)

    def args(self) -> list[str]:
        args = [
            "-multiInstance",
            "-lazySteam",
            "-noprompt",
            "-noupdate",
            "-nosplash",
            "-stablelogs",
            "-sources",
            "--no-steam",
            "--client-id",
            str(self.steam_id),
            "--client-name",
            self.name,
            "-appdata",
            str(self.appdata),
            "--quality",
            "minimal",
            "--resolution",
            "640x480",
            "--no-audio",
        ]
        if not WINDOWED:
            # No test looks at a frame
            args += ["--headless", "--no-render"]
        return args + os.environ.get("MGP_EXTRA_ARGS", "").split()


def profile_xml(dev_folders) -> str:
    folders = "".join(
        f"<LocalFolderConfig><Id>{i}</Id><DebugBuild>true</DebugBuild></LocalFolderConfig>"
        for i in dev_folders
    )
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<Profile xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
        'xmlns:xsd="http://www.w3.org/2001/XMLSchema">'
        f"<Name>Current</Name><GitHub /><DevFolder>{folders}</DevFolder>"
        "<Local /><Mods /></Profile>\n"
    )


def register_source(sources: Path, name: str, folder: Path, file: str) -> None:
    """Points the loader's dev folder source of this name at a folder"""
    tree = ET.parse(sources)
    local = tree.getroot().find("LocalPluginSources")
    if local is None:
        local = ET.SubElement(tree.getroot(), "LocalPluginSources")
    for plugin in local.findall("LocalPlugin"):
        if plugin.findtext("Name") == name:
            local.remove(plugin)
    plugin = ET.SubElement(local, "LocalPlugin")
    for tag, value in (
        ("Name", name),
        ("Folder", str(folder)),
        ("File", file),
        ("Enabled", "true"),
    ):
        ET.SubElement(plugin, tag).text = value
    tree.write(sources, encoding="utf-8", xml_declaration=True)


def ensure_pulsar(client: Client) -> None:
    if client.launcher.exists():
        return
    subprocess.run(
        [
            str(WORKSPACE / "notes/pulsar-dev-instances/new-pulsar-instance.sh"),
            str(client.pulsar),
            str(PULSAR_TEMPLATE),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )


def write_client_configs(client: Client, mgp: bool = True) -> None:
    legacy = client.pulsar / "Legacy"
    dev_folders = ["remote", "direct-transport"] + ([MGP_CLIENT_ID] if mgp else [])
    (legacy / "Profiles" / "Current.xml").write_text(
        profile_xml(dev_folders), encoding="utf-8"
    )
    sources = legacy / "Sources" / "sources.xml"
    register_source(sources, "remote", REMOTE_REPO, "Remote.xml")
    register_source(
        sources, "direct-transport", DIRECT_TRANSPORT_REPO, "DirectTransportClient.xml"
    )
    register_source(
        sources, "se-multigrid-projector", REPO, "MultigridProjectorClient.xml"
    )

    appdata = client.appdata
    appdata.mkdir(parents=True, exist_ok=True)
    (appdata / "Remote.cfg").write_text(
        f"""<?xml version="1.0" encoding="utf-8"?>
<PluginConfig xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <Enabled>true</Enabled>
  <ListenIP>127.0.0.1</ListenIP>
  <ListenPort>{client.port}</ListenPort>
  <AdminPassword>SpaceEngineers</AdminPassword>
  <GridGetRateLimit>1000</GridGetRateLimit>
  <GridGetBurstSize>2000</GridGetBurstSize>
  <GridSetRateLimit>200</GridSetRateLimit>
  <GridSetBurstSize>400</GridSetBurstSize>
  <GridMaxGetOpsPerRequest>500</GridMaxGetOpsPerRequest>
  <GridMaxSetOpsPerRequest>200</GridMaxSetOpsPerRequest>
</PluginConfig>
""",
        encoding="utf-8",
    )

    # The Earth world is experimental; a fresh user data folder says it is not
    game_cfg = appdata / "SpaceEngineers.cfg"
    if not game_cfg.exists():
        shutil.copy(HOME / ".config/SpaceEngineers/SpaceEngineers.cfg", game_cfg)
    text = game_cfg.read_text(encoding="utf-8")
    text = re.sub(
        r"(<Key>ExperimentalMode</Key>\s*<Value>\s*<Value[^>]*>)\w+(</Value>)",
        r"\1True\2",
        text,
    )
    game_cfg.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# Processes. Each runs in a session of its own under run-test.sh (flock), so the
# whole process group is ours to stop.
# ---------------------------------------------------------------------------


def _alive(pid_file: Path, marker: str) -> int | None:
    try:
        pid = int(pid_file.read_text().strip())
        cmdline = Path(f"/proc/{pid}/cmdline").read_bytes()
    except (OSError, ValueError):
        return None
    return pid if marker.encode() in cmdline else None


def start_process(
    command: list[str], need_gib: float, cwd: Path, log: Path, pid_file: Path, env=None
) -> int:
    with open(log, "w") as out:
        process = subprocess.Popen(
            [str(PARALLEL / "run-test.sh"), str(need_gib), "--", *command],
            cwd=cwd,
            env={**os.environ, **(env or {})},
            stdout=out,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
    pid_file.write_text(str(process.pid))
    return process.pid


def _group_alive(pgid: int) -> bool:
    try:
        os.killpg(pgid, 0)
        return True
    except ProcessLookupError:
        return False


def stop_process(pid_file: Path, marker: str, timeout: float = 60.0) -> None:
    """SIGTERM to the process group we started, SIGKILL after the timeout.
    Waits for the whole group: the flock wrapper exits at once, the game only
    after it saved."""
    pid = _alive(pid_file, marker)
    if pid is None:
        pid_file.unlink(missing_ok=True)
        return
    os.killpg(pid, signal.SIGTERM)
    deadline = time.monotonic() + timeout
    while _group_alive(pid):
        if time.monotonic() > deadline:
            os.killpg(pid, signal.SIGKILL)
            break
        time.sleep(1)
    pid_file.unlink(missing_ok=True)


def running_pid(client: Client) -> int | None:
    return _alive(client.pid_file, str(client.launcher))


def launch(client: Client, extra_args=(), mgp: bool = True) -> None:
    if running_pid(client):
        raise RuntimeError(f"Client {client.index} is already running")
    ensure_pulsar(client)
    write_client_configs(client, mgp)
    client.log.unlink(missing_ok=True)
    env = {} if WINDOWED else {"PULSAR_NO_RENDER": "true"}
    start_process(
        [str(client.launcher), *client.args(), *extra_args],
        CLIENT_GIB,
        client.pulsar,
        client.launch_log,
        client.pid_file,
        env,
    )


def stop(client: Client) -> None:
    stop_process(client.pid_file, str(client.launcher))


def api(client: Client) -> RemoteAPI:
    return RemoteAPI(
        f"http://127.0.0.1:{client.port}", username="admin", password="SpaceEngineers"
    )


def wait_api(client: Client, timeout: float = 2400.0) -> RemoteAPI:
    """Waits for the Remote API. The RAM guard may hold the launch for a while,
    so this waits as long as the process lives."""
    remote = api(client)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not running_pid(client):
            raise RuntimeError(f"Client {client.index} exited, see {client.launch_log}")
        try:
            remote.ping()
            return remote
        except Exception:  # noqa: BLE001 -- not listening yet
            time.sleep(3)
    raise TimeoutError(f"Client {client.index} has no Remote API")


# ---------------------------------------------------------------------------
# Session handling
# ---------------------------------------------------------------------------


def load_world(remote: RemoteAPI, world: Path, timeout: float = 600.0) -> None:
    try:
        remote.load(str(world))
    except Exception as err:  # noqa: BLE001 -- the load outlives the HTTP timeout
        print(f"load request returned early ({type(err).__name__})")
    wait_world(remote, timeout)


def _message_boxes(remote: RemoteAPI) -> list[dict]:
    return [
        s for s in remote.list_screens() if s.get("type") == "MyGuiScreenMessageBox"
    ]


def wait_world(remote: RemoteAPI, timeout: float = 600.0) -> None:
    """Waits until the session is ready, clicking OK on any message box on the
    way (the "needs XML" box of a bare XML sector retries the load with XML)"""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        time.sleep(1)
        try:
            boxes = _message_boxes(remote)
            for box in boxes:
                remote.control_click(text="OK", screen=box["index"])
            if not boxes and remote.get_state().get("ready"):
                return
        except Exception:  # noqa: BLE001 -- the API times out while a world loads
            pass
    raise TimeoutError("The world did not become ready")


def ensure_character(remote: RemoteAPI, timeout: float = 300.0) -> dict:
    """Respawns, at the first spawn point, until there is a live character"""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            character = remote.get_character()
            if character.get("state") not in (None, "dead"):
                return character
        except Exception:  # noqa: BLE001 -- 503 without a character
            pass
        try:
            screens = remote.list_screens()
            medical = next(
                (i for i, s in enumerate(screens) if "Medical" in s.get("type", "")),
                None,
            )
            if medical is not None:
                for button in ("Join", "Respawn"):
                    try:
                        remote.control_click(text=button, screen=medical)
                        break
                    except Exception:  # noqa: BLE001 -- the other page of the screen
                        continue
        except Exception:  # noqa: BLE001 -- slow while the base streams in
            pass
        time.sleep(3)
    raise TimeoutError("No live character")


def focus_gameplay(remote: RemoteAPI, timeout: float = 30.0) -> None:
    """Closes the welcome screen and anything else above the gameplay screen.
    The loading screen is left to finish by itself."""
    keep = ("MyGuiScreenGamePlay", "MyGuiScreenHudSpace")

    def kinds():
        return [s.get("type") for s in remote.list_screens()]

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        screens = kinds()
        extra = [i for i, kind in enumerate(screens) if kind not in keep]
        if not extra:
            return
        time.sleep(0.3)
        if "MyGuiScreenLoading" not in screens and kinds() == screens:
            remote.close_screen(extra[-1])
            time.sleep(0.3)
    raise TimeoutError("Could not get back to the gameplay screen")


def plugin_loaded(log: Path, plugin: str = "MultigridProjector") -> bool:
    return log.exists() and plugin in log.read_text(errors="replace")
