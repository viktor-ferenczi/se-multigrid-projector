# Client Utilities

This module provides client-side helper types used throughout the Multigrid Projector client plugin. It covers four concerns: runtime reflection over private game fields and methods (`Reflection`), block construction and welding on both the local client and vanilla servers (`Construction`), post-build property synchronisation for newly placed blocks (`UpdateBlock` and its companion `UpdateEventController`), terminal-control insertion helpers (`AddControl`, `CustomControl`), and a catalogue of built-in action icon paths (`ActionIcons`). All types live in the `MultigridProjectorClient.Utilities` namespace and are consumed by the client feature implementations and Harmony patches described in [Client-Features.md](./Client-Features.md) and [Client-Patches.md](./Client-Patches.md).

## Files

| File | Lines | Purpose |
|------|-------|---------|
| [Construction.cs](../../ClientPlugin/Utilities/Construction.cs) | 284 | Client-side block placement, subgrid welding dispatch, grinding, and post-placement event wiring |
| [Reflection.cs](../../ClientPlugin/Utilities/Reflection.cs) | 278 | Uniform wrappers for `FieldInfo` get/set and `MethodInfo`/generic-method delegate creation |
| [UpdateBlock.cs](../../ClientPlugin/Utilities/UpdateBlock.cs) | 210 | Copies all terminal properties, custom data, blueprints, scripts, and power state from a preview block to a newly built block; handles Event Controller and Turret Controller special cases |
| [AddControl.cs](../../ClientPlugin/Utilities/AddControl.cs) | 51 | Inserts a typed `MyTerminalControl<TBlock>` before or after a named existing control |
| [ActionIcons.cs](../../ClientPlugin/Utilities/ActionIcons.cs) | 48 | String constants for every standard terminal-action icon `.dds` path |
| [CustomControl.cs](../../ClientPlugin/Utilities/CustomControl.cs) | 24 | Data class pairing a `ControlPlacement` direction, a reference control ID, and an `ITerminalControl` instance |

---

## Construction

*`internal static class MultigridProjectorClient.Utilities.Construction`*

Handles all client-side block construction and destruction operations for projected subgrids. It is the core execution path invoked when the local player (or the plugin on their behalf) builds or removes a projected block. It routes work between the server-side MGP plugin, the client-welding fallback for vanilla servers, and creative-mode shortcuts.

Networking: `SpawnBlockOnGrid` raises `MyCubeBuilder.RequestGridSpawn` as a static event over `MyMultiplayer`, causing the server to persist the new grid entity. `PlacePreviewBlock` calls `MyCubeGrid.BuildBlocks`, which is also a networked call replicated to all clients. `GrindBlock` calls `MyCubeGrid.RazeBlocks` (replicated) when creative tools are available, and falls back to a skin-and-message prompt otherwise (all damage is server-authoritative on survival servers).

After a block is placed, `WeldBlock` registers a one-shot `Events.OnNextFatBlockAdded` listener that calls `UpdateBlock.CopyProperties` to replicate terminal properties from the preview block and, for mechanical connection blocks, waits for the top-part replication event before connecting or skinning the attachment.

| Member | Kind | Description |
|--------|------|-------------|
| `GrindBlock(MyCubeGrid grid, Vector3I location)` | static method | Destroys a block in creative mode via `RazeBlocks`; in survival, skins it red with the "Weldless" skin and shows a chat prompt asking the player to remove it manually |
| `SpawnBlockOnGrid(MyCubeBlockDefinition blockDefinition, MatrixD worldMatrix, MyCubeGrid.MyBlockVisuals visuals)` | static method | Constructs a standalone grid block by sending `MyCubeBuilder.RequestGridSpawn` over multiplayer, then fires the `OnBlockAdded` event delegate (retrieved via `Reflection.GetValue`) for local subscribers |
| `PlacePreviewBlock(Subgrid subgrid, Vector3I blockPosition)` | static method | Translates a block position from the preview grid to the built grid coordinate space, then calls `MyCubeGrid.BuildBlocks` to place it with the correct orientation, colour, and skin |
| `GetBuiltBlock(MySlimBlock projectedBlock)` | static method | Returns the matching built `MySlimBlock` for a projected block, or `null` if absent or mismatched by definition |
| `VerifyBuiltBlock(MySlimBlock projectedBlock, MySlimBlock builtBlock)` | static method | Confirms that `builtBlock` occupies the same grid position as `projectedBlock` and is of the same block definition |
| `CanPlaceBlock(MyCubeBlockDefinition blockDefinition, MatrixD worldMatrix, bool dynamicMode = true)` | static method | Tests whether a block can be placed at a given world matrix using `MyCubeGrid.TestBlockPlacementArea` against the appropriate grid-size build settings |
| `WeldBlock(MyProjectorBase projector, MySlimBlock cubeBlock, long owner, ref long builtBy)` | static method | Central dispatch for the weld operation: returns `true` if the server should handle building (encoding the subgrid index via `builtBy` when MGP server plugin is present), or handles placement locally via `PlacePreviewBlock` and registers post-build property copy; returns `false` to suppress the default game handler |

---

## Reflection

*`public static class MultigridProjectorClient.Utilities.Reflection`*

A uniform, null-safe reflection façade that eliminates repetitive `BindingFlags` boilerplate throughout the client codebase. All overloads follow the same three-variant pattern: operate on an instance (resolving the type at runtime), operate on a static member of an explicit `Type`, or operate on an instance member of an explicit `Type` (useful when the declared type differs from the runtime type). All methods return `null`/`false` rather than throwing when the member is not found. Used directly by `Construction.SpawnBlockOnGrid` to retrieve the `OnBlockAdded` event delegate from `MyCubeBuilder`.

| Member | Kind | Description |
|--------|------|-------------|
| `GetValue(object instance, string typeName)` | static method | Gets an instance field value (public or non-public) using the runtime type of `instance` |
| `GetValue(Type targetClass, string typeName)` | static method | Gets a static field value from `targetClass` |
| `GetValue(Type targetClass, object instance, string typeName)` | static method | Gets an instance field value declared on `targetClass` (bypasses runtime-type resolution) |
| `SetValue(object instance, string typeName, object value)` | static method | Sets an instance field; returns `false` if the field is not found |
| `SetValue(Type targetClass, string typeName, object value)` | static method | Sets a static field on `targetClass`; returns `false` if not found |
| `SetValue(Type targetClass, object instance, string typeName, object value)` | static method | Sets an instance field declared on `targetClass`; returns `false` if not found |
| `GetMethod(object instance, string methodName, Type[] overload = null)` | static method | Returns a strongly-typed `Delegate` bound to an instance method; overload parameter types may be specified to disambiguate |
| `GetMethod(Type targetClass, string methodName, Type[] overload = null)` | static method | Returns a `Delegate` bound to a static method of `targetClass` |
| `GetMethod(Type targetClass, object instance, string methodName, Type[] overload = null)` | static method | Returns a `Delegate` bound to an instance method declared on `targetClass` |
| `GetGenericMethod(object instance, Func<MethodInfo, bool> predicate, Type[] inputTypes)` | static method | Finds the first instance method matching `predicate`, closes it over `inputTypes`, and returns a bound `Delegate` |
| `GetGenericMethod(Type targetClass, Func<MethodInfo, bool> predicate, Type[] inputTypes)` | static method | Same as above for static methods on `targetClass` |
| `GetGenericMethod(Type targetClass, object instance, Func<MethodInfo, bool> predicate, Type[] inputTypes)` | static method | Closes a generic instance method declared on `targetClass`, bound to `instance` |
| `GetType(object instance, string typeName)` | static method | Returns a nested type (public or non-public) of the runtime type of `instance` |
| `GetType(Type targetClass, string typeName)` | static method | Returns a nested type of `targetClass` |

---

## UpdateBlock

*`internal static class MultigridProjectorClient.Utilities.UpdateBlock`*

Synchronises the full terminal state from a preview (projected) block to a newly placed built block immediately after construction. This is required because the game creates built blocks with default settings; the plugin must replay every terminal property, custom data field, loaded blueprint, programmable-block script, and enabled/disabled state from the projection's stored object builder. All copy operations are dispatched via `Events.InvokeOnGameThread` with staggered frame delays (15–80 frames) to avoid race conditions with block initialisation and network replication.

`CopyProperties` handles the top-level dispatch: it iterates `ITerminalProperty` entries for Boolean, Color, Single, Int64, and StringBuilder types; skips `OnOff` during the first pass to avoid locking further property updates; copies `CustomData` directly; and then branches on the concrete block type for projector blueprints, programmable-block scripts, and Event Controller events. Power state (`OnOff`) is applied last (frame 80) after all other properties have been written. Property IDs excluded per block type (`SearchBox` for Event Controllers; `RotorAzimuth`, `RotorElevation`, `CameraList` for Turret Controllers) are filtered out because they are either UI-only fields or contain entity IDs that must be remapped by a separate `ReferenceFixer` pass.

Networking: `SetValue` calls on `MyTerminalBlock` propagate through the game's own `Sync<T>` fields, so property copies are automatically replicated to the server.

| Member | Kind | Description |
|--------|------|-------------|
| `CopyProperties(MyTerminalBlock sourceBlock, MyTerminalBlock destinationBlock)` | static method | Copies all terminal properties, custom data, block-type-specific data (blueprints, scripts, event controller events), and power state from `sourceBlock` to `destinationBlock` using frame-deferred game-thread dispatches |

---

## UpdateEventController

*`internal static class MultigridProjectorClient.Utilities.UpdateEventController`*

Companion to `UpdateBlock` that handles the specialised property copying required for `MyEventControllerBlock`. Event Controller state is not exposed as standard terminal properties and must be transferred via dedicated API calls.

| Member | Kind | Description |
|--------|------|-------------|
| `CopyEvents(MyEventControllerBlock sourceBlock, MyEventControllerBlock destinationBlock)` | static method | Copies the selected event (by `UniqueSelectionId`) and the condition state (threshold, comparison direction, AND/OR mode, and angle component) from `sourceBlock` to `destinationBlock` using two frame-deferred game-thread dispatches |

---

## AddControl

*`internal static class MultigridProjectorClient.Utilities.AddControl`*

Provides type-safe helpers for inserting custom terminal controls relative to an existing control identified by its string ID. Used by client features and patches that add plugin-specific controls to block terminal panels. See also `CustomControl` for the data class that pairs placement intent with a control instance.

| Member | Kind | Description |
|--------|------|-------------|
| `AddControlAfter<TBlock>(string id, MyTerminalControl<TBlock> control)` | static method | Inserts `control` immediately after the existing control with `id`; returns `false` if the reference control is not found |
| `AddControlBefore<TBlock>(string id, MyTerminalControl<TBlock> control)` | static method | Inserts `control` immediately before the existing control with `id`; returns `false` if the reference control is not found |

---

## ActionIcons

*`public static class MultigridProjectorClient.Utilities.ActionIcons`*

A catalogue of `string` constants for every standard terminal action icon `.dds` texture path used by Space Engineers. Consumed when registering custom `MyTerminalAction` instances on blocks to ensure icon paths are consistent with the game's own conventions.

| Member | Kind | Description |
|--------|------|-------------|
| `NONE` | `string` const | Empty string — no icon |
| `TOGGLE` | `string` const | Toggle action icon |
| `ON` / `OFF` | `string` const | Switch-on / switch-off icons |
| `REVERSE` | `string` const | Reverse action icon |
| `RESET` | `string` const | Reset action icon |
| `INCREASE` / `DECREASE` | `string` const | Increase / decrease action icons |
| `START` | `string` const | Start action icon |
| `CHARACTER_ON/OFF/TOGGLE` | `string` const | Character-variant switch icons |
| `LARGESHIP_ON/OFF/TOGGLE` | `string` const | Large ship variant switch icons |
| `SMALLSHIP_ON/OFF/TOGGLE` | `string` const | Small ship variant switch icons |
| `STATION_ON/OFF/TOGGLE` | `string` const | Station variant switch icons |
| `NEUTRALS_ON/OFF/TOGGLE` | `string` const | Neutrals variant switch icons |
| `METEOR_ON/OFF/TOGGLE` | `string` const | Meteor variant switch icons |
| `MISSILE_ON/OFF/TOGGLE` | `string` const | Missile variant switch icons |
| `MOVING_OBJECT_ON/OFF/TOGGLE` | `string` const | Moving-object variant switch icons |

---

## CustomControl

*`public class MultigridProjectorClient.Utilities.CustomControl`*

A plain data class that bundles a placement direction, a reference control ID, and an `ITerminalControl` instance. Used as a descriptor when a feature must declare controls that are inserted relative to a named existing control, deferring the actual insertion to a later registration phase.

| Member | Kind | Description |
|--------|------|-------------|
| `Placement` | `ControlPlacement` readonly field | `Before` or `After` — where the control is inserted relative to `ReferenceId` |
| `ReferenceId` | `string` readonly field | The `Id` of the existing terminal control used as the insertion anchor |
| `Control` | `ITerminalControl` readonly field | The control to insert |

---

## Cross-references

- [Client-Features.md](./Client-Features.md) — feature implementations that call `Construction.WeldBlock`, `UpdateBlock.CopyProperties`, `AddControl`, and `CustomControl` to build projected blocks and extend terminal UIs.
- [Client-Patches.md](./Client-Patches.md) — Harmony patches that hook into `MyCubeBuilder` and `MyProjectorBase` pipelines and delegate to `Construction` and `UpdateBlock`.
- [Core-Projection-Engine.md](./Core-Projection-Engine.md) — defines `Subgrid`, `ProjectedBlock`, and `MultigridProjection` types that `Construction` and `UpdateBlock` query to resolve preview-to-built grid mappings and subgrid indices.
