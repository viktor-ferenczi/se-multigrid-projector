# Client Extra Features

The files under `ClientPlugin/Extra/` implement the user-facing quality-of-life features of the Multigrid Projector client plugin. Each feature is an independent static class that contributes terminal controls and/or toolbar actions to the `MySpaceProjector` block via the `MySpaceProjector_CreateTerminalControls` transpiler patch (see [Client-Patches.md](./Client-Patches.md)). Features that involve per-frame work register with `PluginSession`'s update loop. Every feature is individually gated by a `bool` property in [Client-Plugin.md](./Client-Plugin.md) (`Config.Current.*`). Dialogs presented to the player are defined in [Client-Menus.md](./Client-Menus.md).

---

## Files

| File | Lines | Feature | Purpose |
|------|-------|---------|---------|
| [ConnectSubgrids.cs](../../ClientPlugin/Extra/ConnectSubgrids.cs) | 404 | Connect Subgrids | Automatically reconcile mechanical head/top parts when welding subgrid connections |
| [CraftProjection.cs](../../ClientPlugin/Extra/CraftProjection.cs) | 321 | Assemble Projection | Compute and display a Bill-of-Materials for the active projection; queue components in an assembler |
| [ProjectorAligner.cs](../../ClientPlugin/Extra/ProjectorAligner.cs) | 300 | Projector Aligner | Interactively move and rotate a projection using block-placement keys |
| [BlockHighlight.cs](../../ClientPlugin/Extra/BlockHighlight.cs) | 243 | Block Highlight | Draw color-coded wireframe overlays on projected blocks to show their build/weld status |
| [ShipWelding.cs](../../ClientPlugin/Extra/ShipWelding.cs) | 150 | Ship Welding | Drive ship-mounted welders to place projected blocks while the player pilots the craft |
| [ApplyPaint.cs](../../ClientPlugin/Extra/ApplyPaint.cs) | 63 | Apply Paint | Copy color and armor skin from the blueprint's preview blocks onto their already-built counterparts |
| [RepairProjection.cs](../../ClientPlugin/Extra/RepairProjection.cs) | 58 | Repair Projection | Load the projector's own mechanical group as a repair blueprint without leaving the cockpit |
| [ToolbarFix.cs](../../ClientPlugin/Extra/ToolbarFix.cs) | 51 | Fix All Toolbars | Merge toolbar slots and fix block relations from the repair projection onto the live grid |

---

## ConnectSubgrids

*`static class ConnectSubgrids` — `MultigridProjectorClient.Extra`*

**Player perspective.** When the `Connect Subgrids` feature is enabled (`Config.Current.ConnectSubgrids`) and a player welds a mechanical base block (rotor, hinge, piston), the plugin automatically reconciles the head/top part so that the welded connection matches what the blueprint specifies. This covers four scenarios encoded in `ConnectionType`:

- `Default` — the head is already correct; only paint/skin is copied.
- `SmallDefault` — the auto-spawned large head is ground and a small head is re-created via `RecreateTop()`.
- `Special` — the existing head is ground; the correct head type is spawned nearby via `Construction.SpawnBlockOnGrid`, then attached with `CallAttach()`.
- `Legacy` — the connection cannot be recreated in survival; a warning message is shown.
- `None` — no top part exists; nothing to do.

**Technical.** `ConnectSubgrids` is called by [Client-Utilities.md](./Client-Utilities.md) `Construction` at weld time (not at frame update). It does not register any terminal control. It uses `MultigridProjection.TryFindProjectionByProjector` / `TryFindProjectionByBuiltGrid` to locate the [Core-Projection-Engine.md](./Core-Projection-Engine.md) projection context, then navigates `Subgrid.BaseConnections` and `TopConnections` to find the matching preview block. Block placement uses a binary-search offset algorithm (`GetClosestPlaceableMatrix`) to find a non-intersecting spawn position. Events (`Events.OnBlockSpawned`, `Events.OnNextAttachedChanged`) chain the attach/skin steps asynchronously.

**Config toggle.** `Config.Current.ConnectSubgrids` (label "Connect Subgrids"). No terminal button — invoked internally by `Construction`.

| Member | Kind | Description |
|--------|------|-------------|
| `ConnectionType` | `enum` | Classifies how a base↔top connection must be reconstructed: `Default`, `SmallDefault`, `Special`, `Legacy`, `None` |
| `TryGetSubgrid(MySlimBlock, out Subgrid)` | `static bool` | Looks up the `Subgrid` for a slim block (preview or built), forwarding to the two-output overload |
| `TryGetSubgrid(MySlimBlock, out Subgrid, out MultigridProjection)` | `static bool` | Full overload; resolves via projector or built-grid lookup |
| `GetTopPart(MyMechanicalConnectionBlockBase)` | `static MyAttachableTopBlockBase` | Returns the preview top part for a projected base, navigating `BaseConnections` |
| `GetBasePart(MyAttachableTopBlockBase)` | `static MyMechanicalConnectionBlockBase` | Returns the preview base for a projected top part, navigating `TopConnections` |
| `SkinTopParts(sourceTop, destinationTop)` | `static void` | Copies HSV color and armor skin from source top to destination top via `SkinBlocks` |
| `UpdateTopParts(sourceBase, destinationBase)` | `static void` | Reconciles the top part of a destination base to match the source base's blueprint, grinding/replacing as needed |
| `UpdateBaseParts(sourceTop, destinationTop)` | `static void` | Places a missing base part near the top part and copies block properties; shows user guidance when manual intervention is needed |
| `AnalyzeConnection(baseDefinition, topDefinition)` | `static ConnectionType` | Classifies the head combination by comparing subtype sizes against the definition group |

---

## CraftProjection

*`static class CraftProjection` — `MultigridProjectorClient.Extra`*

**Player perspective.** When enabled (`Config.Current.CraftProjection`, label "Assemble Projections"), an **"Assemble Projection"** button appears in the projector terminal after the "Blueprint" control. Clicking it opens the [CraftDialog](./Client-Menus.md) showing a three-column table: components needed to manufacture (required), already available in the grid's inventories and player's suit, and the full blueprint total. From the dialog the player can queue individual rows into the currently selected assembler, copy the full Bill-of-Materials to clipboard, or switch to the Production terminal tab.

**Technical.** `CraftProjection` contributes one `MyTerminalControlButton<MySpaceProjector>` via `IterControls()`. `GetBlueprintComponents` walks the `MultigridProjection` subgrid array (or, for Console Blocks, the logically-connected grid set) and sums component counts from `MyComponentStack.GetGroupInfo`, subtracting partial progress of already-built counterparts found via `Construction.GetBuiltBlock`. `GetInventoryComponents` scans all mechanically-linked grids plus the local character's inventory. The dialog callback calls `assembler.AddQueueItemRequest` for each missing item. The assembler reference is retrieved from the already-open production tab via `MyGuiScreenTerminal.m_instance.m_controllerProduction.m_selectedAssembler`.

**Config toggle.** `Config.Current.CraftProjection`. **Dialog.** [CraftDialog](./Client-Menus.md).

| Member | Kind | Description |
|--------|------|-------------|
| `IterControls()` | `static IEnumerable<CustomControl>` | Yields the "Assemble Projection" terminal button, placed after "Blueprint" |
| `ClampComponents(ref Dictionary<MyDefinitionId,int>)` | `static void` | Clamps all negative component counts to zero (public helper, used after subtraction) |
| `SwitchToProductionTab()` | `static void` | Switches the terminal UI to the Production page |

---

## ProjectorAligner

*`class ProjectorAligner : IDisposable` — `MultigridProjectorClient.Extra`*

**Player perspective.** When enabled (`Config.Current.ProjectorAligner`, label "Align Projection"), an **"Align Projection"** button appears in the projector terminal after "Blueprint". Clicking it closes the terminal and enters an interactive alignment mode where the projection can be nudged (WASD/jump/crouch) and rotated (cube-rotate keys) using the same controls as block placement. The player-facing direction is used to transform key input to projector-local axes. Holding Sprint suspends the mode temporarily without cancelling it. Pressing Escape or opening chat cancels alignment. A toolbar action `ProjectorAlignerStart` is also registered for button-panel use.

**Technical.** Three Harmony patches intercept game-input handlers:
- `MyGuiScreenGamePlay_HandleUnhandledInput` — `Prefix` returns `false` (skips original) when the aligner is active, routing input to `ProjectorAligner.Instance.HandleInput()` instead.
- `MyCubeBuilder_HandleGameInput` and `MyClipboardComponent_HandleGameInput` — `Prefix` sets `MyGuiScreenGamePlay.DisableInput = true` when active, suppressing block-builder input.

`HandleInput` maps movement/rotation keys to projector-relative offsets using `Base6Directions` and quaternion rotation algebra (`OrientationAlgebra.ProjectionRotationFromForwardAndUp`). `UpdateOffsetAndRotation` writes `projector.ProjectionOffset` and `projector.ProjectionRotation` and calls `projector.UpdateOffsetAndRotation()`. Console Block projectors scale rotation values by 90°. The singleton `Instance` is created by `Initialize()` (called from plugin startup) and implements `IDisposable` to release the active projector reference cleanly.

**Config toggle.** `Config.Current.ProjectorAligner`. **Dialog.** [AlignerDialog](./Client-Menus.md) (shown when `Config.Current.ShowDialogs` is true).

| Member | Kind | Description |
|--------|------|-------------|
| `Instance` | `static ProjectorAligner` | Singleton created by `Initialize()`; patched input handlers reference this |
| `Active` | `bool` (property) | True when a projector is assigned and the Sprint key (suspend key) is not held |
| `Initialize()` | `static void` | Creates the singleton instance |
| `IterControls()` | `static IEnumerable<CustomControl>` | Yields the "Align Projection" terminal button |
| `IterActions()` | `static IEnumerable<IMyTerminalAction>` | Yields the `ProjectorAlignerStart` toolbar action |
| `HandleInput()` | `void` | Per-frame method called by the input patch; processes movement/rotation keys and cancellation |
| `Dispose()` | `void` | Calls `Release()` to clear the active projector reference |

---

## BlockHighlight

*`static class BlockHighlight` — `MultigridProjectorClient.Extra`*

**Player perspective.** When enabled (`Config.Current.BlockHighlight`, label "Highlight Blocks"), a **"Highlight Blocks"** checkbox appears in the projector terminal. Enabling it draws colored wireframe boxes around every projected block within 500 m of the camera, updated each game tick:

| Color | Meaning |
|-------|---------|
| Green | Can be built (`BuildCheckResult.OK`) |
| Yellow | Already placed but not fully welded (`BeingBuilt`) |
| Cyan | Obstructed by a non-grid entity |
| Crimson | Obstructed by another grid block |
| No highlight | Fully built, not connected, or not found |

Three toolbar actions are also registered: `BlockHighlightToggle`, `BlockHighlightEnable`, `BlockHighlightDisable`.

**Technical.** A static `HashSet<MyProjectorBase> TargetProjectors` tracks which projectors have highlighting active. `PluginSession` calls `BlockHighlight.HighlightLoop()` every frame when `Config.Current.BlockHighlight` is true. The loop iterates `projection.GetSupportedSubgrids()`, reads each `ProjectedBlock.BuildCheckResult` and `BlockState` under a read lock (`subgrid.BlocksLock.Read()`), then calls `WireFrame` which uses `MySimpleObjectDraw.DrawTransparentBox` with `MySimpleObjectRasterizer.Wireframe` and `MyBillboard.BlendTypeEnum.AdditiveTop`. Enabling highlighting also sets `projection.CheckHavokIntersections = true` so that entity-intersection detection runs in the [Core-Projection-Engine.md](./Core-Projection-Engine.md).

**Config toggle.** `Config.Current.BlockHighlight`.

| Member | Kind | Description |
|--------|------|-------------|
| `IterControls()` | `static IEnumerable<CustomControl>` | Yields the "Highlight Blocks" checkbox, placed after "ShowOnlyBuildable" |
| `IterActions()` | `static IEnumerable<IMyTerminalAction>` | Yields Toggle / Enable / Disable toolbar actions |
| `HighlightLoop()` | `static void` | Per-frame update called from `PluginSession`; renders wireframe overlays for all tracked projectors |

---

## ShipWelding

*`internal static class ShipWelding` — `MultigridProjectorClient.Extra`*

**Player perspective.** When enabled (`Config.Current.ShipWelding`, label "Ship Welding"), ship-mounted welders on the grid (and all mechanically linked subgrids) of the craft the player is currently piloting will automatically place projected blocks — no server plugin required. This extends the client-welding logic to automated welders.

**Technical.** `PluginSession` calls `ShipWelding.WeldLoop()` every frame when `Config.Current.ShipWelding` is true. `WeldLoop` locates the pilot's `MyShipController`, collects all `MyShipWelder` blocks on the mechanical group, then for each welder queries projected blocks inside its `DetectorSphere` using `MyEntities.GetEntitiesInSphere`. For each weldable block (`CanBuild == OK`) it calls `TryWeldPreviewBlock`, which:

1. Checks that the welder's conveyor system can pull the first component of the block (`GridConveyorSystem.PullItem`); if successful the item is consumed in-place.
2. Validates world limits via `welder.IsWithinWorldLimits`.
3. Calls `projector.Build(block, welder.OwnerId, welder.EntityId, builtBy: welder.BuiltBy)` to place the block server-side.

`ConnectSubgrids.TryGetSubgrid` is used to confirm the block belongs to a supported subgrid before attempting the build.

**Config toggle.** `Config.Current.ShipWelding`. No terminal control — purely background loop.

| Member | Kind | Description |
|--------|------|-------------|
| `WeldLoop()` | `static void` | Per-frame update called from `PluginSession`; drives all welders on the piloted craft |

---

## ApplyPaint

*`public static class ApplyPaint` — `MultigridProjectorClient.Extra`*

**Player perspective.** An **"Apply Paint"** button appears in the projector terminal before "Blueprint" whenever a working projector has an active projection. Clicking it instantly copies the color (HSV) and armor skin from every preview block in the blueprint onto its matching built counterpart, for all subgrids. No config toggle gates this feature — it is always visible when the projector is working.

**Technical.** `IterControls()` yields one `MyTerminalControlButton<MySpaceProjector>`. `ApplyPaintFromProjection` iterates `projection.GetSupportedSubgrids()`, skips subgrids with no built grid, and for each `ProjectedBlock` where the built block's `ColorMaskHSV` or `SkinSubtypeId` differs from the preview block, calls `builtGrid.SkinBlocks(builtPosition, builtPosition, ...)` after translating the preview-grid position to built-grid coordinates via `subgrid.PreviewToBuiltBlockPosition`.

**Config toggle.** None — always visible for working projectors. No hotkey.

| Member | Kind | Description |
|--------|------|-------------|
| `IterControls()` | `static IEnumerable<CustomControl>` | Yields the "Apply Paint" terminal button, placed before "Blueprint" |

---

## RepairProjection

*`static class RepairProjection` — `MultigridProjectorClient.Extra`*

**Player perspective.** When enabled (`Config.Current.RepairProjection`, label "Repair Projection"), a **"Load Repair Projection"** button appears in the projector terminal before "Blueprint". It is active only when the projector is working but not yet projecting. Clicking it snapshots the projector's own mechanical group as a multigrid blueprint and loads it directly into the projector — no blueprint file required. `KeepProjection` is forced on so the projection persists even after full completion. See [ProjectionDialog](./Client-Menus.md) for the dialog shown to new users.

**Technical.** `LoadMechanicalGroup` calls `projector.GetFocusedGridsInMechanicalGroup()` to get all grids in the mechanical group, serialises each via `grid.GetObjectBuilder()` to `MyObjectBuilder_CubeGrid`, then passes the list to `MultigridProjection.InitFromObjectBuilder` (the [Core-Projection-Engine.md](./Core-Projection-Engine.md) entry point for programmatic projection loading). Finally `projector.SetValue("KeepProjection", true)` ensures the blueprint is retained.

**Config toggle.** `Config.Current.RepairProjection`.

| Member | Kind | Description |
|--------|------|-------------|
| `IterControls()` | `static IEnumerable<CustomControl>` | Yields the "Load Repair Projection" terminal button, placed before "Blueprint" |

---

## ToolbarFix

*`public static class ToolbarFix` — `MultigridProjectorClient.Extra`*

**Player perspective.** A **"Fix All Toolbars"** button appears in the projector terminal before "Blueprint" whenever the projector is enabled and actively projecting. After a YES/NO confirmation dialog, it merges all toolbar slots and repairs block references (e.g. button-panel names, action targets) across the entire built grid, using the projection as the source of truth.

**Technical.** `FixToolbars` calls `MultigridProjection.TryFindProjectionByProjector` to resolve the engine projection, then shows a `MyGuiSandbox.CreateMessageBox` confirmation. On YES it invokes `projection.FixBlockRelations()`, which is a [Core-Projection-Engine.md](./Core-Projection-Engine.md) method that reconciles toolbar entries and block relations across all subgrids. No config toggle gates this feature.

**Config toggle.** None — always visible for working projectors that are projecting.

| Member | Kind | Description |
|--------|------|-------------|
| `IterControls()` | `static IEnumerable<CustomControl>` | Yields the "Fix All Toolbars" terminal button, placed before "Blueprint" |

---

## Feature → Toggle / Hotkey / Dialog mapping

| Feature class | Config toggle | Terminal control | Toolbar action | Dialog |
|---------------|--------------|-----------------|----------------|--------|
| `ConnectSubgrids` | `ConnectSubgrids` | None (called by `Construction`) | — | — |
| `CraftProjection` | `CraftProjection` | "Assemble Projection" button | — | [CraftDialog](./Client-Menus.md) |
| `ProjectorAligner` | `ProjectorAligner` | "Align Projection" button | `ProjectorAlignerStart` | [AlignerDialog](./Client-Menus.md) |
| `BlockHighlight` | `BlockHighlight` | "Highlight Blocks" checkbox | Toggle / Enable / Disable | — |
| `ShipWelding` | `ShipWelding` | None (background loop) | — | — |
| `ApplyPaint` | None | "Apply Paint" button | — | — |
| `RepairProjection` | `RepairProjection` | "Load Repair Projection" button | — | [ProjectionDialog](./Client-Menus.md) |
| `ToolbarFix` | None | "Fix All Toolbars" button | — | Inline YES/NO confirm |

Terminal controls are registered by the `MySpaceProjector_CreateTerminalControls` transpiler in [Client-Patches.md](./Client-Patches.md). Per-frame features (`BlockHighlight.HighlightLoop`, `ShipWelding.WeldLoop`) are driven by `PluginSession`. Config properties are documented in [Client-Plugin.md](./Client-Plugin.md). Construction helpers (`GetBuiltBlock`, `SpawnBlockOnGrid`, `CanPlaceBlock`, `GrindBlock`) used by several features are in [Client-Utilities.md](./Client-Utilities.md). The full feature list as seen by end-users is in [../Installation.md](../Installation.md).
