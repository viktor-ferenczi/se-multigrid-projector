# Core Projection Engine (Shared/Logic)

The `MultigridProjector.Logic` namespace is the engine of the plugin: it owns the per-projector
projection state machine, tracks every subgrid of a multigrid blueprint and the grid actually built
from it, computes per-block weld/grind state, manages the mechanical (rotor/hinge/piston) and
wheel connections that hold subgrids together, runs the background scan/work loop that keeps all of
this current, and exposes the result through the API provider that backs both the Mod API and the
Programmable Block API. The client ([Client-Patches.md](./Client-Patches.md)) and server
([Server-Patches.md](./Server-Patches.md)) plugins are thin Harmony shims that delegate into the
static and instance entry points of this module; the public-facing data contracts (`BlockState`,
`BlockLocation`, `IMultigridProjectorApi`) live in [Public-API.md](./Public-API.md). See also the
parent [../Architecture.md](../Architecture.md) and [../API.md](../API.md).

## Files

| File | Lines | Purpose |
|------|------:|---------|
| [MultigridProjection.cs](../../Shared/Logic/MultigridProjection.cs) | 2365 | Central per-projector class: lifecycle, subgrid/connection bookkeeping, build & placement checks, the update loop, and all Harmony entry points. |
| [Subgrid.cs](../../Shared/Logic/Subgrid.cs) | 784 | One blueprint subgrid: preview grid, optional built grid, block models, connections, grid-event handling, and background block-state scanning. |
| [ReferenceFixer.cs](../../Shared/Logic/ReferenceFixer.cs) | 700 | Restores inter-block references (toolbars, toolbar group items, controllers, weapon/tool selections, AI waypoints) on freshly built blocks by mapping blueprint IDs to built EntityIds. |
| [MultigridProjectorApiProvider.cs](../../Shared/Logic/MultigridProjectorApiProvider.cs) | 228 | Implements `IMultigridProjectorApi` and publishes the Mod API (mod message) and Programmable Block API (terminal property). |
| [ProjectedBlock.cs](../../Shared/Logic/ProjectedBlock.cs) | 157 | Pairs a preview block with its blueprint builder; detects build/grind state and drives preview transparency visuals. |
| [MultigridUpdateWork.cs](../../Shared/Logic/MultigridUpdateWork.cs) | 127 | `IWork` background task that scans all supported subgrids off the main thread and raises a completion event. |
| [ProjectionStats.cs](../../Shared/Logic/ProjectionStats.cs) | 87 | Aggregable block counts (total, remaining, buildable, per-type) used for projector stats and completion. |
| [MultigridProjectorSession.cs](../../Shared/Logic/MultigridProjectorSession.cs) | 64 | Session object wiring up Mod API request handling and lazy PB API registration. |
| [Connection.cs](../../Shared/Logic/Connection.cs) | 59 | `Connection<T>` base plus `BaseConnection`/`TopConnection`: one side of a mechanical link. |
| [FastBlockLocation.cs](../../Shared/Logic/FastBlockLocation.cs) | 53 | `(gridIndex, position)` value struct with hand-written equality/hash to avoid boxing. |
| [BlockMinLocation.cs](../../Shared/Logic/BlockMinLocation.cs) | 26 | `(gridIndex, minPosition)` key struct used to map blueprint and preview mechanical blocks. |
| [VisualState.cs](../../Shared/Logic/VisualState.cs) | 10 | Enum of preview visual states (None/Hidden/Hologram/Transparent). |
| [ProjectorSubgrid.cs](../../Shared/Logic/ProjectorSubgrid.cs) | 9 | `Subgrid` subclass marking index 0, the grid carrying the projector. |

## Architecture

**Projection setup.** A projection is created lazily. The game's `MyProjectorBase.UpdateAfterSimulation`
is patched to call `MultigridProjection.ProjectorUpdateAfterSimulation`, which, the first time it sees
a working projector with an active clipboard and original grid builders, calls `Create` to construct a
`MultigridProjection`. The constructor takes the projector and the list of `MyObjectBuilder_CubeGrid`
blueprint builders, grabs the projector's `MyProjectorClipboard` (whose `PreviewGrids` are the
already-instantiated preview grids), and then runs four setup passes under a lock on `GridBuilders`:
`MapBlueprintBlocks` walks the blueprint to build the bidirectional `BlueprintConnections` map between
mechanical base and top blocks (matched via `TopBlockId`); `MapPreviewBlocks` indexes the preview base
and top blocks by `BlockMinLocation`; `CreateSubgrids` creates one `Subgrid` per grid (index 0 is a
`ProjectorSubgrid` pre-registered to the projector's own grid); and `MarkSupportedSubgrids` flood-fills
from subgrid 0 over mechanical connections to flag every subgrid that is *supported* (weldable from the
projection). Subgrids reachable only through connectors (separate ships, missiles) stay unsupported and
are eventually hidden. Finally a `ReferenceFixer` is built over the supported subgrids, subgrid events
are subscribed, the `MultigridUpdateWork` is created, and a first forced update is requested. On the
client side, `InitFromObjectBuilder` prepares, normalizes, remaps and broadcasts the blueprint before
any of this happens.

**Subgrid and connection discovery.** Each `Subgrid` builds a `Dictionary<Vector3I, ProjectedBlock>`
keyed by preview position (`CreateBlockModels`) and discovers its own mechanical links in
`FindMechanicalConnections`, producing `BaseConnections` (this grid holds the rotor/hinge/piston base)
and `TopConnections` (this grid holds the head/top), each carrying the `BlockLocation` of its
counterparty on the other subgrid. The projection navigates between the two halves with
`GetCounterparty`. Connection objects (`BaseConnection`/`TopConnection`) hold the preview block, the
built `Block` once it appears, a `Found` block discovered by the scan, and a `RequestAttach` flag.

**Built vs preview grids.** Every subgrid has a `PreviewGrid` (the hologram from the clipboard) and an
optional `BuiltGrid` (the real grid as it gets welded). Subgrid 0's built grid is the projector's grid
from the start; other subgrids get a built grid registered via `RegisterBuiltGrid` only once their
mechanical part is built and attached. Positions are translated between the two coordinate systems with
`PreviewToBuiltBlockPosition`/`BuiltToPreviewBlockPosition` (world-space round-trips), because preview
and built grids are not pixel-aligned. `UpdateGridTransformations` (called each frame from
`UpdateAfterSimulation`) re-positions preview grids: subgrid 0 is placed relative to the projector
(applying offset/rotation), and the rest are aligned iteratively to already-built or already-positioned
neighbours through their connections.

**Block state computation.** `ProjectedBlock.DetectBlock` is the core per-block classifier: given the
built grid it looks up the block at the translated position and resolves a `BlockState` — `NotBuildable`,
`Buildable` (via `Projector.CanBuild`), `Mismatch` (wrong definition present), `BeingBuilt` (present but
under target integrity) or `FullyBuilt`. `MultigridProjection.CanBuild` reimplements the stock build
check across the preview/built coordinate transform, including connectivity, a cached voxel intersection
test (`CheckVoxels`/`EnsureVoxelCache`), and optional Havok placement testing. State drives
`ProjectedBlock.UpdateVisual`, which maps state to a `VisualState` and sets preview transparency
(hidden / hologram / buildable-transparent), honouring the projector's "show only buildable" setting.

**The update / work loop.** Block detection is expensive, so it runs on a background thread.
`UpdateAfterSimulation` decides when a rescan is due (respecting an `UpdateCooldownTime` and the
projector's should/force-update flags) and calls `StartUpdateWork`, which kicks off the
`MultigridUpdateWork` `IWork` task. On the worker thread each supported subgrid runs
`UpdateBlockStatesBackgroundWork` (detect every block, rebuild per-subgrid `Stats`, compute a
`StateHash`) and `FindBuiltBase/TopConnectionsBackgroundWork` (record newly appeared connection
blocks into `Found`). The worker writes **only** into dedicated per-subgrid fields to stay thread-safe;
the heavier `Stats`/`Blocks` are guarded by `RwLock`s. On completion `OnUpdateWorkCompleted` runs back
on the game thread: it bumps `ScanNumber` (which gates `IsValidForApi` and invalidates the cached YAML),
runs `UpdateMechanicalConnections` (promoting `Found` blocks into live connections, on the server
building missing heads/bases with `BuildMissingHead`/`BuildMissingBase` and attaching them, registering
newly built subgrids, and flood-filling `IsConnectedToProjector` to drop split-off subgrids), aggregates
statistics, pushes them to the projector, updates preview visuals and sounds, and schedules built
terminal blocks for reference restoration. Built grids also raise change events
(`OnBlockAdded/Removed/IntegrityChanged`, split/merge, closing) that simply call `RequestUpdate` to
trigger the next scan.

**Reference restoration.** When a terminal block (remote control, event controller, turret controller,
timer, button panel, etc.) is welded, its toolbar slots and block references still point at blueprint
EntityIds. `ReferenceFixer` precomputes, from the blueprint, which blocks reference which, and once both
referrer and referee are built it rewrites the live block's toolbar items, bound cameras, selected
blocks, weapons/tools, waypoints and button names via `TryMapPreviewToBuiltTerminalBlock`. Restoration
is queued during the update loop and applied on the game thread (immediately on the server, after a
short frame delay on clients).

**API exposure.** `MultigridProjectorApiProvider` implements `IMultigridProjectorApi` by looking up the
projection/subgrid for a projector id and reading state through the same locked accessors. It publishes
three shapes of the same data: the in-process `Api` singleton (used by the plugins),
the `ModApi` `object[]` of delegates sent over `SendModMessage` in response to a request id
(wired up by `MultigridProjectorSession`), and the `PbApi` `Delegate[]` registered as a hidden
`MgpApi` terminal property on programmable blocks. All API calls are gated by `IsValidForApi`
(initialized and scanned at least once) so callers never see a half-built model.

## MultigridProjection

*`public class MultigridProjection` in `MultigridProjector.Logic`. The central, non-static engine class — one instance per active projector, tracked in a static registry. Marked `// FIXME: Refactor this class`.*

The orchestrator. It owns the subgrids, the blueprint/preview connection maps, the background update
work, aggregated stats and the reference fixer, and hosts every Harmony entry point used by the client
and server patch modules. Instances are kept in the static `Projections` dictionary keyed by the
projector's `EntityId`; lookups are the primary way patches reach the engine.

| Member | Kind | Description |
|--------|------|-------------|
| `Projections` | field (static) | `RwLockDictionary<long, MultigridProjection>` of active projections by projector EntityId. |
| `Projector` | field | The `MyProjectorBase` this projection drives. |
| `GridBuilders` | field | Blueprint grid builders (locked while remapping or reading consistency). |
| `subgrids` / `subgridsLock` | field | Ordered subgrid list (index 0 = projector grid) and its `RwLock`. |
| `SetPreviewBlockVisuals` | property (static) | Whether audio/visual updates run; from `PluginConfig` (true on client, server-configured). |
| `CheckHavokIntersections` | field | Enables Havok-based detection (client highlighting); shortens the scan cooldown. |
| `BlueprintConnections` | field | Bidirectional base↔top map by `BlockMinLocation`, built from the blueprint. |
| `PreviewBaseBlocks` / `PreviewTopBlocks` | field | Preview mechanical base/top blocks by `BlockMinLocation`. |
| `GridCount` / `PreviewGrids` | property | Number of blueprint grids; the clipboard's preview grids. |
| `Initialized` | property | True once setup completed; guards almost every entry point. |
| `ScanNumber` / `IsValidForApi` | field/property | Scan counter (bumped per completed scan); API readiness gate (`Initialized && HasScanned`). |
| `stats` | field | Latest aggregated `ProjectionStats`. |
| `updateWork` | field | The `MultigridUpdateWork` background task. |
| `referenceFixer` | field | `ReferenceFixer` over supported subgrids. |
| `Create` | method (static) | Constructs and registers a projection (returns null if one already exists). |
| `MultigridProjection(...)` | ctor | Runs all setup passes (map blueprint/preview, create/mark subgrids, build fixer, wire events, start). |
| `Destroy` | method | Tears down: unregisters events, disposes work, clears subgrids and stats. |
| `EnsureNoProjections` | method (static) | Diagnostic warning if any projection is still active when none should be. |
| `TryFindProjectionByProjector` | method (static) | Look up a projection by projector or projector id. |
| `TryFindSubgrid` | method (static) | Look up projection + supported subgrid by id and index. |
| `TryFindProjectionByBuiltGrid` | method (static) | Reverse lookup from a built `MyCubeGrid`. |
| `TryFindPreviewGrid` | method | Index of a preview grid within this projection. |
| `TryGetProjectedBlock` / `TryGetSupportedSubgrid` / `GetSupportedSubgrids` | method | Accessors over supported subgrids and their projected blocks. |
| `SupportedSubgrids` / `UnsupportedSubgrids` | property (private) | Subgrids weldable / not weldable from this projection. |
| `MapBlueprintBlocks` / `MapPreviewBlocks` | method (private) | Build the blueprint and preview connection maps. |
| `CreateSubgrids` / `MarkSupportedSubgrids` | method (private) | Create subgrids; flood-fill supported flags over connections. |
| `OnPropertiesChanged` | method (private) | Detects KeepProjection / ShowOnlyBuildable / offset-rotation changes and reacts. |
| `OnUpdateWorkCompleted(WithErrorHandler)` | method | Game-thread callback after a scan: bumps `ScanNumber`, updates connections, stats, visuals, restore queue. |
| `UpdateMechanicalConnections` | method (private) | Promotes found connection blocks, builds/attaches missing parts, updates connectedness, drops disconnected subgrids. |
| `UpdateBaseConnection` / `UpdateTopConnection` | method (private) | Per-connection update: find newly built/added parts, build missing counterpart, register subgrid. |
| `BuildMissingHead` / `BuildMissingBase` | method (private, server) | Create and attach the missing top/base grid+block for a half-built mechanical connection. |
| `CreateTopPartAndAttach` | method (server) | Build the correctly sized/model head for a base block and attach it (used by a server patch). |
| `RegisterConnectedSubgrid` | method (private) | Registers a subgrid's built grid once both connection halves exist; configures base to match top. |
| `IsConnected` | method (private) | Whether a base and its top are actually attached (same TopBlock EntityId). |
| `UpdateSubgridConnectedness` / `UnregisterDisconnectedSubgrids` | method (private) | Flood-fill `IsConnectedToProjector`; unregister subgrids that split off. |
| `UpdateGridTransformations` | method (private) | Re-position preview grids each frame, aligning to built/positioned neighbours. |
| `BuildInternal` | method (server) | Validates and issues the actual block build request on the correct subgrid (DLC/welding/buildable checks). |
| `CanBuild` | method | Reimplemented build check across the preview/built transform (connectivity, voxels, Havok). |
| `TestPlacementAreaCube` | method | True if a base block's preview maps to a built top subgrid (placement gate). |
| `FindProjectedBlock` | method (private) | Ray-pick the nearest buildable preview block for hand welding (per-thread scratch arrays). |
| `FindProjectedBlocks` | method (static, server) | Ship-welder variant: find all buildable preview blocks in a detector sphere. |
| `MyWelder_FindProjectedBlock` | method (static, client) | Client welder entry point delegating to `FindProjectedBlock`. |
| `CheckVoxels` / `EnsureVoxelCache` / `InvalidateVoxelCache` | method (private) | Cached voxel-intersection test around the projector (500 m sphere, invalidated on voxel add/remove or 100 m move). |
| `InitializeClipboard` | method | Activate the clipboard/preview without consuming PCU. |
| `GetObjectBuilderOfProjector` | method (static) | Fix blueprint remapping when the projector is copied/saved. |
| `ProjectorInit` | method (static) | Capture original grid builders on projector init. |
| `InitFromObjectBuilder` | method (static, client) | Client-side blueprint prepare/normalize/remap and broadcast on load. |
| `ProjectorUpdateAfterSimulation` | method (static) | Per-frame patch entry: lazily creates the projection and runs `UpdateAfterSimulation`. |
| `UpdateAfterSimulation` | method (private) | Per-frame work: grid transforms, terminal restore, decide and start the next scan. |
| `RemoveProjection` | method | Tear down the projection and optionally clear the blueprint/clipboard. |
| `ShouldUpdateProjection` / `ForceUpdateProjection` / `RescanFullProjection` | method | Request a rescan (soft / forced / full re-register of built grids). |
| `AggregateStatistics` / `UpdateProjectorStats` | method | Sum subgrid stats and push totals to the projector. |
| `UpdatePreviewBlockVisuals` / `HidePreviewGrids` | method (private) | Refresh or hide preview block visuals. |
| `GetYaml` | method | Human-readable dump of subgrids, blocks, states and connections (cached per scan). |
| `ScheduleTerminalBlocksForRestore` / `RestoreTerminalBlocks` | method (private) | Queue built terminal blocks and apply `ReferenceFixer` restoration (server immediate, client delayed). |
| `FixBlockRelations` | method | Restore all block references (`ReferenceFixer.RestoreAll`). |
| `TryMapPreviewToBuiltTerminalBlockId` / `MapPreviewToBuiltTerminalBlockIds` | method | Map blueprint terminal block ids to built EntityIds. |
| `RaiseAttachedEntityChanged` / `ShouldAllowBuildingDefaultTopBlock` | method | Force a rescan on attach change; veto the stock auto-built head for projected bases. |

## Subgrid

*`public class Subgrid : IDisposable` in `MultigridProjector.Logic`.*

Represents one grid of the blueprint. It owns its preview grid, its (optional) built grid, the
`ProjectedBlock` models keyed by preview position, the mechanical connections originating on it, its
welding statistics, and the grid event subscriptions. The background worker writes its scan results
into dedicated fields here; all shared collections are protected by `RwLock`s. Subclassed by
[`ProjectorSubgrid`](#projectorsubgrid) for index 0.

| Member | Kind | Description |
|--------|------|-------------|
| `Index` | field | Subgrid index; also indexes the preview grid list (0 = projector grid). |
| `GridBuilder` | field | This subgrid's blueprint builder. |
| `PreviewGrid` | field | Preview (hologram) grid from the clipboard. |
| `BuiltGrid` / `BuiltGridLock` / `HasBuilt` | property/field | The real grid once built, its lock, and a built-state flag. |
| `Stats` | property | Latest welding statistics (swapped in by the worker). |
| `IsConnectedToProjector` | field | Whether this built subgrid is mechanically connected back to the projector. |
| `BaseConnections` / `TopConnections` | field | Mechanical base / top connections on this subgrid by preview position. |
| `IsUpdateRequested` | field | A rescan of this subgrid has been requested. |
| `Supported` | field | This subgrid is weldable from the projection. |
| `Blocks` / `BlocksLock` | field | Projected block models by preview position, and their lock. |
| `Positioned` | field | The preview grid has been aligned this frame. |
| `StateHash` | property | Hash of all block states; drives change detection for visuals/API. |
| `OnTerminalBlockAdded` | event | Fired when a functional block is welded (drives reference restoration). |
| `Subgrid(projection, index)` | ctor | Builds block models, collects initial stats, finds mechanical connections. |
| `CreateBlockModels` | method (private) | Pair preview blocks with blueprint builders into `ProjectedBlock`s. |
| `FindMechanicalConnections` / `PrepareBase` / `PrepareTop` | method (private) | Populate `BaseConnections`/`TopConnections` from blueprint+preview maps. |
| `Dispose` | method | Unregister built grid and clear connections/blocks. |
| `TryGetProjectedBlock` / `TryGetBlockBuilder` / `TryGetBlockState` | method | Locked lookups by preview position. |
| `HasBuildableBlockAtPosition` | method | True if a built grid exists and the block there is `Buildable`. |
| `RequestUpdate` | method | Mark this subgrid for rescan (only if supported). |
| `IterBlockStates` | method | Enumerate `(position, state)` filtered by a bounding box and state mask (backs the API). |
| `GetBlockOrientationQuaternion` | method | Orientation of a preview block relative to the built grid. |
| `PreviewToBuiltBlockPosition` / `BuiltToPreviewBlockPosition` | method | Translate positions between preview and built coordinate systems. |
| `ConfigureBuiltGrid` | method | Copy the preview display name onto a newly built subgrid. |
| `RegisterBuiltGrid` / `UnregisterBuiltGrid` | method | Attach/detach a built grid: (un)subscribe events, reset stats/blocks/connections. |
| `ConnectGridEvents` / `DisconnectGridEvents` | method (private) | (Un)subscribe block add/remove/integrity, split/merge, closing handlers. |
| `OnBlockIntegrityChanged` | method (private, server) | Request a rescan when a block crosses its target integrity. |
| `OnBlockAdded` / `OnBlockRemoved` | method (private) | Track built mechanical/terminal blocks, request rescan, fire `OnTerminalBlockAdded`. |
| `OnGridSplitOrMerge` / `OnGridClosing` / `OnCheckConnectionChanged` | method (private) | Re-register or drop the built grid; request rescans on topology changes. |
| `UpdatePreviewBlockVisuals` / `Hide` / `HidePreviewGrid` | method | Refresh preview transparency (skipped if state hash unchanged) or hide preview blocks. |
| `AddBlockToGroups` / `RemoveBlockFromGroups` | method (server) | Maintain named block groups on the built grid from the blueprint groups. |
| `UpdateBlockStatesBackgroundWork` | method | Worker: detect every block, rebuild `stats`, compute `StateHash`; returns block count. |
| `FindBuiltBaseConnectionsBackgroundWork` / `FindBuiltTopConnectionsBackgroundWork` | method | Worker: record built mechanical blocks into connection `Found` fields. |

## ProjectorSubgrid

*`public class ProjectorSubgrid : Subgrid` in `MultigridProjector.Logic`.*

Trivial subclass used for subgrid index 0 — the grid that carries the projector. It exists only to give
that subgrid a distinct type; its built grid is the projector's own grid, registered at construction.

| Member | Kind | Description |
|--------|------|-------------|
| `ProjectorSubgrid(projection)` | ctor | Calls the base `Subgrid` constructor with index 0. |

## ProjectedBlock

*`public class ProjectedBlock` in `MultigridProjector.Logic`.*

One projected block: the pairing of a preview `MySlimBlock` with its blueprint `MyObjectBuilder_CubeBlock`.
It is the unit of state detection and preview rendering. `DetectBlock` classifies the block against the
built grid; `UpdateVisual` translates that state into a transparency setting. Built positions are cached
once a built grid exists, since the preview→built transform is a world-space round-trip.

| Member | Kind | Description |
|--------|------|-------------|
| `Builder` | field | Original blueprint builder (clone before mutating). |
| `Preview` | field | Preview `MySlimBlock` on the projected grid. |
| `State` | property | Current `BlockState` (Unknown/NotBuildable/Buildable/Mismatch/BeingBuilt/FullyBuilt). |
| `BuildCheckResult` | property | Latest `BuildCheckResult` from the build check. |
| `SlimBlock` | property | The matching built block, if present. |
| `BuiltPosition` / `HasBuiltGrid` | property (private) | Cached position on the built grid and whether it is set. |
| `ProjectedBlock(preview, builder)` | ctor | Pair a preview block with its builder. |
| `Clear` | method | Reset to the unbuilt/unknown state. |
| `DetectBlock` | method | Classify the block against the built grid (calls `CanBuild` when missing). |
| `UpdateVisual` | method | Apply the visual state if it changed (hide / hologram / transparent). |
| `GetVisualState` | method (private) | Map `BlockState` (+ show-only-buildable) to a `VisualState`. |

## Connection (BaseConnection / TopConnection)

*`public abstract class Connection<T> where T : MyCubeBlock`, with concrete `BaseConnection : Connection<MyMechanicalConnectionBlockBase>` and `TopConnection : Connection<MyAttachableTopBlockBase>`, in `MultigridProjector.Logic`.*

Represents one side of a mechanical link between two subgrids. The base type holds the preview block,
the built block (`Block`, with `HasBuilt`), the `volatile Found` block discovered by the background
worker, and a `RequestAttach` flag. `BaseConnection` additionally stores the `TopLocation` of its head
and `TopConnection` the `BaseLocation` of its stator; both expose an `IsWheel` test (suspension / wheel)
so wheels can be treated specially.

| Member | Kind | Description |
|--------|------|-------------|
| `Preview` | field | The preview block for this connection side. |
| `Block` / `HasBuilt` | field/property | Built block (null if not built / closed). |
| `Found` | field (volatile) | Block discovered by the worker; promoted into `Block` on the game thread. |
| `RequestAttach` | field | Requests attaching the counterparty when both sides exist. |
| `ClearBuiltBlock` | method | Reset `Block`, `Found`, `RequestAttach`. |
| `BaseConnection.TopLocation` | field | `BlockLocation` of the head this base connects to. |
| `BaseConnection.IsWheel` | property | True if the base is a `MyMotorSuspension`. |
| `TopConnection.BaseLocation` | field | `BlockLocation` of the stator this head connects to. |
| `TopConnection.IsWheel` | property | True if the top is a `MyWheel`. |

## MultigridUpdateWork

*`public class MultigridUpdateWork : IWork, IDisposable` in `MultigridProjector.Logic`.*

The background scan task. `Start` launches a `ParallelTasks` task running `DoWork`, which scans all
supported subgrids (block states + statistics, then mechanical connection discovery) entirely off the
main thread, writing only into per-subgrid worker fields. On success it raises `OnUpdateWorkCompleted`
on the game thread, which the projection handles. `ShouldStop` lets a scan bail out early when the
projection is torn down or the projector closes.

| Member | Kind | Description |
|--------|------|-------------|
| `OnUpdateWorkCompleted` | event | Raised on completion of a successful scan (game thread). |
| `IsComplete` | property | True when no scan is running. |
| `ShouldStop` | property (private) | Worker should abort (stop requested, not initialized, or projector closed). |
| `SubgridsScanned` / `BlocksScanned` | field | Per-scan counters for performance logging. |
| `Options` | property | `WorkOptions` with profiler debug info. |
| `MultigridUpdateWork(projection)` | ctor | Bind to the owning projection. |
| `Dispose` | method | Signal stop and wait for the running task. |
| `Start` | method | Launch the background task if the previous one is complete. |
| `DoWork` | method | Worker body: update block states/stats then find built mechanical connections. |
| `UpdateBlockStatesAndCollectStatistics` / `FindBuiltMechanicalConnections` | method (private) | The two worker phases over supported subgrids. |
| `OnComplete` | method (private) | Raise the completion event only if the scan succeeded. |

## ProjectionStats

*`public class ProjectionStats` in `MultigridProjector.Logic`.*

A mutable, aggregable bag of block counts. Each subgrid scan rebuilds its own `ProjectionStats`; the
projection sums them with `Add` to drive the projector's displayed totals and the build-completion
decision (`IsBuildCompleted`).

| Member | Kind | Description |
|--------|------|-------------|
| `TotalBlocks` / `TotalArmorBlocks` | field | Total and armor-only block counts. |
| `RemainingBlocks` / `RemainingArmorBlocks` | field | Not-yet-fully-built block counts. |
| `BuildableBlocks` | field | Blocks currently weldable or being built. |
| `RemainingBlocksPerType` | field | Remaining count per `MyCubeBlockDefinition`. |
| `IsBuildCompleted` | property | True when valid and nothing remains. |
| `Clear` | method | Reset all counters. |
| `RegisterBlock` | method | Tally one block by its `BlockState`. |
| `Add` | method | Accumulate another `ProjectionStats` into this one. |

## ReferenceFixer

*`public class ReferenceFixer` in `MultigridProjector.Logic`.*

Restores inter-block references that the stock projector cannot, because welded blocks store EntityIds
that only exist in the original blueprint. The constructor scans the blueprint to index every terminal
block by id and to build a `referenceMap` of who references whom. When a block is built,
`Restore` rewrites its own references and those of any block that points at it, using
`TryMapPreviewToBuiltTerminalBlock` to translate blueprint ids to live EntityIds. Handles toolbars and
a range of specific block types (remote control, event controller, turret controller, offensive combat,
AI path recorder, button panel, ship controllers, timers, sensors).

Toolbar restoration handles both kinds of toolbar item:

- **Single-block items** (`MyObjectBuilder_ToolbarItemTerminalBlock`) target one block directly by
  `BlockEntityId`; that id is remapped from the preview block to the built block.
- **Group items** (`MyObjectBuilder_ToolbarItemTerminalGroup`) are anchored to a grid by `BlockEntityId`
  and resolved at runtime by group name (`MyToolbarItemTerminalGroup.GetBlocks`). After welding, the
  stored anchor still points at the preview block, so it is remapped to the built block — otherwise the
  group resolves to no blocks and the slot/action renders empty. The group's *membership* is restored
  separately by the Subgrid block-group restoration. Group items also register a dependency on their
  anchor block in `referenceMap`, so a group-only toolbar is re-restored once the anchor is welded
  (without it, such a toolbar would register no dependencies and never retry).

Two block types needed multiplayer-specific handling, because on the server the freshly welded block
is "clean" — it carries none of the blueprint's component object-builder state:

- **Offensive combat** — the selected weapons are stored per *attack strategy* sub-component
  (circle-orbit, hit-and-run, stay-at-range), each force-created and registered under its own concrete
  type. `MyComponentContainer.TryGet` does an exact-type lookup, so each strategy's weapons are restored
  individually via the generic `RestoreOffensiveCombatWeapons<T>` rather than through the abstract base
  `MyOffensiveWithWeaponsCombatComponent` (which is not a registration key and would never match).
- **AI path recorder** — in multiplayer the server welds a block whose path-recorder component has no
  waypoints (waypoints are only loaded from the component object builder at init time, which a freshly
  welded block lacks). `RestorePathRecorder` reconstructs the missing `MyAutopilotWaypoint`s from the
  blueprint, then remaps each waypoint's toolbar-action block references; `MyPathRecorderComponent.Serialize`
  writes them back so clients receive them on replication.

| Member | Kind | Description |
|--------|------|-------------|
| `blocksById` | field (private) | Terminal `ProjectedBlock`s by blueprint EntityId. |
| `referenceMap` | field (private) | For each referenced block id, the set of referrer ids. |
| `ReferenceFixer(subgrids)` | ctor | Index terminal blocks and build the reference map. |
| `IterReferencedBlockIds` / `IterToolbarReferencedBlockIds` / `IterOffensiveCombatReferencedBlockIds` | method (private) | Enumerate the blueprint ids a block refers to (per block type). |
| `TryMapPreviewToBuiltTerminalBlock<T>` | method | Map a blueprint terminal block id to its built block (only if being/fully built and in scene). |
| `Restore` / `RestoreSafe` | method | Restore a built block's references plus its referrers (Safe wraps in try/catch). |
| `RestoreAll` / `RestoreAllSafe` | method | Restore every indexed block. |
| `RestoreOneWay` | method (private) | Restore one block's outgoing references by builder type. |
| `RestoreToolbar` / `RestoreToolbarActions` | method (private) | Rewrite toolbar slot / action targets; handle both single-block and group toolbar items. |
| `RestoreRemoteControl` / `RestoreEventController` / `RestoreTurretController` / `RestoreOffensiveCombat` / `RestorePathRecorder` / `RestoreButtonPanel` | method (private) | Type-specific reference restoration. `RestorePathRecorder` also reconstructs missing waypoints on server-welded blocks. |
| `RestoreOffensiveCombatWeapons<T>` | method (private) | Restore the selected-weapons list for one offensive-combat attack-strategy component `T` (exact-type `Components.TryGet`). |

## MultigridProjectorApiProvider

*`public class MultigridProjectorApiProvider : IMultigridProjectorApi` in `MultigridProjector.Logic`.*

The single backing implementation of the projector API (see [Public-API.md](./Public-API.md) for the
`IMultigridProjectorApi` contract and the [../API.md](../API.md) usage guide). Every method resolves the
projection/subgrid for a projector id, checks `IsValidForApi`, and returns state through the locked
accessors. It also assembles the marshalled forms consumed by external mods and scripts: a delegate
array for the Mod API (mod message) and a `Delegate[]` published as a hidden `MgpApi` terminal property
for Programmable Blocks.

| Member | Kind | Description |
|--------|------|-------------|
| `Api` | property (static) | Lazy singleton `IMultigridProjectorApi`. |
| `Version` | property | API version string. |
| `GetSubgridCount` / `GetOriginalGridBuilders` | method | Subgrid count and the original blueprint builders. |
| `GetPreviewGrid` / `GetBuiltGrid` | method | Preview / built grid for a subgrid. |
| `GetBlockState` / `GetBlockStates` | method | Single block state, or a box+mask filtered set of states. |
| `GetBaseConnections` / `GetTopConnections` | method | Mechanical connection maps for a subgrid. |
| `GetScanNumber` / `GetStateHash` | method | Projection scan counter and per-subgrid state hash (change detection). |
| `GetYaml` | method | Full YAML dump of the projection. |
| `IsSubgridComplete` | method | Whether a subgrid is fully built. |
| `ModApi` | property (static) | `object[]` of version + delegates sent over `SendModMessage`. |
| `ModApiGetBlockState` / `ModApiGetBlockStates` / `ModApiGetBaseConnections` / `ModApiGetTopConnections` | method (static, private) | List/int-marshalled adapters for the Mod and PB APIs. |
| `WorkshopId` / `ModApiRequestId` / `ModApiResponseId` | const | Mod message channel ids. |
| `PbApi` | property (static) | `Delegate[]` exposed to Programmable Blocks. |
| `RegisterProgrammableBlockApi` | method (static) | Add the hidden `MgpApi` terminal property to PBs (server only). |

## MultigridProjectorSession

*`public class MultigridProjectorSession : IDisposable` in `MultigridProjector.Logic`.*

A lightweight session object created by the plugins. It owns a `Comms` instance, answers Mod API
requests by responding with `MultigridProjectorApiProvider.ModApi`, and lazily registers the
Programmable Block API once a PB appears in the world.

| Member | Kind | Description |
|--------|------|-------------|
| `MultigridProjectorSession()` | ctor | Create `Comms`, subscribe to entity-create, register the Mod API request handler. |
| `Dispose` | method | Unregister handlers and dispose `Comms`. |
| `OnEntityCreate` | method (private) | Notice when a programmable block first appears. |
| `Update` | method | Once a PB exists, register the PB API one time. |
| `HandleModApiRequest` | method (static, private) | Respond to a Mod API request with the `ModApi` payload. |

## FastBlockLocation

*`public readonly struct FastBlockLocation : IEquatable<FastBlockLocation>` in `MultigridProjector.Logic`.*

A `(GridIndex, Position)` value identifying a block by subgrid and blueprint position. Implements
`IEquatable` and a custom `GetHashCode` to avoid boxing when used as a dictionary key on hot paths.

| Member | Kind | Description |
|--------|------|-------------|
| `GridIndex` / `Position` | field | Subgrid index and block position. |
| `INVALID` | field (static) | Sentinel value (`GridIndex == -1`). |
| `FastBlockLocation(gridIndex, position)` | ctor | Construct the location. |
| `Equals` / `GetHashCode` / `ToString` | method | Value equality, boxing-free hash, `S{i}[x,y,z]` formatting. |

## BlockMinLocation

*`public readonly struct BlockMinLocation` in `MultigridProjector.Logic`.*

A `(GridIndex, MinPosition)` key used to identify mechanical blocks by their minimum cube position. It
is the key type of `BlueprintConnections`, `PreviewBaseBlocks` and `PreviewTopBlocks`, matching blueprint
and preview blocks across grids.

| Member | Kind | Description |
|--------|------|-------------|
| `GridIndex` / `MinPosition` | field | Subgrid index and minimum cube position. |
| `BlockMinLocation(gridIndex, minPosition)` | ctor | Construct the key. |
| `GetHashCode` | method | Custom hash for dictionary keys. |

## VisualState

*`public enum VisualState` in `MultigridProjector.Logic`.*

The preview rendering states a `ProjectedBlock` can be in. `ProjectedBlock.UpdateVisual` maps a
`BlockState` (and the show-only-buildable setting) to one of these and sets preview transparency
accordingly.

| Member | Kind | Description |
|--------|------|-------------|
| `None` | enum value | Uninitialized. |
| `Hidden` | enum value | Fully transparent / not shown (built or hidden). |
| `Hologram` | enum value | Semi-transparent hologram (not-buildable / mismatch). |
| `Transparent` | enum value | Lightly transparent (buildable). |
