# API Examples (Mod & PB)

These two projects demonstrate how to consume the Multigrid Projector public API from
two different integration surfaces: a Space Engineers **mod** (using `MultigridProjectorModAgent`)
and a **Programmable Block script** (using an embedded `MultigridProjectorProgrammableBlockAgent`
shim). They serve as copy-paste starting points for developers and as smoke tests for the API
contract. See [Public-API.md](./Public-API.md) for the full API contract and member reference,
and [../API.md](../API.md) for the user-facing feature summary.

---

## Files

| File | Lines | Purpose |
|---|---|---|
| [Script.cs](../../IngameApiTest/Script/Script.cs) | 360 | PB script — embeds the agent shim and exercises every API call |
| [MultigridProjectorModApiTest.cs](../../ModApiTest/Mod/Data/Scripts/MultigridProjector/ModApiTest/MultigridProjectorModApiTest.cs) | 183 | Mod game-logic component — attaches to every projector, logs API output |
| [ModApiTest/Mod/Data/Scripts/MultigridProjector/Api/README.md](../../ModApiTest/Mod/Data/Scripts/MultigridProjector/Api/README.md) | 9 | Instructions for copying the five API source files into a new mod |
| [ModApiTest/Deploy.bat](../../ModApiTest/Deploy.bat) | — | Deploys the mod folder and copies API source files from `MultigridProjectorApi/Api/` |
| [IngameApiTest/Deploy.bat](../../IngameApiTest/Deploy.bat) | — | Deploys the `Script/` folder to the local ingame-scripts directory |
| [ModApiTest/steam_description.txt](../../ModApiTest/steam_description.txt) | — | Steam Workshop description for the mod example |
| [IngameApiTest/steam_description.txt](../../IngameApiTest/steam_description.txt) | — | Steam Workshop description for the PB script example |

Both projects also contain a standard `Properties/AssemblyInfo.cs` (boilerplate, not documented further)
and a `modinfo.sbmi` / `metadata.mod` pair that carries the Steam Workshop ID.

---

## ModApiTest (Mod API example)

### What it does

`MultigridProjectorModApiTest` is a `MyGameLogicComponent` that the game attaches to **every
projector block** in the world. On each attached projector it:

1. Constructs a `MultigridProjectorModAgent`; falls back to `MultigridProjectorModShim` if the
   plugin is absent.
2. Logs the plugin/shim version to chat once (static flag `mgpVersionLogged`).
3. Every 100 simulation frames (`UpdateBeforeSimulation100`) detects when the active blueprint
   changes by comparing the `gridBuilders` list reference returned by `GetOriginalGridBuilders`.
4. On a blueprint change, calls `GatherBlueprintDetails` which logs a full dump of every subgrid
   (preview grid, built grid, base/top connections, state hash, completion flag, all block states,
   and the YAML representation) to `MyLog.Default` and a chat message.
5. Between blueprint changes, calls `LogAndChatSubgridStateChanges` to detect per-subgrid hash
   changes and announce them to chat.

### How the agent is obtained

```csharp
var agent = new MultigridProjectorModAgent();
mgp = agent.Available ? (IMultigridProjectorApi) agent : new MultigridProjectorModShim(projector);
```

`MultigridProjectorModAgent` communicates with the plugin through the game's `IMyModContext` /
`MyAPIGateway` mod-API bridge. `MultigridProjectorModShim` is a no-op fallback that returns safe
defaults so the mod compiles and runs even without the plugin installed.

### API calls demonstrated

| Call | Where used |
|---|---|
| `GetOriginalGridBuilders(projectorId)` | `UpdateBeforeSimulation100` — change detection |
| `GetScanNumber(projectorId)` | `GatherBlueprintDetails`, `LogAndChatSubgridStateChanges` |
| `GetSubgridCount(projectorId)` | `GatherBlueprintDetails`, `LogAndChatSubgridStateChanges` |
| `GetPreviewGrid(projectorId, subgridIndex)` | `GatherBlueprintDetails` |
| `GetBuiltGrid(projectorId, subgridIndex)` | `GatherBlueprintDetails` |
| `GetBaseConnections(projectorId, subgridIndex)` | `GatherBlueprintDetails` |
| `GetTopConnections(projectorId, subgridIndex)` | `GatherBlueprintDetails` |
| `GetStateHash(projectorId, subgridIndex)` | `GatherBlueprintDetails`, `LogAndChatSubgridStateChanges` |
| `IsSubgridComplete(projectorId, subgridIndex)` | `GatherBlueprintDetails` |
| `GetBlockStates(dict, projectorId, subgridIndex, box, mask)` | `GatherBlueprintDetails` |
| `GetBlockState(projectorId, subgridIndex, position)` | `GatherBlueprintDetails` (first block) |
| `GetYaml(projectorId)` | `GatherBlueprintDetails` |

### Member table — `MultigridProjectorModApiTest`

| Member | Kind | Description |
|---|---|---|
| `mgpVersionLogged` | `static bool` | Guards one-time version announcement to chat |
| `projector` | `IMyProjector` | The projector block this component is attached to |
| `mgp` | `IMultigridProjectorApi` | Plugin agent or fallback shim |
| `gridBuilders` | `List<MyObjectBuilder_CubeGrid>` | Most-recently-seen blueprint builder list; used for change detection |
| `subgridStateHashes` | `List<ulong>` | Per-subgrid state hashes from last check |
| `Init(objectBuilder)` | override method | Resolves the projector reference, creates agent/shim, schedules 100-frame updates |
| `Close()` | override method | Disposes the agent (if `IDisposable`) and clears references |
| `UpdateBeforeSimulation100()` | override method | Blueprint-change detection and state-change polling |
| `LogAndChatSubgridStateChanges(projectorEntityId)` | private method | Compares state hashes per subgrid and announces changes |
| `GatherBlueprintDetails()` | private method | Full API dump to log and chat on blueprint load |

### Packaging and folder layout

The mod folder is `ModApiTest/Mod/` and is deployed to
`%AppData%\SpaceEngineers\Mods\Multigrid Projector Mod API Test\`.

```
Mod/
  modinfo.sbmi           — Steam Workshop ID (2433810091)
  metadata.mod           — ModVersion 0.9.2
  thumb.jpg
  Data/
    Scripts/
      MultigridProjector/
        ModApiTest/
          MultigridProjectorModApiTest.cs   ← the example class
        Api/
          README.md                         ← copy instructions
          (BlockLocation.cs etc. are copied by Deploy.bat at deploy time)
```

The five API source files (`BlockLocation.cs`, `BlockState.cs`, `IMultigridProjectorApi.cs`,
`MultigridProjectorModAgent.cs`, `MultigridProjectorModShim.cs`) live in
`MultigridProjectorApi/Api/` at the repo root and are **not checked in** under `ModApiTest/Mod/`.
`Deploy.bat` copies them into place so the mod folder is complete before use. The `README.md`
inside `Api/` records which files to copy for developers setting up their own mod.

### How to run

1. Install the [Plugin Loader](https://github.com/sepluginloader/SpaceEngineersLauncher) and
   enable the Multigrid Projector plugin; restart the game.
2. Build the solution (or run `Deploy.bat` from the post-build step — see
   [Build-And-Project-Layout.md](./Build-And-Project-Layout.md)).
3. Add the mod ("Multigrid Projector Mod API Test") to a world and load it.
4. Place a projector block and load a multi-subgrid blueprint.
5. Check the SE client log (`SpaceEngineers.log`) for the API dump output.

---

## IngameApiTest (PB script example)

### What it does

`Script.cs` is a standard Programmable Block script that:

1. Locates a block named `"Projector"` on the same grid.
2. Instantiates `MultigridProjectorProgrammableBlockAgent` (embedded in the same file below the
   `#region MGP API Agent` marker) using the PB's own block reference.
3. On every `Main()` invocation, calls `EchoBlueprintDetails` which writes a formatted summary
   to the PB's `Echo` output covering: scan number, subgrid count, preview/built grids,
   base/top connections, state hash, completion flag, all block states, and the YAML dump.

The script is wrapped in `#if INGAME` / `#endif` guards so it can be compiled as a C# project
in the IDE for syntax checking without dragging in game assemblies as real dependencies.

### How the agent is obtained (in-script shim pattern)

```csharp
mgp = new MultigridProjectorProgrammableBlockAgent(Me);
```

The constructor reads the custom block property `"MgpApi"` exposed by the plugin on the PB block:

```csharp
api = programmableBlock.GetProperty("MgpApi")?.As<Delegate[]>().GetValue(programmableBlock);
```

It expects at least 12 delegates (indices 0–11). Index 0 is a `Func<string>` that returns the
version string; if that succeeds, `Available` is set to `true`. All subsequent wrapper methods
guard on `Available` and cast the appropriate delegate before calling it. This avoids any hard
dependency on the plugin's assembly — the entire agent is self-contained source code that the
script compiler sees as part of the script.

### API calls demonstrated

| Call | Delegate index | Description |
|---|---|---|
| `GetSubgridCount(projectorId)` | `api[1]` | Number of subgrids in the active projection |
| `GetPreviewGrid(projectorId, subgridIndex)` | `api[2]` | Preview (hologram) grid object |
| `GetBuiltGrid(projectorId, subgridIndex)` | `api[3]` | Built grid object, or null |
| `GetBlockState(projectorId, subgridIndex, position)` | `api[4]` | Single-block build state |
| `GetBlockStates(dict, projectorId, subgridIndex, box, mask)` | `api[5]` | Bulk block-state fill |
| `GetBaseConnections(projectorId, subgridIndex)` | `api[6]` | Base-part connection map |
| `GetTopConnections(projectorId, subgridIndex)` | `api[7]` | Top-part connection map |
| `GetScanNumber(projectorId)` | `api[8]` | Scan sequence counter |
| `GetYaml(projectorId)` | `api[9]` | Full YAML dump |
| `GetStateHash(projectorId, subgridIndex)` | `api[10]` | Per-subgrid block-state hash |
| `IsSubgridComplete(projectorId, subgridIndex)` | `api[11]` | True if subgrid fully welded |

### Types embedded in the script

#### `BlockLocation` struct

| Member | Kind | Description |
|---|---|---|
| `GridIndex` | `readonly int` | Subgrid index of the connected part |
| `Position` | `readonly Vector3I` | Grid-local position of the connected part |
| `BlockLocation(gridIndex, position)` | constructor | Value-type initialiser |
| `GetHashCode()` | override | Combines grid index and position components |

#### `BlockState` enum

| Value | Int | Meaning |
|---|---|---|
| `Unknown` | 0 | State not yet determined by the background worker |
| `NotBuildable` | 1 | No connectivity or collision prevents placement |
| `Buildable` | 2 | Ready to weld (connections valid, no collision) |
| `BeingBuilt` | 4 | Partially welded, below blueprint integrity threshold |
| `FullyBuilt` | 8 | At or above blueprint integrity requirement |
| `Mismatch` | 128 | Wrong block definition in the projected position |

#### `MultigridProjectorProgrammableBlockAgent` class

| Member | Kind | Description |
|---|---|---|
| `api` | `Delegate[]` | Raw delegate array retrieved from the `"MgpApi"` block property |
| `Available` | `bool` property | True when the plugin exposed a valid delegate array |
| `Version` | `string` property | Version string returned by `api[0]` |
| `GetSubgridCount(projectorId)` | method | Wraps `api[1]` |
| `GetPreviewGrid(projectorId, subgridIndex)` | method | Wraps `api[2]` |
| `GetBuiltGrid(projectorId, subgridIndex)` | method | Wraps `api[3]` |
| `GetBlockState(projectorId, subgridIndex, position)` | method | Wraps `api[4]` |
| `GetBlockStates(dict, projectorId, subgridIndex, box, mask)` | method | Wraps `api[5]`; translates `int` values to `BlockState` |
| `GetBaseConnections(projectorId, subgridIndex)` | method | Wraps `api[6]`; reconstructs `Dictionary<Vector3I, BlockLocation>` from three parallel lists |
| `GetTopConnections(projectorId, subgridIndex)` | method | Wraps `api[7]`; same parallel-list pattern |
| `GetScanNumber(projectorId)` | method | Wraps `api[8]` |
| `GetYaml(projectorId)` | method | Wraps `api[9]` |
| `GetStateHash(projectorId, subgridIndex)` | method | Wraps `api[10]` |
| `IsSubgridComplete(projectorId, subgridIndex)` | method | Wraps `api[11]` |
| `MultigridProjectorProgrammableBlockAgent(programmableBlock)` | constructor | Reads `"MgpApi"` property, validates length >= 12, calls `api[0]` for version |

### Packaging and deployment

The script payload is `IngameApiTest/Script/` containing:

```
Script/
  Script.cs        — the full PB script including the embedded agent shim
  metadata.mod     — ModVersion 1.0
  modinfo.sbmi     — Steam Workshop ID (2471605159)
  thumb.png
```

`Deploy.bat` copies the entire `Script/` folder to
`%AppData%\SpaceEngineers\IngameScripts\local\Multigrid Projector Ingame API Test\`.
After deployment the script appears in the game's local ingame-script browser.

### How to run

1. Install the Plugin Loader and enable the Multigrid Projector plugin; restart the game.
2. Run `Deploy.bat` (or build with the post-build step — see
   [Build-And-Project-Layout.md](./Build-And-Project-Layout.md)).
3. In-game, place a Programmable Block and open it; browse local scripts and load
   "Multigrid Projector Ingame API Test".
4. Place a projector named `"Projector"` on the same grid and load a multi-subgrid blueprint.
5. Run the PB; the `Echo` panel shows the full projection dump.

---

## Cross-references

- [Public-API.md](./Public-API.md) — canonical API contract (`IMultigridProjectorApi`, all method
  signatures and semantics)
- [Core-Projection-Engine.md](./Core-Projection-Engine.md) — internals that produce the data
  these examples consume
- [Build-And-Project-Layout.md](./Build-And-Project-Layout.md) — post-build `Deploy.bat` hooks
  that automate deployment of both examples
- [../API.md](../API.md) — user-facing API overview
