# In game tests

Pytest suite driven through the [Remote plugin](https://github.com/CometWorks/remote),
in single player and on a dedicated server. Written and run on Linux; the rig
uses the workspace's Linux scripts, so it doesn't run on Windows yet.

## What it covers

| File | What it covers |
|---|---|
| `test_projection.py` | the projections as the world loads them: every blueprint grid a subgrid, every base mapped to its top part, only the bases on the projector's grid buildable, the projector's totals over all subgrids |
| `test_weld.py` | welding every vanilla mechanical combination: each subgrid built with the blueprint's grid size and block count, each base holding a top part of the blueprint's subtype |
| `test_references.py` | toolbar items (in toolbars and waypoint actions), bound and turret cameras, tool, weapon and selection lists, and block groups of welded blocks across subgrids, and the same after a referenced block is welded again |
| `test_rebuild.py` | welding again after losing a top subgrid, a base or a block on a subgrid, and after a save and reload halfway |
| `test_load.py` | a blueprint loaded into a projector during the session, the way the blueprint screen does it |

The files in `ds/` run the same tests against a dedicated server with the MGP
server plugin; `test_rebuild_ds.py` skips the reload test.

The mechanical combinations are the game's own, from its CubeBlocks
definitions, DLC blocks left out (the clients run without Steam):

- `large`: rotor, advanced rotor and hinge with large and small heads, piston
- `small`: rotor, 3x3 and 1x1 advanced rotor, 3x3 and 1x1 hinge, piston
- `wheels-large`, `wheels-small`: every suspension (normal and short, 1x1 to
  5x5, plain and mirrored) with its wheel
- `chain`: a hinge carrying a piston carrying a rotor, and a rotor carrying two
  pistons
- `refs`: the references bench, see `refs.py`
- `group`: a hand built block reference test group, a station with a
  small grid on an advanced rotor and two rotor and hinge levels below that,
  blocks pointing up to three subgrids away. `import_group.py` copies it from
  its test world and adds what it lacked; see the script.

Known MGP defects are strict xfails, so the run stays green and a fix shows up
as an unexpected pass:
- SE1-0111: on a server's client, a remote control's camera and an event
  controller's selection on a subgrid stay stale.
- SE1-0113: flight movement toolbars aren't restored, and a group toolbar item
  welded before its group is lost.

## How a run works

Every test file is a session of its own. It starts a client, loads a fresh copy
of the test world, and stops the client at the end.

The test world is a copy of Remote's Earth test world. Each bench is a station
floating above the player: a floor, a projector and a battery. The projector
loads, with the world, a blueprint of the whole bench, mechanical parts and
subgrids included (`tests/fixtures/<bench>.sbc`). The projector is the first
block of that blueprint, so the projection lands on the bench itself.

The fixture blueprints come from the game: `fixtures.py` lets the game add the
top part of every base and writes the result out. Run it again after a game
update that may move top parts:

```bash
MGP_TASK=<task> uv run python tests/fixtures.py [bench ...]
```

No test looks at a picture. The tests read:
- MGP's own view through its PB API. A programmable block on a control station
  runs `MgpReport.cs` every 100 ticks and echoes a compact report of every
  projection, which reaches the client as the block's detailed info.
- Grids, blocks and the projector's totals through Remote.
- Object builders of welded blocks through Remote.

The tests weld with hand welder passes through Remote, with creative tools on,
in a creative world. They take blocks away with the creative remove request
(Remote's `raze` grid event), which the server carries out for a client too;
damage sent from a client of a server never lands.

## Remote ops these tests need

`test_weld.py`, `test_references.py`, `test_rebuild.py` and `test_load.py`
need three call ops
that Remote doesn't have yet: `WeldProjection`, `GetObjectBuilder` and
`LoadProjection` (proposed in the workspace at
`notes/dis-0005-remote-ops/NOTE.md`). Without them those tests skip, and
`test_projection.py` still runs. To run them, point the rig at a Remote
working copy that has the ops:

```bash
export MGP_REMOTE_REPO=~/path/to/remote
```

## Isolation

Every port, client id and folder comes from a test slot of the workspace
(`notes/parallel-test-work/NOTE.md`). `MGP_TASK` names the slot, default
`mgp-tests`. It is claimed on first use and kept until someone releases it:

```bash
~/ws/se/notes/parallel-test-work/slot.sh list
~/ws/se/notes/parallel-test-work/slot.sh release <n>
```

What a slot gives the suite:
- Client 0 plays single player. Clients 1 and 2 join the dedicated server. Each
  client has its own Pulsar folder `~/.se-test/<task>-c<i>`, created on first
  use with the workspace's `new-pulsar-instance.sh` from `~/.config/Pulsar`.
- Each client also gets a user data folder `<task>-c<i>-data` and the slot's
  Remote port and client id.
- The server runs Magnetar with its own config and data folders under
  `<task>-ds0` and the slot's ports, over DirectTransport.
- Every launch writes the Pulsar profile and plugin sources: Remote,
  DirectTransport and this working copy of MGP, compiled as dev folders.
- The clients are headless and `--no-render`.
- Every process starts under the workspace's `run-test.sh`, which waits for the
  RAM floor. Only the processes the rig started are stopped.

## Running

```bash
uv run pytest                     # single player
uv run pytest tests/ds            # dedicated server
uv run pytest tests/test_weld.py  # one file
```

A single player file takes one to five minutes, a dedicated server file about
a minute more for the server.

| Variable | Effect |
|---|---|
| `MGP_TASK` | the slot's task name |
| `MGP_SLOT` | use this slot number instead of claiming one |
| `MGP_REMOTE_REPO` | the Remote working copy, default `../remote` |
| `MGP_KEEP=1` | leave the client (and server) running after the run |
| `MGP_ATTACH=1` | reuse a client (and server) of the slot already in the test world |
| `MGP_WINDOWED=1` | a real window instead of headless |
| `MGP_EXTRA_ARGS` | more launcher options |

What MGP logged during each test goes to `tests/artifacts/<test file>.log`.
