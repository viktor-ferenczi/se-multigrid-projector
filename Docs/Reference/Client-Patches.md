# Client Harmony Patches

The `ClientPlugin/Patches` directory contains all Harmony patches that are applied exclusively inside the game client (loaded by Pulsar). Their primary role is to intercept the vanilla projector, welder, blueprint-screen, and mechanical-connection code paths and redirect them through the multigrid engine in `MultigridProjection` (see [Core-Projection-Engine.md](./Core-Projection-Engine.md)). Most patches follow a simple guard pattern: call `MultigridProjection.TryFindProjectionByProjector` (or the equivalent grid-based lookup), delegate to the engine method, and return `false` to suppress the original implementation. Patches that are not applicable to the current projector fall through by returning `true`, preserving vanilla behaviour. A secondary role is adding client-side terminal controls, toolbar actions, and blueprint-screen normalization that have no server counterpart.

---

## Files

| File | Lines | Patched target | Purpose |
|------|------:|----------------|---------|
| [MySpaceProjector_CreateTerminalControls.cs](../../ClientPlugin/Patches/MySpaceProjector_CreateTerminalControls.cs) | 122 | `MySpaceProjector.CreateTerminalControls` | Injects custom terminal controls and toolbar actions; removes vanilla block-marker controls |
| [MyProjectorBase_BuildInternal.cs](../../ClientPlugin/Patches/MyProjectorBase_BuildInternal.cs) | 81 | `MyProjectorBase.BuildInternal` | Replaces entire body to call `MultigridProjection.BuildInternal`, encoding subgrid index via `builtBy` |
| [MyGuiBlueprintScreenPatches.cs](../../ClientPlugin/Patches/MyGuiBlueprintScreenPatches.cs) | 70 | `MyGuiBlueprintScreen_Reworked.CreateBlueprintFromClipboard`, `MyBlueprintUtils.SavePrefabToFile` | Normalises blueprint world position and aligns grid to repair projector before saving |
| [MyProjectorBase_InitFromObjectBuilder.cs](../../ClientPlugin/Patches/MyProjectorBase_InitFromObjectBuilder.cs) | 63 | `MyProjectorBase.InitFromObjectBuilder` | Delegates to `MultigridProjection.InitFromObjectBuilder`; shows unsupported/client-weld dialog when server lacks plugin |
| [MyProjectorBase_SetNewBlueprint.cs](../../ClientPlugin/Patches/MyProjectorBase_SetNewBlueprint.cs) | 59 | `MyProjectorBase.Remap` | Replaces Remap with a safe remapping sequence that preserves subgrid entity-ID consistency |
| [MyShipWelder_FindProjectedBlocks.cs](../../ClientPlugin/Patches/MyShipWelder_FindProjectedBlocks.cs) | 53 | `MyShipWelder.FindProjectedBlocks` | Fully replaces ship-welder block search with `MultigridProjection.FindProjectedBlocks` |
| [MyProjectorBase_CanBuild.cs](../../ClientPlugin/Patches/MyProjectorBase_CanBuild.cs) | 52 | `MyProjectorBase.CanBuild(MySlimBlock, bool)` | Delegates build-eligibility check to `MultigridProjection.CanBuild`; falls back to original for non-multigrid projectors |
| [MyWelder_FindProjectedBlock.cs](../../ClientPlugin/Patches/MyWelder_FindProjectedBlock.cs) | 47 | `MyWelder.FindProjectedBlock` | Replaces hand-welder raycast block search with `MultigridProjection.MyWelder_FindProjectedBlock` |
| [MyProjectorBase_InitializeClipboard.cs](../../ClientPlugin/Patches/MyProjectorBase_InitializeClipboard.cs) | 44 | `MyProjectorBase.InitializeClipboard` | Delegates clipboard initialisation to `MultigridProjection.InitializeClipboard` |
| [MyProjectorBase_UpdateStats.cs](../../ClientPlugin/Patches/MyProjectorBase_UpdateStats.cs) | 43 | `MyProjectorBase.UpdateStats` | Replaces vanilla stats update with `MultigridProjection.UpdateProjectorStats` (aggregates across all subgrids) |
| [MyProjectorBase_RemoveProjection.cs](../../ClientPlugin/Patches/MyProjectorBase_RemoveProjection.cs) | 43 | `MyProjectorBase.RemoveProjection` | Delegates projection teardown to `MultigridProjection.RemoveProjection`; suppresses original |
| [MyProjectorBase_Build.cs](../../ClientPlugin/Patches/MyProjectorBase_Build.cs) | 42 | `MyProjectorBase.Build` | Redirects weld-block call through `Construction.WeldBlock` to route to the correct subgrid |
| [MyMechanicalConnectionBlockBase_CreateTopPartAndAttach.cs](../../ClientPlugin/Patches/MyMechanicalConnectionBlockBase_CreateTopPartAndAttach.cs) | 40 | `MyMechanicalConnectionBlockBase.CreateTopPartAndAttach` | Intercepts top-part creation so the engine can attach mechanical parts to the projected subgrid |
| [MyMechanicalConnectionBlockBase_RaiseAttachedEntityChanged.cs](../../ClientPlugin/Patches/MyMechanicalConnectionBlockBase_RaiseAttachedEntityChanged.cs) | 40 | `MyMechanicalConnectionBlockBase.RaiseAttachedEntityChanged` | Postfix: notifies `MultigridProjection.RaiseAttachedEntityChanged` when a mechanical attachment changes |
| [MyProjectorBase_Init.cs](../../ClientPlugin/Patches/MyProjectorBase_Init.cs) | 40 | `MyProjectorBase.Init` | Postfix: calls `MultigridProjection.ProjectorInit` after the projector entity is initialised |
| [MyProjectorBase_GetObjectBuilderCubeBlock.cs](../../ClientPlugin/Patches/MyProjectorBase_GetObjectBuilderCubeBlock.cs) | 40 | `MyProjectorBase.GetObjectBuilderCubeBlock` | Postfix: serialises multigrid projection state into the returned object builder |
| [MyProjectorBase_UpdateAfterSimulation.cs](../../ClientPlugin/Patches/MyProjectorBase_UpdateAfterSimulation.cs) | 39 | `MyProjectorBase.UpdateAfterSimulation` | Replaces per-tick update with `MultigridProjection.ProjectorUpdateAfterSimulation` |
| [MyProjectorClipboard_UpdateGridTransformations.cs](../../ClientPlugin/Patches/MyProjectorClipboard_UpdateGridTransformations.cs) | 33 | `MyProjectorClipboard.UpdateGridTransformations` | Suppresses vanilla clipboard transform update; alignment is handled inside `UpdateAfterSimulation` instead |
| [MyProjectorBase_OnBlockAdded.cs](../../ClientPlugin/Patches/MyProjectorBase_OnBlockAdded.cs) | 32 | `MyProjectorBase.previewGrid_OnBlockAdded` | Suppresses the vanilla handler; `MultigridProjection` subscribes its own listener |
| [MyProjectorBase_OnBlockRemoved.cs](../../ClientPlugin/Patches/MyProjectorBase_OnBlockRemoved.cs) | 32 | `MyProjectorBase.previewGrid_OnBlockRemoved` | Suppresses the vanilla handler; `MultigridProjection` subscribes its own listener |
| [MyProjectorBlockMarker_Constructor.cs](../../ClientPlugin/Patches/MyProjectorBlockMarker_Constructor.cs) | 29 | `MyProjectorBase.MyProjectorBlockMarker..ctor(int, int)` | Forces `maxMissingBlocks` and `maxUnfinishedBlocks` to zero, disabling Keen's built-in block highlighting |
| [MyProjectorBase_UpdateProjection.cs](../../ClientPlugin/Patches/MyProjectorBase_UpdateProjection.cs) | 29 | `MyProjectorBase.UpdateProjection` | Suppresses vanilla `ProjectorUpdateWork` for welding projectors; allows console-projector paths through |

---

## Patch groups

### Projector lifecycle

These patches manage the full lifetime of a `MyProjectorBase` entity from construction through teardown.

#### `MyProjectorBase_Init`
- **Target:** `MyProjectorBase.Init(MyObjectBuilder_CubeBlock)`
- **Kind:** Postfix
- Calls `MultigridProjection.ProjectorInit` after vanilla Init completes, letting the engine register the projector and prepare subgrid tracking structures.

#### `MyProjectorBase_InitFromObjectBuilder`
- **Target:** `MyProjectorBase.InitFromObjectBuilder(List<MyObjectBuilder_CubeGrid>)`
- **Kind:** Prefix (client-only)
- Delegates to `MultigridProjection.InitFromObjectBuilder`. If the server does not have the plugin and the player has client-side welding enabled, shows an informational dialog; otherwise shows an unsupported dialog.

#### `MyProjectorBase_SetNewBlueprint`
- **Target:** `MyProjectorBase.Remap`
- **Kind:** Prefix (client-only, server path only)
- Completely replaces the Remap handler: calls `projector.RemapObjectBuilders()` followed by `projector.SetNewBlueprint(gridBuilders)`, avoiding the vanilla remapping that corrupts subgrid entity-ID consistency. Returns `false` to always suppress the original.

#### `MyProjectorBase_InitializeClipboard`
- **Target:** `MyProjectorBase.InitializeClipboard`
- **Kind:** Prefix (client-only)
- Calls `projection.InitializeClipboard()` and suppresses the original so that the engine sets up the multi-clipboard covering all subgrid preview meshes.

#### `MyProjectorBase_RemoveProjection`
- **Target:** `MyProjectorBase.RemoveProjection(bool keepProjection)`
- **Kind:** Prefix (client-only)
- Delegates to `projection.RemoveProjection(keepProjection)` and always returns `false` to suppress the original, ensuring all subgrid preview grids and listeners are cleaned up.

---

### Build and weld

These patches intercept every code path that triggers block construction or welder block scanning.

#### `MyProjectorBase_Build`
- **Target:** `MyProjectorBase.Build(MySlimBlock, long, ref long)`
- **Kind:** Prefix (client-only)
- Routes through `Construction.WeldBlock`, which encodes the subgrid index into the `builtBy` field before forwarding the build request. This is the entry point for player-triggered welding.

#### `MyProjectorBase_BuildInternal`
- **Target:** `MyProjectorBase.BuildInternal(Vector3I, long, long, bool, long)`
- **Kind:** Transpiler — replaces the entire method body with a call to `MyProjectorBase_BuildInternal.BuildInternal` (server-only path)
- Implemented as a Transpiler rather than a Prefix to avoid a Harmony crash that occurs when patching multiplayer event handlers with a Prefix. Decodes the subgrid index from `builtBy` and calls `projection.BuildInternal`.

#### `MyProjectorBase_CanBuild`
- **Target:** `MyProjectorBase.CanBuild(MySlimBlock, bool)`
- **Kind:** Prefix (client-only)
- Calls `projection.CanBuild(projectedBlock, checkHavokIntersections, out var fallback)`. Returns the engine's `fallback` flag so vanilla logic is invoked when the engine cannot make a determination.

#### `MyShipWelder_FindProjectedBlocks`
- **Target:** `MyShipWelder.FindProjectedBlocks`
- **Kind:** Prefix (server-only)
- Completely replaces the ship-welder projected-block search with `MultigridProjection.FindProjectedBlocks`, which scans all subgrid preview meshes within the welder's detector sphere.

#### `MyWelder_FindProjectedBlock`
- **Target:** `MyWelder.FindProjectedBlock`
- **Kind:** Prefix (client-only)
- Replaces the hand-welder raycast logic with `MultigridProjection.MyWelder_FindProjectedBlock`, enabling hand welders to target blocks on any subgrid.

---

### Block events and simulation stats

These patches keep the engine's internal state and the projector's stat counters consistent with the live projection.

#### `MyProjectorBase_OnBlockAdded`
- **Target:** `MyProjectorBase.previewGrid_OnBlockAdded`
- **Kind:** Prefix (server-only)
- Returns `false` for multigrid projectors, suppressing the vanilla handler. The engine registers its own `OnBlockAdded` listeners for every subgrid preview.

#### `MyProjectorBase_OnBlockRemoved`
- **Target:** `MyProjectorBase.previewGrid_OnBlockRemoved`
- **Kind:** Prefix (server-only)
- Mirror of `OnBlockAdded`: suppresses the vanilla handler so the engine's own listeners are the sole owners of block-removal tracking.

#### `MyProjectorBase_UpdateStats`
- **Target:** `MyProjectorBase.UpdateStats`
- **Kind:** Prefix (client-only)
- Calls `projection.UpdateProjectorStats()`, which aggregates remaining/built/total block counts across all subgrids, and suppresses the original single-grid stats update.

#### `MyProjectorBase_UpdateProjection`
- **Target:** `MyProjectorBase.UpdateProjection`
- **Kind:** Prefix (no role annotation — applies to both)
- Suppresses the vanilla `ProjectorUpdateWork` path for welding projectors (`AllowWelding == true && AllowScaling == false`). Console projectors (scaling allowed) continue to use the original code path.

#### `MyProjectorBase_UpdateAfterSimulation`
- **Target:** `MyProjectorBase.UpdateAfterSimulation`
- **Kind:** Prefix (client-only)
- Calls `MultigridProjection.ProjectorUpdateAfterSimulation(projector)`, which drives preview-grid alignment, subgrid transform updates, and any per-tick engine housekeeping. Returns `false` to suppress the original.

---

### Mechanical connections

These patches ensure that piston/rotor top-parts and their attachment events are wired through the engine rather than vanilla logic.

#### `MyMechanicalConnectionBlockBase_CreateTopPartAndAttach`
- **Target:** `MyMechanicalConnectionBlockBase.CreateTopPartAndAttach`
- **Kind:** Prefix (server-only)
- Looks up the projection by the base block's grid. If found, delegates to `projection.CreateTopPartAndAttach(subgrid, baseBlock)` and returns the engine's bool result. Vanilla code runs only when no projection is registered for that grid.

#### `MyMechanicalConnectionBlockBase_RaiseAttachedEntityChanged`
- **Target:** `MyMechanicalConnectionBlockBase.RaiseAttachedEntityChanged`
- **Kind:** Postfix (client-only)
- Calls `projection.RaiseAttachedEntityChanged()` after the vanilla event fires, allowing the engine to re-evaluate subgrid linkage whenever a mechanical connection changes.

---

### Terminal UI and blueprint screen

These patches add or remove terminal controls on the projector block and normalise blueprint files created from the clipboard.

#### `MySpaceProjector_CreateTerminalControls`
- **Target:** `MySpaceProjector.CreateTerminalControls`
- **Kind:** Transpiler
- Removes the vanilla `MarkMissingBlocks` and `MarkUnfinishedBlocks` controls from the IL stream (replaced by the plugin's block-highlight system). Inserts calls to `CreateControls()` and `CreateActions()` just before the final `ret`, which inject controls from `BlockHighlight`, `ApplyPaint`, `RepairProjection`, `ProjectorAligner`, `CraftProjection`, `ToolbarFix`, and toolbar actions from `BlockHighlight`/`ProjectorAligner`. Controls are added idempotently using reference-control IDs for positioning.

#### `MyGuiBlueprintScreenPatches`
- **Target:** `MyGuiBlueprintScreen_Reworked.CreateBlueprintFromClipboard` (Prefix + Postfix) and `MyBlueprintUtils.SavePrefabToFile` (Prefix)
- **Kind:** Prefix/Postfix pair + Prefix
- Wraps `CreateBlueprintFromClipboard` with a flag so that any `SavePrefabToFile` call it triggers is intercepted. On matching saves (replace or from-clipboard), calls `AlignToRepairProjector(null)` and `CensorWorldPosition()` on the blueprint grids to strip absolute world coordinates and align to repair projection origin.

---

### Miscellaneous

#### `MyProjectorBase_GetObjectBuilderCubeBlock`
- **Target:** `MyProjectorBase.GetObjectBuilderCubeBlock(bool)`
- **Kind:** Postfix (client-only)
- Calls `MultigridProjection.GetObjectBuilderOfProjector(__instance, copy, __result)` to inject multigrid-specific fields (e.g., sub-blueprint references) into the serialised block builder returned to the game.

#### `MyProjectorClipboard_UpdateGridTransformations`
- **Target:** `MyProjectorClipboard.UpdateGridTransformations`
- **Kind:** Prefix (client-only)
- Returns `false` for all multigrid projectors, suppressing the vanilla single-grid clipboard transform tick. Preview-grid alignment for all subgrids is instead driven from `UpdateAfterSimulation`.

#### `MyProjectorBlockMarker_Constructor`
- **Target:** `MyProjectorBase.MyProjectorBlockMarker..ctor(int, int)`
- **Kind:** Prefix
- Zeroes `maxMissingBlocks` and `maxUnfinishedBlocks` before the constructor runs, disabling Keen's built-in coloured block-marker system. The plugin supplies its own `BlockHighlight` highlighting instead.

---

## Cross-references

- [Core-Projection-Engine.md](./Core-Projection-Engine.md) — `MultigridProjection` methods that most patches delegate to.
- [Server-Patches.md](./Server-Patches.md) — counterpart Harmony patches applied on the dedicated server.
- [Client-Features.md](./Client-Features.md) — extra client-side features (BlockHighlight, ApplyPaint, RepairProjection, ProjectorAligner, CraftProjection) whose controls are injected by `MySpaceProjector_CreateTerminalControls`.
- [Client-Utilities.md](./Client-Utilities.md) — `Construction.WeldBlock` and other utilities called by build/weld patches.
