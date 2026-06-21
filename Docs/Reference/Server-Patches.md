# Server Harmony Patches

Server-side Harmony patches applied exclusively by the Magnetar server plugin. They intercept `MyProjectorBase`, `MyShipWelder`, `MyProjectorClipboard`, and `MyMechanicalConnectionBlockBase` methods to replace or augment vanilla single-grid projection behaviour with the multi-subgrid logic implemented in the [Core Projection Engine](./Core-Projection-Engine.md).

All patches carry the `[ServerOnly]` attribute — they are never active on game clients. Where a conceptually equivalent client patch exists (see [Client-Patches.md](./Client-Patches.md)), the server version is **authoritative**: it actually creates blocks and mechanical tops, remaps entity IDs, and drives networking to clients. The vanilla handler is suppressed (Prefix returning `false`) wherever the plugin's own implementation covers the full responsibility.

## Files

| File | Lines | Patched target | Purpose |
|------|-------|----------------|---------|
| [MyProjectorBase_Init.cs](../../ServerPlugin/Patches/MyProjectorBase_Init.cs) | 38 | `MyProjectorBase.Init` | Postfix — bootstraps the `MultigridProjection` for the projector after vanilla init |
| [MyProjectorBase_InitializeClipboard.cs](../../ServerPlugin/Patches/MyProjectorBase_InitializeClipboard.cs) | 40 | `MyProjectorBase.InitializeClipboard` | Prefix — replaces vanilla clipboard init with the multigrid projection's own clipboard setup |
| [MyProjectorBase_RemoveProjection.cs](../../ServerPlugin/Patches/MyProjectorBase_RemoveProjection.cs) | 39 | `MyProjectorBase.RemoveProjection` | Prefix — delegates projection teardown to `MultigridProjection.RemoveProjection`, suppressing vanilla |
| [MyProjectorBase_Remap.cs](../../ServerPlugin/Patches/MyProjectorBase_Remap.cs) | 54 | `MyProjectorBase.Remap` | Prefix — replaces the vanilla entity-ID remapping with a consistent multigrid-safe remap; server-only patch with no client counterpart |
| [MyProjectorBase_Build.cs](../../ServerPlugin/Patches/MyProjectorBase_Build.cs) | 49 | `MyProjectorBase.Build` | Prefix — resolves the subgrid index from the preview grid and smuggles it into the `builtBy` parameter before `BuildInternal` is called |
| [MyProjectorBase_BuildInternal.cs](../../ServerPlugin/Patches/MyProjectorBase_BuildInternal.cs) | 73 | `MyProjectorBase.BuildInternal` | Transpiler — replaces the entire method body; dispatches to `MultigridProjection.BuildInternal` which actually places the block on the correct subgrid |
| [MyProjectorBase_CanBuild.cs](../../ServerPlugin/Patches/MyProjectorBase_CanBuild.cs) | 48 | `MyProjectorBase.CanBuild(MySlimBlock, bool)` | Prefix — delegates build-eligibility checks to `MultigridProjection.CanBuild`, accounting for cross-subgrid dependency ordering |
| [MyShipWelder_FindProjectedBlocks.cs](../../ServerPlugin/Patches/MyShipWelder_FindProjectedBlocks.cs) | 49 | `MyShipWelder.FindProjectedBlocks` | Prefix — replaces the vanilla welder scan with `MultigridProjection.FindProjectedBlocks` so welders see projected blocks across all subgrids |
| [MyProjectorBase_OnBlockAdded.cs](../../ServerPlugin/Patches/MyProjectorBase_OnBlockAdded.cs) | 39 | `MyProjectorBase.previewGrid_OnBlockAdded` | Prefix — suppresses the vanilla per-block-added handler; the `MultigridProjection` instance subscribes its own handler |
| [MyProjectorBase_OnBlockRemoved.cs](../../ServerPlugin/Patches/MyProjectorBase_OnBlockRemoved.cs) | 39 | `MyProjectorBase.previewGrid_OnBlockRemoved` | Prefix — suppresses the vanilla per-block-removed handler for the same reason |
| [MyProjectorBase_UpdateStats.cs](../../ServerPlugin/Patches/MyProjectorBase_UpdateStats.cs) | 39 | `MyProjectorBase.UpdateStats` | Prefix — replaces the single-grid stats calculation with `MultigridProjection.UpdateProjectorStats` that aggregates across all subgrids |
| [MyProjectorBase_UpdateAfterSimulation.cs](../../ServerPlugin/Patches/MyProjectorBase_UpdateAfterSimulation.cs) | 36 | `MyProjectorBase.UpdateAfterSimulation` | Prefix — drives the per-tick multigrid update loop; returns `false` to suppress vanilla update when the projection is managed |
| [MyProjectorBase_GetObjectBuilderCubeBlock.cs](../../ServerPlugin/Patches/MyProjectorBase_GetObjectBuilderCubeBlock.cs) | 36 | `MyProjectorBase.GetObjectBuilderCubeBlock` | Postfix — augments the serialised object builder with multigrid blueprint data so the projection survives save/load |
| [MyProjectorClipboard_UpdateGridTransformations.cs](../../ServerPlugin/Patches/MyProjectorClipboard_UpdateGridTransformations.cs) | 42 | `MyProjectorClipboard.UpdateGridTransformations` | Prefix — suppresses vanilla clipboard grid-transformation updates for managed projections; alignment is handled inside `UpdateAfterSimulation` instead |
| [MyMechanicalConnectionBlockBase_CreateTopPartAndAttach.cs](../../ServerPlugin/Patches/MyMechanicalConnectionBlockBase_CreateTopPartAndAttach.cs) | 41 | `MyMechanicalConnectionBlockBase.CreateTopPartAndAttach` | Prefix — intercepts mechanical-top creation on a built grid and routes it through `MultigridProjection.CreateTopPartAndAttach` to connect the correct projected subgrid |
| [MyMechanicalConnectionBlockBase_RaiseAttachedEntityChanged.cs](../../ServerPlugin/Patches/MyMechanicalConnectionBlockBase_RaiseAttachedEntityChanged.cs) | 36 | `MyMechanicalConnectionBlockBase.RaiseAttachedEntityChanged` | Postfix — notifies the active projection when a mechanical attachment changes so it can re-evaluate subgrid linkage |

## Patch groups

### Projector lifecycle

These patches manage the creation, configuration, and teardown of a `MultigridProjection` instance that shadows every active projector.

#### `MyProjectorBase.Init` — Postfix

After the vanilla projector has initialised from its object builder, `MultigridProjection.ProjectorInit(projector, objectBuilder)` is called. This is where the multigrid projection is constructed and registered against the projector entity. There is a direct client counterpart in [Client-Patches.md](./Client-Patches.md) that performs the same registration on the client side.

#### `MyProjectorBase.InitializeClipboard` — Prefix (suppresses original)

Calls `MultigridProjection.InitializeClipboard()` and returns `false` to block the vanilla single-grid clipboard setup. The multigrid clipboard must account for multiple preview grids and their relative transforms, so the vanilla path is entirely replaced.

#### `MyProjectorBase.RemoveProjection` — Prefix (suppresses original)

Calls `MultigridProjection.RemoveProjection(keepProjection)` and returns `false`. The multigrid teardown must clean up all preview subgrids; the vanilla method only handles a single grid and would leave orphaned preview entities.

#### `MyProjectorBase.Remap` — Prefix (suppresses original) — **server-only, no client counterpart**

Completely replaces the vanilla `Remap` implementation. The vanilla method uses `MyBlueprintIdTracker` to remap preview block entity IDs, but this breaks subgrid connection consistency when multiple grids share references. The patch instead calls `projector.RemapObjectBuilders()` followed by `projector.SetNewBlueprint(gridBuilders)`, achieving a consistent remap across all subgrids without `MyBlueprintIdTracker`. This patch has no equivalent in the client patches; the server is solely responsible for remapping.

---

### Build and weld

These patches intercept the build and welding pipeline so that block placement and welder scanning operate across all subgrids of the projection.

#### `MyProjectorBase.Build` — Prefix

Before `BuildInternal` is called, this Prefix resolves which subgrid the projected block belongs to via `MultigridProjection.TryFindPreviewGrid`. The resulting subgrid index is encoded into the `builtBy` parameter (normally a player ID) so `BuildInternal` can recover it without a separate lookup. This is a deliberate field-reuse trick documented in the code.

#### `MyProjectorBase.BuildInternal` — Transpiler (full replacement)

The entire method body is replaced by a redirect to a static `BuildInternal` replacement using IL emission. A Prefix is deliberately avoided here because patching multiplayer event-handler methods with a Prefix causes random null-dereference crashes before the Prefix even executes (a known Harmony limitation). The replacement reads the subgrid index from `builtBy`, looks up the relevant `MultigridProjection`, and calls `projection.BuildInternal(...)` which performs the authoritative server-side block placement on the correct subgrid.

#### `MyProjectorBase.CanBuild(MySlimBlock, bool)` — Prefix

Delegates to `MultigridProjection.CanBuild`, which understands cross-subgrid build ordering (a mechanical top cannot be projected until its base has been built). Returns `BuildCheckResult.NotWeldable` as the default when the projection is managed, letting the logic method supply the actual result.

#### `MyShipWelder.FindProjectedBlocks` — Prefix (suppresses original)

Replaces the vanilla welder proximity scan with `MultigridProjection.FindProjectedBlocks(welder, detectorSphere, weldedBlocks)`. The vanilla scan only searches the single preview grid attached to the projector; this replacement searches all subgrid preview grids, enabling welders to build every subgrid of a multi-part blueprint.

---

### Block events and statistics

These patches suppress vanilla per-event and per-tick handlers that only work for single-grid projections and replace them with multigrid-aware equivalents.

#### `MyProjectorBase.previewGrid_OnBlockAdded` — Prefix (suppresses original)

When a block is added to a preview grid, the vanilla handler updates the projector's internal state for the single grid it knows about. For multigrid projections the `MultigridProjection` instance subscribes its own event handlers directly on all preview grids, so the vanilla handler must be suppressed to avoid double-processing.

#### `MyProjectorBase.previewGrid_OnBlockRemoved` — Prefix (suppresses original)

Identical rationale to `OnBlockAdded` — the vanilla single-grid handler is suppressed and the `MultigridProjection` instance handles removal across all subgrids.

#### `MyProjectorBase.UpdateStats` — Prefix (suppresses original)

Replaces the vanilla statistics calculation (remaining blocks, build progress) with `MultigridProjection.UpdateProjectorStats()`, which aggregates counts across all subgrids.

#### `MyProjectorBase.UpdateAfterSimulation` — Prefix (conditionally suppresses original)

Called every simulation tick. Delegates to `MultigridProjection.ProjectorUpdateAfterSimulation(projector)`, which drives alignment, state transitions, and stats updates for all subgrids. Returns `false` (suppressing vanilla) when the projection is managed, `true` otherwise. Grid transformation alignment is performed here rather than in `UpdateGridTransformations` (see Misc section below).

---

### Mechanical connections

These patches handle the creation and attachment of mechanical top parts (pistons, rotors, hinges) that link subgrids to each other.

#### `MyMechanicalConnectionBlockBase.CreateTopPartAndAttach` — Prefix (conditionally suppresses original)

When a mechanical base block (rotor base, piston base, hinge) on a **built** grid attempts to create its top part, this Prefix checks whether the grid belongs to an active multigrid projection via `MultigridProjection.TryFindProjectionByBuiltGrid`. If it does, `projection.CreateTopPartAndAttach(subgrid, baseBlock)` is called, which places and attaches the correct projected top-part subgrid rather than spawning a new default top. Returning `false` suppresses the vanilla top-creation path. If the grid is not part of a managed projection the vanilla path runs unchanged.

#### `MyMechanicalConnectionBlockBase.RaiseAttachedEntityChanged` — Postfix

After the vanilla method fires the attachment-changed event (e.g. after a rotor or piston top connects), this Postfix locates any active projection that owns the base block's grid and calls `projection.RaiseAttachedEntityChanged()`. This allows the projection engine to re-evaluate subgrid linkage and trigger follow-up logic such as updating build states for dependent subgrids.

---

### Miscellaneous

#### `MyProjectorBase.GetObjectBuilderCubeBlock` — Postfix

After the projector's object builder is serialised (for save-game or clipboard copy), this Postfix calls `MultigridProjection.GetObjectBuilderOfProjector(__instance, copy, __result)` to inject the multigrid blueprint data into the resulting object builder. Without this, only the first (base) grid blueprint would be persisted and the rest of the projection would be lost on reload.

#### `MyProjectorClipboard.UpdateGridTransformations` — Prefix (suppresses original)

The vanilla clipboard calls `UpdateGridTransformations` every tick to move preview grids into alignment with the projector. For multigrid projections this is suppressed entirely because alignment for all subgrids is handled inside the `UpdateAfterSimulation` patch, which has full knowledge of the relative transforms between subgrids. Running both would cause conflicts or redundant transform updates.

---

## Cross-references

- [Core-Projection-Engine.md](./Core-Projection-Engine.md) — `MultigridProjection` class that all patches delegate to.
- [Client-Patches.md](./Client-Patches.md) — Client-side counterparts; most lifecycle and stats patches mirror each other, but build/weld/mechanical patches are server-authoritative only.
- [Server-Plugin.md](./Server-Plugin.md) — Plugin entry point that registers these patches with Harmony at startup.
