# Public Mod & PB API

The **Public Mod & PB API** is the supported surface through which external **mods** and in-game **Programmable Block (PB) scripts** query and control multi-subgrid projections built by the Multigrid Projector plugin. Every consumer ultimately talks to the same engine-side implementation, [`MultigridProjectorApiProvider`](./Core-Projection-Engine.md), but reaches it through one of two consumption paths:

- **Mod API** — a server/client mod performs a mod-message handshake with the plugin. It sends a request via `MyAPIGateway.Utilities.SendModMessage` and receives back an `object[]` of delegates plus a version string. The [`MultigridProjectorModAgent`](../../MultigridProjectorApi/Api/MultigridProjectorModAgent.cs) class wraps this raw array behind the strongly typed [`IMultigridProjectorApi`](../../MultigridProjectorApi/Api/IMultigridProjectorApi.cs) interface.
- **PB API** — a Programmable Block script copies the same agent source *inside* itself (the API project compiles into the script) and performs the identical mod-message handshake at runtime. The delegate array is provided by the plugin via the same registered messaging IDs, so the agent code is shared verbatim between mods and PB scripts.

When the plugin is **not** installed, a mod can instead instantiate the [`MultigridProjectorModShim`](../../MultigridProjectorApi/Api/MultigridProjectorModShim.cs), a drop-in implementation of the same interface that emulates single-grid projection behavior so the consuming mod keeps working without duplicating projector logic.

All of these types live in the `MultigridProjector.Api` namespace inside the [`MultigridProjectorApi`](../../MultigridProjectorApi) shared project (`MultigridProjectorApi.shproj` / `.projitems`), which is compiled into the client plugin, the server plugin, every consuming mod, and every PB script that uses the API.

See the parent [API overview](../API.md), the engine-side provider in [Core-Projection-Engine.md](./Core-Projection-Engine.md), and worked end-to-end usage in [Examples.md](./Examples.md).

## Files

| File | Lines | Purpose |
| --- | --- | --- |
| [IMultigridProjectorApi.cs](../../MultigridProjectorApi/Api/IMultigridProjectorApi.cs) | 55 | The public API contract: the interface every consumer programs against. |
| [MultigridProjectorModAgent.cs](../../MultigridProjectorApi/Api/MultigridProjectorModAgent.cs) | 174 | Client/PB-side agent that performs the mod-message handshake and adapts the raw delegate array to the interface. |
| [MultigridProjectorModShim.cs](../../MultigridProjectorApi/Api/MultigridProjectorModShim.cs) | 313 | Fallback implementation used when the plugin is absent; emulates single-grid projection state for one projector. |
| [BlockState.cs](../../MultigridProjectorApi/Api/BlockState.cs) | 23 | Enum of per-block build states (flag values, usable as a mask). |
| [BlockLocation.cs](../../MultigridProjectorApi/Api/BlockLocation.cs) | 24 | Struct identifying a block by subgrid index and position, used for subgrid connections. |

## How the API is consumed

### The handshake (Mod API and PB API)

Both consumption paths use the same Space Engineers mod-messaging channel. The IDs are derived from the plugin's Steam Workshop ID (`2415983416`):

- `ModApiRequestId = WorkshopId * 1000 + 0`
- `ModApiResponseId = WorkshopId * 1000 + 1`

The handshake performed by [`MultigridProjectorModAgent`](../../MultigridProjectorApi/Api/MultigridProjectorModAgent.cs) is:

1. In its constructor the agent registers a message handler for `ModApiResponseId`, then sends an empty (`null` payload) request to `ModApiRequestId`.
2. The plugin's [`MultigridProjectorApiProvider`](./Core-Projection-Engine.md) responds by sending back an `object[]` to `ModApiResponseId`.
3. The agent's `HandleModMessage` casts the payload to `object[]`. Element `[0]` is the version string; elements `[1]`..`[12]` are the API delegates. Each public method on the agent casts the appropriate slot to its concrete `Func<...>` type and invokes it.

This same agent source is what a **PB script** embeds (the `IngameApiTest` example bundles the agent), so a Programmable Block obtains the API the same way a mod does — there is no separate registration mechanism for scripts.

### Version negotiation and availability

- The agent exposes an `Available` flag and a `Version` string. Both are set only once a valid response arrives.
- `HandleModMessage` treats the response as valid only if the array is non-null and `Length >= 12`. If the plugin is missing or returns an incompatible array, `Available` stays `false`.
- While `Available` is `false`, **every** agent method short-circuits to a safe default (`0`, `false`, `null`, `""`, or `BlockState.Unknown`) instead of calling into a missing delegate. Consumers should branch on `Available` (or treat these defaults as "no projection") to remain robust when the plugin is absent.
- The interface's `Version` getter reflects the Multigrid Projector version (currently `0.9.2`). The plugin advertises its version through array slot `[0]`; the shim hard-codes the same value.

### Fallback when the plugin is absent

If the plugin is not installed, a mod can construct one [`MultigridProjectorModShim`](../../MultigridProjectorApi/Api/MultigridProjectorModShim.cs) **per projector** and use it through the same `IMultigridProjectorApi` interface. The shim is `IDisposable` and must be disposed when the projector closes or its data is no longer needed — unlike the agent, which needs only a single instance per mod to serve all projectors. See the shim section below for its single-grid limitations.

Worked, compilable examples of both paths are documented in [Examples.md](./Examples.md).

## IMultigridProjectorApi

*`public interface IMultigridProjectorApi` (namespace `MultigridProjector.Api`)*

The contract every consumer programs against. It is implemented by the plugin engine (surfaced as the delegate array), by the [`MultigridProjectorModAgent`](../../MultigridProjectorApi/Api/MultigridProjectorModAgent.cs) wrapper, and by the [`MultigridProjectorModShim`](../../MultigridProjectorApi/Api/MultigridProjectorModShim.cs) fallback. All methods are keyed by `projectorId` (the entity ID of an `IMyProjector`) and, where applicable, a zero-based `subgridIndex`. Subgrid `0` is always the projector's own built grid; higher indices are additional subgrids of a multigrid blueprint.

| Member | Kind | Description |
| --- | --- | --- |
| `Version` | `string` property (get) | The Multigrid Projector version string (e.g. `0.9.2`). |
| `GetSubgridCount(long projectorId)` | `int` method | Number of subgrids in the active projection; returns `0` if there is no projection. |
| `GetOriginalGridBuilders(long projectorId)` | `List<MyObjectBuilder_CubeGrid>` method | The original grid builders the projection is based on; returns `null` if no blueprint is loaded. |
| `GetPreviewGrid(long projectorId, int subgridIndex)` | `IMyCubeGrid` method | The preview grid (hologram) for the given subgrid. It always exists while the projection is active, even if the subgrid is fully built. |
| `GetBuiltGrid(long projectorId, int subgridIndex)` | `IMyCubeGrid` method | The already-built grid for the given subgrid, or `null` if not built yet. The first subgrid (index `0`) is always built. |
| `GetBlockState(long projectorId, int subgridIndex, Vector3I position)` | `BlockState` method | The build state of a single projected block at `position` within the subgrid. |
| `GetBlockStates(Dictionary<Vector3I, BlockState> blockStates, long projectorId, int subgridIndex, BoundingBoxI box, int mask)` | `bool` method | Writes the build state of the preview blocks within `box` (in the given subgrid) into `blockStates`, filtered to states matching `mask` (a bitwise OR of `BlockState` flag values). Returns `true` on success. |
| `GetBaseConnections(long projectorId, int subgridIndex)` | `Dictionary<Vector3I, BlockLocation>` method | The base connections of the blueprint for this subgrid: maps each base block position to the top subgrid and top part position it connects to. Only contains connections present in the blueprint. |
| `GetTopConnections(long projectorId, int subgridIndex)` | `Dictionary<Vector3I, BlockLocation>` method | The top connections of the blueprint for this subgrid: maps each top block position to the base subgrid and base part position it connects to. Only contains connections present in the blueprint. |
| `GetScanNumber(long projectorId)` | `long` method | The grid scan sequence number, incremented each time the preview grids/blocks change in any way in any subgrid. Reset to `0` when a blueprint is loaded, when the projector is cleared, or when it is turned OFF. |
| `GetYaml(long projectorId)` | `string` method | YAML representation of all information available via the API functions. Returns an empty string if the grid scan sequence number is `0`. The format may change incompatibly only on major version increases; new fields may be added without notice on any release. |
| `GetStateHash(long projectorId, int subgridIndex)` | `ulong` method | A hash of all block states of a subgrid, updated when the scan number increases. Changes only when a block state actually changes, so it can be polled to detect state changes efficiently. Reset to `0` when a blueprint is loaded, cleared, or the projector is turned OFF. |
| `IsSubgridComplete(long projectorId, int subgridIndex)` | `bool` method | `true` if the subgrid is fully built (completed). |

## MultigridProjectorModAgent

*`public class MultigridProjectorModAgent : IMultigridProjectorApi` (namespace `MultigridProjector.Api`)*

The client/PB-side adapter. A consumer instantiates it **once** (one instance serves every projector), and the constructor immediately performs the mod-message handshake described above. The agent stores the returned delegate array and forwards each interface call to the matching delegate slot, converting between the wire representation and the typed interface (for example, integer block states are cast to `BlockState`, and the flat connection lists returned by the delegates are recombined into `Dictionary<Vector3I, BlockLocation>` results). When the plugin is unavailable, every method returns a safe default rather than throwing.

| Member | Kind | Description |
| --- | --- | --- |
| `MultigridProjectorModAgent()` | constructor | Registers the response handler for `ModApiResponseId` and sends the request to `ModApiRequestId`, initiating the handshake. |
| `Available` | `bool` property (get) | `true` once a valid delegate array (length >= 12) has been received; `false` if the plugin is absent or incompatible. All methods short-circuit to defaults while `false`. |
| `Version` | `string` property (get) | Version string reported by the plugin (array slot `[0]`); `null` until a valid response arrives. |
| `GetSubgridCount` … `IsSubgridComplete` | methods | Implement every [`IMultigridProjectorApi`](#imultigridprojectorapi) member by casting and invoking the corresponding delegate (`api[1]`..`api[12]`). Return defaults when `Available` is `false`. |
| `WorkshopId`, `ModApiRequestId`, `ModApiResponseId` | private `const long` | Steam Workshop ID (`2415983416`) and the derived mod-message request/response channel IDs. |
| `HandleModMessage(object obj)` | private method | Response handler: validates the `object[]`, captures `Version` from slot `[0]`, and sets `Available = true`. |

## MultigridProjectorModShim

*`public class MultigridProjectorModShim : IMultigridProjectorApi, IDisposable` (namespace `MultigridProjector.Api`)*

A standalone fallback that a mod can use when the plugin is **not** installed, implementing the same interface so the consuming mod needs no duplicate logic. Unlike the agent, the shim is constructed **per projector** (it wraps one `IMyProjector`) and is `IDisposable` — it must be disposed once the projector closes or its data is no longer needed.

The shim only supports **single-grid** projection: `GetSubgridCount` returns `0` or `1`, the only valid `subgridIndex` is `0`, and the `projectorId` argument is ignored. It compares the preview grid against the built grid to derive block states, and there are no subgrid connections (`GetBaseConnections`/`GetTopConnections` return an empty dictionary). It emulates Multigrid Projector's grid-scan behavior: a scan sequence number is bumped (subject to a configurable cooldown) when changes occur, and a change counter is exposed in place of a real state hash so consumer optimizations that watch the scan number / hash still function. It subscribes to the built grid's block and grid events to detect changes, and detects projector restarts (preview grid replacement) and projection offset/rotation changes.

| Member | Kind | Description |
| --- | --- | --- |
| `MultigridProjectorModShim(IMyProjector projector, double scanCooldownSeconds = 2.0)` | constructor | Wraps `projector` and subscribes to its built grid's `OnBlockIntegrityChanged`, `OnBlockAdded`, `OnBlockRemoved`, `OnGridSplit`, and `OnGridMerge` events. `scanCooldownSeconds` throttles emulated scan increments. |
| `Dispose()` | method | Unsubscribes all grid event handlers. Must be called when the projector closes or the shim is no longer needed. |
| `Version` | `string` property (get) | Hard-coded `0.9.2`, matching the plugin's API version. |
| `GetSubgridCount` | method | Returns `1` if the projector is projecting, else `0`. |
| `GetOriginalGridBuilders` | method | Returns a single-item list built from the projected grid's object builder (cached); `null` if not projecting. |
| `GetPreviewGrid` | method | Returns `projector.ProjectedGrid` for `subgridIndex == 0` while projecting; otherwise `null`. |
| `GetBuiltGrid` | method | Returns `projector.CubeGrid` for `subgridIndex == 0` while projecting; otherwise `null`. |
| `GetBlockState` | method | Derives a `BlockState` by comparing the preview block to the built block (buildability, definition mismatch, integrity); `Unknown` if not projecting or `subgridIndex != 0`. |
| `GetBlockStates` | method | Fills `blockStates` for the preview blocks within `box` using the same comparison logic; returns `false` if not projecting or `subgridIndex != 0`. |
| `GetBaseConnections` / `GetTopConnections` | methods | Return an empty dictionary while projecting (single grid has no subgrid connections); `null` otherwise. |
| `GetScanNumber` | method | Returns the emulated scan number, incrementing it (after the cooldown) when a change has been registered; `0` if not projecting. Detects projector restart and projection config changes. |
| `GetYaml` | method | Returns a placeholder string; YAML is not implemented in the shim. |
| `GetStateHash` | method | Returns the emulated change counter in place of a real hash; `0` if not projecting or `subgridIndex != 0`. |
| `IsSubgridComplete` | method | `true` when the projector has blocks and `RemainingBlocks == 0`; `false` if not projecting or `subgridIndex != 0`. |

## BlockState

*`public enum BlockState` (namespace `MultigridProjector.Api`)*

The build state of a single projected block. The values are powers of two so they can be combined into a bitmask and passed to `GetBlockStates`'s `mask` parameter to filter results.

| Member | Value | Description |
| --- | --- | --- |
| `Unknown` | `0` | State is still unknown — not yet determined by the background worker. |
| `NotBuildable` | `1` | Not buildable due to lack of connectivity or colliding objects. |
| `Buildable` | `2` | Not built yet but ready to build (side connections are good and nothing collides). |
| `BeingBuilt` | `4` | Being built, but not yet to the integrity level the blueprint requires (needs more welding). |
| `FullyBuilt` | `8` | Built to the blueprint's required integrity level or more. |
| `Mismatch` | `128` | A block with a different definition than the blueprint requires occupies the projected block's place. |

## BlockLocation

*`public struct BlockLocation` (namespace `MultigridProjector.Api`)*

Identifies a block by its subgrid and position. Used as the value type in the `GetBaseConnections` / `GetTopConnections` maps to point at the block on the connected subgrid.

| Member | Kind | Description |
| --- | --- | --- |
| `GridIndex` | `readonly int` field | The subgrid index of the referenced block. |
| `Position` | `readonly Vector3I` field | The block position within that subgrid. |
| `BlockLocation(int gridIndex, Vector3I position)` | constructor | Initializes both fields. |
| `GetHashCode()` | method (override) | Combined hash of `GridIndex` and the three position components, so `BlockLocation` works as a dictionary key. |

## See also

- [API overview](../API.md) — parent document.
- [Core-Projection-Engine.md](./Core-Projection-Engine.md) — the engine-side `MultigridProjectorApiProvider` that produces the delegate array this API wraps.
- [Examples.md](./Examples.md) — worked Mod API and PB API usage examples.
