"""The checks of the BuildInternal RPC (SE-1753)

Space Engineers 1.211.018 made the server check a client's BuildInternal RPC:
the builder must be the sender's own controlled character, builtBy the sender's
identity, the block within the world's block limits and, in survival without an
instant creative tools build, the builder must hold the block's first
component. MGP replaces BuildInternal, so it has to make the same checks.

The rpc-probe client plugin next to this file adds a projector action that sends
the vanilla RPC with the arguments the test writes into the projector's custom
data. The world is survival with the hinge (block pair LargeHinge) limited to
none, and the client is an admin with creative tools on, so an instant build
needs no components. Each test asks for a different base of the large bench and
counts the bases of that subtype on the station afterwards.

A request the server makes itself for a block other than a ship welder is not
checked for components (SE-1769): ToolCore's welders take the first component
out of the tool and then call projector.Build with the tool as the builder. The
tool-probe server plugin makes such a request.
"""

from __future__ import annotations

import re
import time
from pathlib import Path

import compat
import ds_rig
from fixtures import bench_ids, bench_index

BENCHES = ["large"]
WORLD_SETTINGS = {"GameMode": "Survival", "EnableResearch": "false"}

PROBE = Path(__file__).parent / "rpc-probe"
CLIENT_PLUGINS = [("rpc-probe", "rpc-probe", PROBE, "RpcProbe.xml")]
SERVER_PLUGINS = [compat.TOOL_PROBE]
SEND = "MgpTestBuildRpc"

STATION = bench_ids(bench_index("large"))["grid"]
PROJECTOR_CELL = (0, 1, 0)
LIMITED = "LargeHinge"


def limit_hinges(world_folder: Path) -> None:
    """EDIT_WORLD: nobody may build a hinge"""
    item = f"<item><Key>{LIMITED}</Key><Value>0</Value></item>"
    for name in ("Sandbox.sbc", "Sandbox_config.sbc"):
        path = world_folder / name
        text, count = re.subn(
            r"<BlockTypeLimits>\s*<dictionary\s*/>\s*</BlockTypeLimits>",
            f"<BlockTypeLimits><dictionary>{item}</dictionary></BlockTypeLimits>",
            path.read_text(encoding="utf-8"),
        )
        assert count == 1, f"No empty BlockTypeLimits in {name}"
        path.write_text(text, encoding="utf-8")


EDIT_WORLD = limit_hinges


def client_lines(text: str) -> list[str]:
    log = ds_rig.CLIENT.log.read_text(errors="replace")
    return [line for line in log.splitlines() if text in line]


def count(game, subtype: str) -> int:
    return sum(1 for c in game.cubes(STATION).values() if c.get("subtypeId") == subtype)


def send(game, subtype: str, builder="self", built_by="self", instant=True) -> int:
    """Sends the RPC for a projected block of subtype, returns how many more of
    them the station has afterwards"""
    before = count(game, subtype)
    sent = len(client_lines("RpcProbe: sent"))
    game.api.set_custom_data(
        STATION,
        PROJECTOR_CELL,
        f"subtype={subtype}\nbuilder={builder}\nbuiltBy={built_by}\ninstant={instant}",
    )
    game.api.apply_action(STATION, PROJECTOR_CELL, SEND)
    deadline = time.monotonic() + 30
    while len(client_lines("RpcProbe: sent")) == sent:
        assert time.monotonic() < deadline, client_lines("RpcProbe:")[-3:]
        time.sleep(0.5)
    # A built block reaches the client within a second or two
    deadline = time.monotonic() + 10
    while count(game, subtype) == before and time.monotonic() < deadline:
        time.sleep(1)
    return count(game, subtype) - before


def test_probe_is_ready(game):
    deadline = time.monotonic() + 60
    while not client_lines("RpcProbe: action added"):
        assert (
            time.monotonic() < deadline
        ), "The rpc-probe plugin did not add its action"
        time.sleep(1)
    game.api.set_admin_flag("creativeTools", True)


def test_honest_rpc_builds(game):
    assert send(game, "LargeStator") == 1


def test_builder_not_the_senders_character_is_refused(game):
    assert send(game, "LargeAdvancedStator", builder="projector") == 0


def test_built_by_not_the_sender_is_refused(game):
    assert send(game, "LargePistonBase", built_by="other") == 0


def test_world_block_limit_is_refused(game):
    assert send(game, LIMITED) == 0


def test_survival_without_components_is_refused(game):
    # Not instant: the character has none of the stator's steel plates
    assert send(game, "LargeStator", instant=False) == 0


def test_server_side_build_by_a_block_builds(game):
    # Not instant, and the projector holds no steel plates: built like a ToolCore welder's
    before = count(game, "LargeAdvancedStator")
    asked = server_lines("ToolProbe: asked")
    game.api.set_custom_data(STATION, PROJECTOR_CELL, "serverBuild=LargeAdvancedStator")
    assert wait_server_lines(
        "ToolProbe: asked", asked + 1
    ), "the tool-probe made no request"
    deadline = time.monotonic() + 10
    while count(game, "LargeAdvancedStator") == before and time.monotonic() < deadline:
        time.sleep(1)
    assert count(game, "LargeAdvancedStator") - before == 1


def test_refusals_are_logged(game):
    for reason in (
        "is not the sender's controlled character",
        "is not the sender's identity",
        "world block limits",
        "holds none of its first component",
    ):
        assert wait_server(reason), reason


def wait_server(text: str, timeout: float = 60) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if text in ds_rig.server_log_text():
            return True
        time.sleep(1)
    return False


def server_lines(text: str) -> int:
    return ds_rig.server_log_text().count(text)


def wait_server_lines(text: str, lines: int, timeout: float = 30) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if server_lines(text) >= lines:
            return True
        time.sleep(0.5)
    return False
