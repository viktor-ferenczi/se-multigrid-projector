# Shared Extension Methods

This module collects static extension-method classes that enrich game types (`MyCubeGrid`, `MyCubeBlock`, `MyProjectorBase`, object builders, VRageMath structs, and standard collections) with helpers used throughout the Multigrid Projector plugin. The classes live in `Shared/Extensions/` and are compiled into both the client and server assemblies. They abstract away direct field access (enabled by the Krafs publicizer), reduce boilerplate in patches, and encapsulate cross-cutting concerns such as blueprint normalization, projection-state management, grid alignment, and PCU accounting. See [Core-Projection-Engine.md](./Core-Projection-Engine.md) for the primary consumers of these helpers.

---

## Files

| File | Lines | Purpose |
|---|---|---|
| [MyObjectBuilderExtensions.cs](../../Shared/Extensions/MyObjectBuilderExtensions.cs) | 218 | Blueprint / object-builder preparation, world-position censoring, toolbar retrieval, repair-projector alignment |
| [MyProjectorBaseExtensions.cs](../../Shared/Extensions/MyProjectorBaseExtensions.cs) | 185 | Typed get/set wrappers for private `MyProjectorBase` fields exposed by the publicizer; clipboard access; entity-ID remapping |
| [MyCubeBlockExtensions.cs](../../Shared/Extensions/MyCubeBlockExtensions.cs) | 143 | Name helpers, definition matching, grid alignment, toolbar retrieval, event-controller selected-block access |
| [EnumerableExtensions.cs](../../Shared/Extensions/EnumerableExtensions.cs) | 94 | Blueprint collection helpers: clone, index enumeration, position normalization, PCU calculation, projection preparation |
| [MyCubeGridExtensions.cs](../../Shared/Extensions/MyCubeGridExtensions.cs) | 39 | Safe name helpers, block-group list access, overlapping-block lookup |
| [MyBlockGroupExtensions.cs](../../Shared/Extensions/MyBlockGroupExtensions.cs) | 24 | Terminal-block set access on a block group; factory method for new groups |
| [LinearAlgebraExtensions.cs](../../Shared/Extensions/LinearAlgebraExtensions.cs) | 23 | Conversion between `MatrixD` and `MyPositionAndOrientation`; `Vector3I` YAML formatting |
| [MyMechanicalConnectionBlockBaseExtensions.cs](../../Shared/Extensions/MyMechanicalConnectionBlockBaseExtensions.cs) | 20 | Return-value adapter for `CreateTopPart` on mechanical base blocks |
| [DictionaryExtensions.cs](../../Shared/Extensions/DictionaryExtensions.cs) | 15 | In-place dictionary sync (`Update`) that removes stale keys and upserts new values |

---

## MyObjectBuilderExtensions

*`public static class MyObjectBuilderExtensions`*

**Extends:** `MyObjectBuilder_CubeGrid`, `MyObjectBuilder_CubeBlock`, `MyObjectBuilder_TerminalBlock`, `IReadOnlyCollection<MyObjectBuilder_CubeGrid>`, `MyObjectBuilder_ComponentContainer`

**Purpose:** Mutates and queries object builders — the serialized snapshots of grids and blocks — before they are used to create or repair projected entities. Key responsibilities include stripping ownership and dynamic-physics flags for projection use, aligning a blueprint to a repair projector, censoring absolute world positions for network transmission, and surfacing toolbar builders from the type hierarchy.

| Method | Extends | Description |
|---|---|---|
| `PrepareForProjection(this MyObjectBuilder_CubeGrid gridBuilder)` | `MyObjectBuilder_CubeGrid` | Sets `IsStatic = false`, `DestructibleBlocks = false`, and calls `PrepareForProjection` on every block builder. |
| `PrepareForProjection(this MyObjectBuilder_CubeBlock blockBuilder)` | `MyObjectBuilder_CubeBlock` | Clears owner and share-mode; for projector blocks calls `RemoveNestedRepairBlueprints` to prevent recursive repair projections. |
| `GetToolbar(this MyObjectBuilder_TerminalBlock block)` | `MyObjectBuilder_TerminalBlock` | Returns the serialized `MyObjectBuilder_Toolbar` from sensor, button-panel, event-controller, ship-controller, timer, defensive-combat, or offensive-combat builders; `null` for unsupported types. |
| `AlignToRepairProjector(this MyObjectBuilder_CubeGrid gridBuilder, MyProjectorBase projector)` | `MyObjectBuilder_CubeGrid` | Finds the matching projector block in the blueprint using a four-fallback strategy (exact name+position, unique name, first block, "Repair"-named) and moves it to index 0 so the preview grid aligns automatically; returns `true` on success. |
| `CensorWorldPosition(this MyObjectBuilder_CubeGrid gridBuilder)` | `MyObjectBuilder_CubeGrid` | Replaces the grid's `PositionAndOrientation` with `MyPositionAndOrientation.Default`. |
| `CensorWorldPosition(this IReadOnlyCollection<MyObjectBuilder_CubeGrid> gridBuilders)` | `IReadOnlyCollection<MyObjectBuilder_CubeGrid>` | Translates all grids so the first grid is at the origin, preserving relative offsets between subgrids while removing absolute world coordinates. |
| `TryGet<T>(this MyObjectBuilder_ComponentContainer componentContainer, out T component)` | `MyObjectBuilder_ComponentContainer` | Scans the component list for the first instance of type `T` and returns it via `out`; returns `false` if not found. |

---

## MyProjectorBaseExtensions

*`public static class MyProjectorBaseExtensions`*

**Extends:** `MyProjectorBase`

**Purpose:** Provides named, typed accessors and mutators for the private fields of `MyProjectorBase` that were made accessible by the Krafs publicizer. This avoids raw field references scattered across patches and keeps field-name changes isolated to this one file. Also provides the clipboard accessor and a thread-safe entity-ID remapping helper. See [Core-Projection-Engine.md](./Core-Projection-Engine.md) for how the projection engine orchestrates these state fields.

| Method | Extends | Description |
|---|---|---|
| `GetClipboard(this MyProjectorBase projector)` | `MyProjectorBase` | Returns the projector's `MyProjectorClipboard` instance. |
| `SetBuildableBlocksCount(this MyProjectorBase projector, int value)` | `MyProjectorBase` | Writes `m_buildableBlocksCount`. |
| `GetShowOnlyBuildable(this MyProjectorBase projector)` | `MyProjectorBase` | Reads `m_showOnlyBuildable`. |
| `GetKeepProjection(this MyProjectorBase projector)` | `MyProjectorBase` | Reads `m_keepProjection`. |
| `GetInstantBuildingEnabled(this MyProjectorBase projector)` | `MyProjectorBase` | Reads `m_instantBuildingEnabled`. |
| `GetShouldUpdateTexts(this MyProjectorBase projector)` | `MyProjectorBase` | Reads `m_shouldUpdateTexts`. |
| `SetShouldUpdateTexts(this MyProjectorBase projector, bool value)` | `MyProjectorBase` | Writes `m_shouldUpdateTexts`. |
| `SetRemainingBlocks(this MyProjectorBase projector, int value)` | `MyProjectorBase` | Writes `m_remainingBlocks`. |
| `SetStatsDirty(this MyProjectorBase projector, bool value)` | `MyProjectorBase` | Writes `m_statsDirty`. |
| `SetTotalBlocks(this MyProjectorBase projector, int value)` | `MyProjectorBase` | Writes `m_totalBlocks`. |
| `SetRemainingArmorBlocks(this MyProjectorBase projector, int value)` | `MyProjectorBase` | Writes `m_remainingArmorBlocks`. |
| `GetRemainingArmorBlocks(this MyProjectorBase projector)` | `MyProjectorBase` | Reads `m_remainingArmorBlocks`. |
| `GetRemainingBlocksPerType(this MyProjectorBase projector)` | `MyProjectorBase` | Reads `m_remainingBlocksPerType` as `Dictionary<MyCubeBlockDefinition, int>`. |
| `GetOriginalGridBuilders(this MyProjectorBase projector)` | `MyProjectorBase` | Reads `m_originalGridBuilders` (the list of raw grid object builders stored in the projector). |
| `SetOriginalGridBuilders(this MyProjectorBase projector, List<MyObjectBuilder_CubeGrid> gridBuilders)` | `MyProjectorBase` | Writes `m_originalGridBuilders`. |
| `GetProjectionTimer(this MyProjectorBase projector)` | `MyProjectorBase` | Reads `m_projectionTimer`. |
| `SetProjectionTimer(this MyProjectorBase projector, int value)` | `MyProjectorBase` | Writes `m_projectionTimer`. |
| `SetHiddenBlock(this MyProjectorBase projector, MySlimBlock block)` | `MyProjectorBase` | Writes `m_hiddenBlock`. |
| `GetTierCanProject(this MyProjectorBase projector)` | `MyProjectorBase` | Reads `m_tierCanProject`. |
| `GetRemoveRequested(this MyProjectorBase projector)` | `MyProjectorBase` | Reads `m_removeRequested`. |
| `SetRemoveRequested(this MyProjectorBase projector, bool value)` | `MyProjectorBase` | Writes `m_removeRequested`. |
| `GetShouldResetBuildable(this MyProjectorBase projector)` | `MyProjectorBase` | Reads `m_shouldResetBuildable`. |
| `SetShouldResetBuildable(this MyProjectorBase projector, bool value)` | `MyProjectorBase` | Writes `m_shouldResetBuildable`. |
| `GetForceUpdateProjection(this MyProjectorBase projector)` | `MyProjectorBase` | Reads `m_forceUpdateProjection`. |
| `SetForceUpdateProjection(this MyProjectorBase projector, bool value)` | `MyProjectorBase` | Writes `m_forceUpdateProjection`. |
| `GetShouldUpdateProjection(this MyProjectorBase projector)` | `MyProjectorBase` | Reads `m_shouldUpdateProjection`. |
| `SetShouldUpdateProjection(this MyProjectorBase projector, bool value)` | `MyProjectorBase` | Writes `m_shouldUpdateProjection`. |
| `GetLastUpdate(this MyProjectorBase projector)` | `MyProjectorBase` | Reads `m_lastUpdate`. |
| `SetLastUpdate(this MyProjectorBase projector, int value)` | `MyProjectorBase` | Writes `m_lastUpdate`. |
| `GetProjectionRotation(this MyProjectorBase projector)` | `MyProjectorBase` | Reads `m_projectionRotation` as `Vector3I`. |
| `SetIsActivating(this MyProjectorBase projector, bool value)` | `MyProjectorBase` | Writes the publicizer-exposed `IsActivating` property. |
| `RemapObjectBuilders(this MyProjectorBase projector)` | `MyProjectorBase` | Reads `m_originalGridBuilders` and calls `MyEntities.RemapObjectBuilderCollection` inside a lock to consistently remap all entity IDs across subgrids while keeping mechanical connections intact. |

---

## MyCubeBlockExtensions

*`public static class MyCubeBlockExtensions`*

**Extends:** `MyCubeBlock`, `MySlimBlock`, `MyTerminalBlock`, `MyDefensiveCombatBlock`, `MyOffensiveCombatBlock`, `MyRemoteControl`, `MyEventControllerBlock`

**Purpose:** Provides safe display-name helpers, definition/orientation matching for projection placement, world-space grid alignment, toolbar retrieval across the full block-type hierarchy, and access to publicizer-exposed fields on combat and event-controller blocks. Used heavily in the projection engine (see [Core-Projection-Engine.md](./Core-Projection-Engine.md)) to match preview blocks against built blocks and to copy toolbar state.

| Method | Extends | Description |
|---|---|---|
| `GetSafeName(this MyCubeBlock block)` | `MyCubeBlock` | Returns the first non-null of `DisplayNameText`, `DisplayName`, `Name`, or `""`. |
| `GetDebugName(this MyCubeBlock block)` | `MyCubeBlock` | Returns `"<name> [<entityId>]"` for logging. |
| `HasSameDefinition(this MySlimBlock block, MySlimBlock other)` | `MySlimBlock` | Returns `true` when both slim blocks share the same `BlockDefinition.Id`. |
| `IsMatchingBuilder(this MySlimBlock previewBlock, MyObjectBuilder_CubeBlock blockBuilder)` | `MySlimBlock` | Returns `true` when the preview block's definition ID, forward orientation, and up orientation all match the builder. |
| `AlignGrid(this MyCubeBlock block, MyCubeBlock referenceBlock)` | `MyCubeBlock` | Repositions and reorients the block's entire `CubeGrid` so that `block` coincides with `referenceBlock` in world space, enabling sub-grid preview alignment. |
| `GetFocusedGridsInMechanicalGroup(this MyCubeBlock focusedBlock)` | `MyCubeBlock` | Returns all grids in the physical group of the focused block, with the focused block's own grid first. |
| `GetToolbar(this MyTerminalBlock block)` | `MyTerminalBlock` | Returns the runtime `MyToolbar` from sensor, button-panel, event-controller, flight-movement, ship-controller, timer, defensive-combat, or offensive-combat blocks; `null` otherwise. |
| `GetWaypointActionsToolbar(this MyDefensiveCombatBlock defensiveCombatBlock)` | `MyDefensiveCombatBlock` | Returns `m_waypointActionsToolbar` (publicizer field). |
| `GetWaypointActionsToolbar(this MyOffensiveCombatBlock offensiveCombatBlock)` | `MyOffensiveCombatBlock` | Returns `m_waypointActionsToolbar` (publicizer field). |
| `GetBoundCameraSync(this MyRemoteControl remoteControlBlock)` | `MyRemoteControl` | Returns the `Sync<long, SyncDirection.BothWays>` field `m_bindedCamera` used for bound-camera state. |
| `GetSelectedBlockIds(this MyEventControllerBlock eventControllerBlock)` | `MyEventControllerBlock` | Reads `m_selectedBlockIds` as `MySerializableList<long>`. |
| `SetSelectedBlockIds(this MyEventControllerBlock eventControllerBlock, MySerializableList<long> selectedBlockIds)` | `MyEventControllerBlock` | Writes `m_selectedBlockIds`. |
| `GetSelectedBlocks(this MyEventControllerBlock eventControllerBlock)` | `MyEventControllerBlock` | Reads `m_selectedBlocks` as `Dictionary<long, IMyTerminalBlock>`. |

---

## EnumerableExtensions

*`public static class EnumerableExtensions`*

**Extends:** `IEnumerable<T>`, `IEnumerable<MyObjectBuilder_CubeGrid>`, `IEnumerable<MyCubeGrid>`, `List<MyObjectBuilder_CubeGrid>`

**Purpose:** Provides collection-level operations on blueprints (lists of grid object builders) and on live grid sets. Handles cloning, positional normalization, bulk projector assignment, block counting, PCU estimation, and the two-phase projection-preparation pipeline. Used by the [Core-Projection-Engine.md](./Core-Projection-Engine.md) when loading and normalizing blueprints.

| Method | Extends | Description |
|---|---|---|
| `Enumerate<T>(this IEnumerable<T> coll)` | `IEnumerable<T>` | Yields `(Index, Value)` tuples — a Python-style indexed enumeration for `foreach`. |
| `Clone(this IEnumerable<MyObjectBuilder_CubeGrid> gridBuilders)` | `IEnumerable<MyObjectBuilder_CubeGrid>` | Deep-clones each grid builder and returns a new `List<MyObjectBuilder_CubeGrid>`. |
| `NormalizeBlueprintPositionAndOrientation(this IEnumerable<MyObjectBuilder_CubeGrid> gridBuilders)` | `IEnumerable<MyObjectBuilder_CubeGrid>` | Transforms all grids so the first grid is at the identity transform, correcting position data damaged in client–server transmission. |
| `SetProjector(this IEnumerable<MyCubeGrid> grids, MyProjectorBase projector)` | `IEnumerable<MyCubeGrid>` | Assigns the given `projector` reference to the `Projector` property of every live grid. |
| `GetBlockCount(this IEnumerable<MyObjectBuilder_CubeGrid> grids)` | `IEnumerable<MyObjectBuilder_CubeGrid>` | Returns the total number of blocks across all grid builders as `long`. |
| `TryCalculatePcu(this IEnumerable<MyObjectBuilder_CubeGrid> gridBuilders, out long totalPcu, out int unknownBlockCount)` | `IEnumerable<MyObjectBuilder_CubeGrid>` | Sums PCU from block definitions; `unknownBlockCount` tallies blocks without a definition. Returns `true` only when all blocks are known. |
| `PrepareForProjection(this List<MyObjectBuilder_CubeGrid> gridBuilders)` | `List<MyObjectBuilder_CubeGrid>` | Calls `MyObjectBuilderExtensions.PrepareForProjection` on every grid builder in the list. |
| `PrepareForConsoleProjection(this IEnumerable<MyObjectBuilder_CubeGrid> grids, MyProjectorClipboard clipboard)` | `IEnumerable<MyObjectBuilder_CubeGrid>` | Runs each grid through `clipboard.ProcessCubeGrid` (the vanilla projector's own normalization pass). |

---

## MyCubeGridExtensions

*`public static class MyCubeGridExtensions`*

**Extends:** `MyCubeGrid`

**Purpose:** Adds safe display-name helpers mirroring `MyCubeBlockExtensions`, exposes the publicizer-surfaced `BlockGroups` list for iteration, and provides a world-space overlapping-block lookup. Called by patches and the projection engine when enumerating or matching grid content. See [Core-Projection-Engine.md](./Core-Projection-Engine.md).

| Method | Extends | Description |
|---|---|---|
| `GetSafeName(this MyCubeGrid grid)` | `MyCubeGrid` | Returns the first non-null of `DisplayNameText`, `DisplayName`, `Name`, or `""`. |
| `GetDebugName(this MyCubeGrid grid)` | `MyCubeGrid` | Returns `"<name> [<entityId>]"` for logging. |
| `GetBlockGroups(this MyCubeGrid grid)` | `MyCubeGrid` | Returns the publicizer-exposed `BlockGroups` list (`List<MyBlockGroup>`). |
| `GetOverlappingBlock(this MyCubeGrid grid, MySlimBlock block)` | `MyCubeGrid` | Converts the given block's world position to grid-integer coordinates and returns the block at that position on `grid`, or `null`. |

---

## MyBlockGroupExtensions

*`public static class MyBlockGroupExtensions`*

**Extends:** `MyBlockGroup`

**Purpose:** Exposes the internal terminal-block set on a block group and provides a factory for creating named groups programmatically (used when the projection engine recreates block groups from blueprint data).

| Method | Extends | Description |
|---|---|---|
| `GetTerminalBlocks(this MyBlockGroup blockGroup)` | `MyBlockGroup` | Returns the publicizer-exposed `Blocks` field as `HashSet<MyTerminalBlock>`. |
| `NewBlockGroup(string name)` | *(static factory, not an extension)* | Creates a new `MyBlockGroup` with `Name` initialized to the given string via `StringBuilder`. |

---

## LinearAlgebraExtensions

*`public static class LinearAlgebraExtensions`*

**Extends:** `MatrixD`, `MyPositionAndOrientation`, `Vector3I`

**Purpose:** Bridges the gap between the `MatrixD` world-matrix representation used internally and the `MyPositionAndOrientation` struct used in object builders and networking. Also provides a compact YAML-style formatter for integer vectors used in diagnostic output. Referenced in `EnumerableExtensions.NormalizeBlueprintPositionAndOrientation` and in [Core-Projection-Engine.md](./Core-Projection-Engine.md) coordinate transforms.

| Method | Extends | Description |
|---|---|---|
| `ToPositionAndOrientation(this MatrixD matrix)` | `MatrixD` | Constructs a `MyPositionAndOrientation` from the matrix's `Translation`, `Forward`, and `Up` vectors. |
| `ToMatrixD(this MyPositionAndOrientation po, out MatrixD matrix)` | `MyPositionAndOrientation` | Constructs a `MatrixD` via `MatrixD.CreateWorld` from the orientation's `Forward` and `Up` and the stored `Position`. |
| `FormatYaml(this Vector3I v)` | `Vector3I` | Returns `"X, Y, Z"` — a compact, YAML-compatible representation for logging and diagnostics. |

---

## MyMechanicalConnectionBlockBaseExtensions

*`public static class MyMechanicalConnectionBlockBaseExtensions`*

**Extends:** `MyMechanicalConnectionBlockBase`

**Purpose:** Adapts the game's `CreateTopPart(out topBlock, builderID, ...)` overload into a return-value form, automatically forwarding the base block's own `BuiltBy` field. Used when the projection engine creates rotor tops, piston heads, and hinge tops as part of multi-subgrid blueprint construction.

| Method | Extends | Description |
|---|---|---|
| `CreateTopPart(this MyMechanicalConnectionBlockBase baseBlock, MyCubeBlockDefinitionGroup definitionGroup, MyMechanicalConnectionBlockBase.MyTopBlockSize topSize, bool instantBuild)` | `MyMechanicalConnectionBlockBase` | Calls the game's `CreateTopPart(out topBlock, baseBlock.BuiltBy, definitionGroup, topSize, instantBuild)` and returns `topBlock` directly. |

---

## DictionaryExtensions

*`public static class DictionaryExtensions`*

**Extends:** `Dictionary<TK, TV>`

**Purpose:** Provides an in-place synchronization operation that makes one dictionary mirror another — removing keys absent from the source and upserting all key–value pairs present in it. Used in the [Core-Projection-Engine.md](./Core-Projection-Engine.md) to keep cached projection-state dictionaries consistent with authoritative data without allocating a new dictionary.

| Method | Extends | Description |
|---|---|---|
| `Update<TK, TV>(this Dictionary<TK, TV> dict, Dictionary<TK, TV> other)` | `Dictionary<TK, TV>` | Removes all keys not present in `other`, then sets `dict[key] = value` for every entry in `other`. |
