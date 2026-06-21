# Shared Utilities & Infrastructure

The `Shared/Utilities` folder is the cross-cutting infrastructure layer compiled into **both** the client plugin and the dedicated-server plugin. It is organised into seven concerns: (1) **logging abstraction** (`IPluginLogger`, `PluginLog`) that hides the concrete logger supplied by Pulsar/Magnetar; (2) **patch application, IL verification and Harmony transpiler helpers** (`PatchHelpers`, `EnsureOriginal`, `TranspilerHelpers`, `Hashing`, `Arithmetic`) that apply the plugin's Harmony patches (logging exactly which game methods were patched), hash game-method bodies at startup, and throw a descriptive error if the game has been updated in an incompatible way; (3) **concurrency** (`RwLock`, `RwLockDictionary`) providing a lightweight spin-based reader/writer lock used wherever projection state is read from the game thread while background threads may write; (4) **multiplayer comms** (`Comms`, `ExecLocation`) for detecting the runtime role (single-player / server / client) and routing plugin-to-plugin handshake packets; (5) **game-thread event helpers** (`Events`) for scheduling deferred work and subscribing to one-shot game events safely; (6) **environment detection** (`WineDetector`) to identify Wine/Proton hosts; and (7) **small math and build-time helpers** (`OrientationAlgebra`, `Validation`, `IgnoresAccessChecksToAttribute`, `GameAssembliesToPublicize`, `MultigridProjectorConfig`).

See also [Core-Projection-Engine.md](./Core-Projection-Engine.md) for how the projection engine consumes these helpers, [Shared-Patches.md](./Shared-Patches.md) for how Harmony patches use `EnsureOriginal` and `TranspilerHelpers`, [Build-And-Project-Layout.md](./Build-And-Project-Layout.md) for the publicizer/access-checks build pipeline, and [../Troubleshooting.md](../Troubleshooting.md) for diagnosing `EnsureOriginal` failures and Wine/Proton environment issues.

---

## Files

| File | Lines | Purpose |
|---|---|---|
| [`TranspilerHelpers.cs`](../../Shared/Utilities/TranspilerHelpers.cs) | 256 | Extension methods on `List<CodeInstruction>` for searching, mutating, hashing, and recording IL; `CodeInstructionNotFound` exception. |
| [`Comms.cs`](../../Shared/Utilities/Comms.cs) | 123 | Multiplayer role detection, secure-message routing, and server-has-plugin handshake. |
| [`EnsureOriginal.cs`](../../Shared/Utilities/EnsureOriginal.cs) | 111 | Class-level attribute that hashes game-method IL at startup and refuses to load if the hash does not match. |
| [`PatchHelpers.cs`](../../Shared/Utilities/PatchHelpers.cs) | 103 | Applies the plugin's Harmony patches (all / uncategorized / by category) and Info-logs exactly which game methods were patched, so a run can be verified from the log alone. |
| [`Events.cs`](../../Shared/Utilities/Events.cs) | 138 | Helpers for deferring actions to the game thread and subscribing to one-shot game events. |
| [`RwLock.cs`](../../Shared/Utilities/RwLock.cs) | 93 | Lightweight spin-based reader/writer lock with `using`-compatible `Reader`/`Writer` scope guards. |
| [`Hashing.cs`](../../Shared/Utilities/Hashing.cs) | 84 | FNV-1a string hash, IL instruction sequence hasher, and hash-code combiner (extension methods). |
| [`WineDetector.cs`](../../Shared/Utilities/WineDetector.cs) | 61 | Detects Wine/Proton via `ntdll.dll!wine_get_version` and environment variables. |
| [`OrientationAlgebra.cs`](../../Shared/Utilities/OrientationAlgebra.cs) | 60 | Converts a `(forward, up)` direction pair to the `Vector3I` projection rotation used by the projector. |
| [`PluginLog.cs`](../../Shared/Utilities/PluginLog.cs) | 56 | Static facade (`Info`/`Debug`/`Warn`/`Error`) that delegates to the registered `IPluginLogger`. |
| [`RwLockDictionary.cs`](../../Shared/Utilities/RwLockDictionary.cs) | 43 | `Dictionary<TKey,TValue>` subclass that embeds an `RwLock` and exposes `Read()`/`Write()` scopes. |
| [`Arithmetic.cs`](../../Shared/Utilities/Arithmetic.cs) | 33 | Stand-alone hash-code combiner (same algorithm as `Hashing.CombineHashCodes`; used by `EnsureOriginal`). |
| [`IgnoresAccessChecksToAttribute.cs`](../../Shared/Utilities/IgnoresAccessChecksToAttribute.cs) | 24 | Declares `System.Runtime.CompilerServices.IgnoresAccessChecksToAttribute` for non-`DEV_BUILD` builds where Krafs.Publicizer is not active. |
| [`ExecLocation.cs`](../../Shared/Utilities/ExecLocation.cs) | 22 | Marker attributes (`[Everywhere]`, `[ServerOnly]`, `[ClientOnly]`) for annotating patch methods by execution context. |
| [`Validation.cs`](../../Shared/Utilities/Validation.cs) | 15 | `EnsureInfo<T>` guard that converts a `null` `AccessTools` result into a descriptive exception. |
| [`MultigridProjectorConfig.cs`](../../Shared/Utilities/MultigridProjectorConfig.cs) | 11 | Stub configuration class (currently compiled out with `#if UNUSED`). |
| [`IPluginLogger.cs`](../../Shared/Utilities/IPluginLogger.cs) | 10 | Logger interface implemented by the host (Pulsar/Magnetar). |
| [`GameAssembliesToPublicize.cs`](../../Shared/Utilities/GameAssembliesToPublicize.cs) | 9 | Assembly-level `[IgnoresAccessChecksTo]` declarations for `Sandbox.Game`, `SpaceEngineers.Game`, and `Sandbox.Graphics`. |

---

## IPluginLogger

_`public interface IPluginLogger` — namespace `MultigridProjector.Utilities`_

The logger contract that the host environment (Pulsar on the client, Magnetar on the server) injects at startup by assigning `PluginLog.Logger`. All plugin code logs through the static `PluginLog` facade; the host decides where messages actually go (file, in-game console, etc.).

| Member | Kind | Description |
|---|---|---|
| `Info(string msg)` | method | Log an informational message. |
| `Debug(string msg)` | method | Log a debug-level message (may be suppressed in release builds). |
| `Warn(string msg)` | method | Log a warning. |
| `Error(string msg)` | method | Log an error. |

---

## PluginLog

_`public static class PluginLog` — namespace `MultigridProjector.Utilities`_

Static facade over `IPluginLogger`. Every call prepends the `"Multigrid Projector: "` prefix automatically. Must be initialised by the host before any plugin code runs (`PluginLog.Logger = <implementation>`). Throws a descriptive `Exception` if called before initialisation.

| Member | Kind | Description |
|---|---|---|
| `Logger` | `static IPluginLogger` | Set once by the host at startup; holds the concrete logger. |
| `Prefix` | `static string` | String prepended to every message; defaults to `"Multigrid Projector: "`. |
| `Info(string msg)` | static method | Delegate to `Logger.Info` with prefix. |
| `Debug(string msg)` | static method | Delegate to `Logger.Debug` with prefix. |
| `Warn(string msg)` | static method | Delegate to `Logger.Warn` with prefix. |
| `Error(string msg)` | static method | Delegate to `Logger.Error` with prefix. |
| `Error(Exception e, string msg="")` | static method | Format exception + optional message and delegate to `Logger.Error`. |

---

## EnsureOriginal

_`[AttributeUsage(AttributeTargets.Class)] public class EnsureOriginal : Attribute` — namespace `MultigridProjector.Utilities`_

A class-level attribute placed on Harmony patch classes alongside `[HarmonyPatch]`. When `EnsureOriginal.VerifyAll()` is called once at plugin load time, it scans every type in the calling assembly for `[HarmonyPatch]` + `[EnsureOriginal]` pairs. For each such pair it hashes the IL body of the patched game method (opcodes, value-type operands, string operands, labels) using `Arithmetic.CombineHashCodes` and compares the hex digest against the list of allowed digests supplied to the attribute. If none match the plugin refuses to load with a human-readable error listing the changed method names and the expected vs. actual digests.

Setting the environment variable `SE_PLUGIN_DISABLE_METHOD_VERIFICATION=1` bypasses hash checking in `TranspilerHelpers.VerifyCodeHash` (but **not** `EnsureOriginal.VerifyAll` itself — that path uses `Arithmetic.CombineHashCodes` directly). See [../Troubleshooting.md](../Troubleshooting.md) for guidance on updating digests after a game update.

| Member | Kind | Description |
|---|---|---|
| `EnsureOriginal(params string[] allowedHexDigests)` | constructor | Accept one or more 8-character lowercase hex digests that are all considered valid. Multiple digests allow a patch class to remain valid across minor game patches. |
| `VerifyAll()` | static method | Entry point called at startup. Reflects the calling assembly, finds all `[HarmonyPatch]+[EnsureOriginal]` classes, hashes each target method, and throws `NotSupportedException` listing every mismatch. |

Usage example (see [Shared-Patches.md](./Shared-Patches.md) for real instances):

```csharp
[HarmonyPatch(typeof(MyProjectorBase), nameof(MyProjectorBase.Build))]
[EnsureOriginal("1a2b3c4d", "5e6f7a8b")]  // hex digests for game versions 1.x and 1.y
internal static class MyProjectorBase_Build
{
    static IEnumerable<CodeInstruction> Transpiler(IEnumerable<CodeInstruction> instructions) { … }
}
```

---

## PatchHelpers

_`public static class PatchHelpers` — namespace `MultigridProjector.Utilities`_

The single entry point both plugins use to apply their Harmony patches. It wraps Harmony's
`PatchAll` family so that **every applied patch is logged**, and supports the dedicated server's
two-phase startup (apply most patches early, defer a category to `IPlugin.Init`).

**Why the per-patch lines log at `Info`, not `Debug`:** the game's `MyLog.Default.Debug` is
`[Conditional("DEBUG")]` and is therefore compiled out of the Release builds that ship to Magnetar and
Pulsar. `Info` is the lowest level that survives into the build users actually run, so it is the only
level at which patch application can be verified from the logs. Each applied patch is logged as
`Namespace.Type.Method(argTypes) <- PatchClass[, …]` with a running count, followed by a summary line.

| Member | Kind | Description |
|---|---|---|
| `LateCategory` | `const string` (`"Late"`) | Harmony patch category for patches deferred to `IPlugin.Init` because their target assembly is not loaded yet at the dedicated server's early bootstrap point. No patch currently uses it; the mechanism is kept for future late-loaded targets, which opt in with `[HarmonyPatchCategory(PatchHelpers.LateCategory)]`. |
| `PatchAll(Harmony)` | static method | Applies **every** patch in the executing assembly (`PatchAll`). Used by the **client** (Pulsar), whose `IPlugin.Init` already runs before world load. |
| `PatchUncategorized(Harmony)` | static method | Applies everything **except** the `"Late"` category (`PatchAllUncategorized`). Used by the **dedicated server's early bootstrap**, before world-load compilation. |
| `PatchCategory(Harmony, category)` | static method | Applies only the patches in the given category. Used by the dedicated server from `IPlugin.Init`, once late-loaded target assemblies exist. |

Internally `ApplyAndLog` snapshots `harmony.GetPatchedMethods()` before applying, then reports exactly
the methods the current phase added — `GetPatchedMethods()` is scoped to `harmony.Id`, so the
before/after delta isolates each phase even though the dedicated server applies two phases under the
same id. See [Server-Plugin.md → Lifecycle](./Server-Plugin.md#lifecycle) for the two-phase flow; the
Info-level patch lines let patch timing be verified from the server and client logs.

---

## TranspilerHelpers

_`public static class TranspilerHelpers` — namespace `MultigridProjector.Utilities`_

Extension methods on `List<CodeInstruction>` (the input/output type of Harmony transpilers) that make it practical to write robust, self-verifying transpilers. All search methods throw `CodeInstructionNotFound` if a match is not found, giving clear crash messages instead of silent no-ops.

The environment variable `SE_PLUGIN_DISABLE_METHOD_VERIFICATION` (any value other than `"0"`) suppresses hash-mismatch exceptions from `VerifyCodeHash`, which can be useful for testing on untested game builds.

| Member | Kind | Description |
|---|---|---|
| `FindAllIndex(predicate)` | extension method | Returns a `List<int>` of all indices where `CodeInstructionPredicate` is satisfied. |
| `GetField(predicate)` | extension method | Finds the first `ldfld`/`stfld` instruction whose `FieldInfo` satisfies `FieldInfoPredicate`; throws `CodeInstructionNotFound` on failure. |
| `FindPropertyGetter(name)` | extension method | Finds the `call get_<name>` instruction; throws `CodeInstructionNotFound` on failure. |
| `FindPropertySetter(name)` | extension method | Finds the `call set_<name>` instruction; throws `CodeInstructionNotFound` on failure. |
| `GetLabel(predicate)` | extension method | Returns the `Label` operand of the first instruction whose opcode satisfies `OpcodePredicate`. |
| `RemoveFieldInitialization(name)` | extension method | Removes the 3-instruction `ldarg.0` / `newobj` / `stfld` sequence that initialises a named field; throws `CodeInstructionNotFound` if the pattern is not found. |
| `Hash()` | extension method | Returns an 8-character lowercase hex string summarising the IL sequence (delegates to `HashInstructions().CombineHashCodes()`). |
| `VerifyCodeHash(patchedMethod, expected)` | extension method | Compares `Hash()` against `expected`; throws `Exception` describing the mismatch unless `SE_PLUGIN_DISABLE_METHOD_VERIFICATION` is set. |
| `RecordOriginalCode(patchedMethod)` | extension method | **Debug only.** Writes `<MethodName>.original.il` next to the calling source file when the IL changes. |
| `RecordPatchedCode(patchedMethod)` | extension method | **Debug only.** Writes `<MethodName>.patched.il` next to the calling source file when the IL changes. |
| `RecordCustomCode(il, suffix, patchedMethod)` | extension method | **Debug only.** Writes `<MethodName>.<suffix>.il` — general-purpose snapshot helper. |
| `DeepClone(CodeInstruction)` | extension method | Returns a deep copy of a single `CodeInstruction` including cloned label and exception-block lists. |
| `DeepClone(IEnumerable<CodeInstruction>)` | extension method | Deep-clones an entire IL sequence as a new `List<CodeInstruction>`. |
| `OpcodePredicate` | delegate | `bool(OpCode)` — predicate over an opcode. |
| `CodeInstructionPredicate` | delegate | `bool(CodeInstruction)` — predicate over a full instruction. |
| `FieldInfoPredicate` | delegate | `bool(FieldInfo)` — predicate over the field referenced by an instruction. |

### CodeInstructionNotFound

_`public class CodeInstructionNotFound : Exception`_

Thrown by `TranspilerHelpers` search methods when no matching instruction is found. Carries a descriptive message indicating which kind of search failed.

---

## Hashing

_`public static class Hashing` — namespace `MultigridProjector.Utilities`_

Extension methods for producing stable, order-sensitive hashes of strings and IL sequences. Used by `TranspilerHelpers.VerifyCodeHash` and directly in `EnsureOriginal` (via `Arithmetic.CombineHashCodes`). The string hash is FNV-1a (32-bit). The instruction-sequence hash covers opcodes, value-type operands, string operands, and branch labels; it deliberately excludes reference-type operands (e.g. `MethodBase`, `FieldInfo`) because those are bound at JIT time and not stable across runs.

| Member | Kind | Description |
|---|---|---|
| `Hash(this string value)` | extension method | FNV-1a 32-bit hash of a string; returns `int`. |
| `HashBody(this MethodInfo methodInfo)` | extension method | Hash the current (post-patch) IL body of a method via `PatchProcessor.GetCurrentInstructions`. |
| `HashBody(this ConstructorInfo constructorInfo)` | extension method | Hash the current IL body of a constructor. |
| `HashInstructions(this IEnumerable<CodeInstruction>)` | extension method | Yield one `int` per meaningful IL token; consumed by `CombineHashCodes`. |
| `CombineHashCodes(this IEnumerable<int>)` | extension method | Combine a sequence of hashes into one `int` using the djb2-variant two-accumulator algorithm. |

---

## Arithmetic

_`public static class Arithmetic` — namespace `MultigridProjector.Utilities`_

A minimal static helper holding the hash-code combiner used by `EnsureOriginal` (which cannot call the `Hashing` extension method because it lives in a different compilation unit that avoids circular dependencies).

| Member | Kind | Description |
|---|---|---|
| `CombineHashCodes(IEnumerable<int> hashCodes)` | static method | Djb2-variant two-accumulator combiner; identical algorithm to `Hashing.CombineHashCodes`. |

---

## RwLock

_`public class RwLock` — namespace `MultigridProjector.Utilities`_

A lightweight spin-wait reader/writer lock backed by a single `int` field. Negative value (`-1`) means a writer holds the lock; positive values are the concurrent reader count; zero means unlocked. Designed for use with C# `using` blocks via the inner `Reader` and `Writer` scope guards, which acquire the lock in their constructor and release it in `Dispose`.

```csharp
// read-side critical section
using (myLock.Read()) { … }

// write-side critical section
using (myLock.Write()) { … }
```

| Member | Kind | Description |
|---|---|---|
| `Read()` | method | Acquire a read scope; blocks (spins) until no writer holds the lock. Returns `Reader`. |
| `Write()` | method | Acquire a write scope; blocks (spins) until all readers and writers have released. Returns `Writer`. |
| `Reader` (nested class) | `IDisposable` | Holds a read lock from construction until `Dispose`. |
| `Writer` (nested class) | `IDisposable` | Holds the exclusive write lock from construction until `Dispose`. |

The implementation uses `Interlocked.CompareExchange` with `SpinWait` for both reader and writer paths; there are no kernel-mode waits and no allocations beyond the scope guard objects.

---

## RwLockDictionary\<TKey, TValue\>

_`public class RwLockDictionary<TKey, TValue> : Dictionary<TKey, TValue>` — namespace `MultigridProjector.Utilities`_

A `Dictionary<TKey, TValue>` that embeds an `RwLock` and exposes `Read()` / `Write()` scope methods. Callers wrap dictionary access in a `using` block rather than managing a separate lock object.

```csharp
using (dict.Read())  { value = dict[key]; }
using (dict.Write()) { dict[key] = value; }
```

Constructors mirror `Dictionary<TKey,TValue>` (capacity, comparer, copy-from-dictionary, combinations).

| Member | Kind | Description |
|---|---|---|
| `Read()` | method | Delegates to the embedded `RwLock.Read()`. |
| `Write()` | method | Delegates to the embedded `RwLock.Write()`. |

---

## Comms

_`public class Comms : IDisposable` — namespace `MultigridProjector.Utilities`_

Manages the plugin-level multiplayer presence. On construction it detects the runtime role and registers a secure-message handler (handler ID `0x7b94`). In `MultiplayerClient` role it listens for a specific 8-byte signature packet from the server and sets `ServerHasPlugin = true` when it arrives; in `MultiplayerServer` / `DedicatedServer` role it fires that packet at every connecting player via `MyVisualScriptLogicProvider.PlayerConnected`. The static `PacketReceived` event is the general routing point: other subsystems subscribe to it and filter by content.

`Dispose` unregisters the secure-message handler and the `PlayerConnected` hook to prevent leaks across hot-reload cycles.

| Member | Kind | Description |
|---|---|---|
| `Role` | `static Role` | The detected role for this session (set in the constructor). |
| `ServerHasPlugin` | `static bool` | `true` once the server is known to have the plugin installed (always `true` in single-player and on the server itself). |
| `PacketReceived` | `static event OnPacketReceived` | Fired for every incoming secure-message packet after signature dispatch; subscribers receive `(byte[] data, ulong fromSteamId, bool fromServer)`. |
| `Comms()` | constructor | Detects role, registers handler, schedules deferred handshake logic via `Events.InvokeOnGameThread`. |
| `Dispose()` | method | Unregisters secure-message handler and event hooks. |
| `SendToServer<T>(handlerId, packet, reliable)` | static method | Serialize `packet` with `MyAPIGateway.Utilities.SerializeToBinary` and send to the server. |
| `SendToClient<T>(handlerId, packet, steamId, reliable)` | static method | Serialize `packet` and send to a specific client by Steam ID. |

### Role (enum)

| Value | Meaning |
|---|---|
| `SinglePlayer` | No multiplayer session; the local player is both client and server. |
| `MultiplayerServer` | Listen server (also the local client). |
| `MultiplayerClient` | Connected to a remote server. |
| `DedicatedServer` | `MyAPIGateway.Utilities.IsDedicated` is `true`; no local client. |

---

## Events

_`internal class Events` — namespace `MultigridProjector.Utilities`_

Static helpers for deferring work to the game thread and for attaching one-shot event listeners to game objects. The `InvokeOnGameThread` wrapper adds a `try/catch` in release builds because callbacks invoked by the game engine bypass the plugin's top-level error handlers; exceptions would otherwise crash the game process.

| Member | Kind | Description |
|---|---|---|
| `InvokeOnGameThread(task, frames)` | static method | Schedule `task` to run on the game thread. `frames <= 0` means next frame; positive values delay by that many gameplay frames. In release builds `task` is wrapped in a `try/catch` that logs to `PluginLog.Error`. |
| `OnNextFatBlockAdded(grid, action, predicate)` | static method | Subscribe a one-shot callback for the next `MyCubeGrid.OnFatBlockAdded` event that satisfies `predicate`. Handles replication delay: if the block is a terminal block with no properties yet, it re-defers for 2 frames and retries. |
| `OnNextAttachedChanged(baseBlock, action, predicate)` | static method | Subscribe a one-shot callback for the next `MyMechanicalConnectionBlockBase.OnAttachedChanged` event satisfying `predicate`. |
| `OnBlockSpawned(action, predicate)` | static method | Subscribe a one-shot callback on `MyEntities.OnEntityAdd` filtered to single-block grids (newly welded blocks). |
| `InvokeOnEvent<TObject,TEvent1>(owner, attach, detach, action, predicate, delay)` | static method | Generic one-shot event subscription primitive: attaches a handler, and when the predicate passes, detaches it and schedules the action via `InvokeOnGameThread`. |

---

## WineDetector

_`public static class WineDetector` — namespace `MultigridProjectorServer.MultigridProjector.Utilities`_

Detects whether the dedicated server process is running inside Wine or Proton on Linux. Used to apply compatibility workarounds where behaviour differs between native Windows and Wine. See [../Troubleshooting.md](../Troubleshooting.md) for notes on known Wine/Proton issues.

Detection strategy (in order):
1. P/Invoke `ntdll.dll!wine_get_version` — present only in Wine's `ntdll.dll`.
2. Environment variables: `WINE_WINDOWS_DIR`, `WINELOADERNOEXEC`, `PROTON_VERSION`.
3. `STEAM_RUNTIME` environment variable containing `"steamrt"` (Proton Steam Runtime).

| Member | Kind | Description |
|---|---|---|
| `IsRunningInWineOrProton()` | static method | Returns `true` if any Wine/Proton indicator is found; `false` on native Windows. Swallows `DllNotFoundException` and other exceptions gracefully. |

---

## OrientationAlgebra

_`public static class OrientationAlgebra` — namespace `MultigridProjector.Utilities`_

Converts a `(Base6Directions.Direction forward, Base6Directions.Direction up)` pair into the `Vector3I` projection-rotation value used by the projector block. The lookup is backed by two pre-computed arrays indexed by `(forward * 6 + up) % 36`: `ValidOrientations` (a `bool[36]` that rejects geometrically impossible combinations) and `ProjectionRotations` (a `Vector3I[36]` holding the rotation for valid pairs).

| Member | Kind | Description |
|---|---|---|
| `ProjectionRotationFromForwardAndUp(forward, up, out rotation)` | static method | Returns `true` and sets `rotation` when the orientation is geometrically valid; returns `false` and `Vector3I.Zero` for impossible (forward == up) combinations. |

---

## ExecLocation — execution-context marker attributes

_Namespace `MultigridProjector.Utilities`_

Three `[AttributeUsage(AttributeTargets.Method)]` attributes used as documentation annotations on patch method implementations to make the intended execution context clear at a glance. They have no runtime effect; they are purely for readability and static-analysis tooling.

| Attribute | Meaning |
|---|---|
| `[Everywhere]` | The annotated method runs on both server and client. |
| `[ServerOnly]` | The annotated method runs only on the server side. |
| `[ClientOnly]` | The annotated method runs only on the client side. |

---

## Validation

_`public static class Validation` — namespace `MultigridProjector.Utilities`_

A single guard method that converts a `null` return from `AccessTools` reflection helpers into a descriptive exception that hints the developer to enable `Harmony.DEBUG = true`.

| Member | Kind | Description |
|---|---|---|
| `EnsureInfo<T>(T info) where T : class` | static method | Returns `info` unchanged if non-null; throws `Exception` with a `Harmony.DEBUG` hint if `info` is `null`. |

---

## IgnoresAccessChecksToAttribute & GameAssembliesToPublicize

_`System.Runtime.CompilerServices.IgnoresAccessChecksToAttribute` — conditional declaration in `IgnoresAccessChecksToAttribute.cs`_

The `Krafs.Publicizer` NuGet package emits `[IgnoresAccessChecksTo]` assembly attributes automatically when building in an IDE (`DEV_BUILD`). When Pulsar/Magnetar builds the plugin without Krafs, the attribute declaration must be present in the plugin assembly itself; `IgnoresAccessChecksToAttribute.cs` provides it under `#if !DEV_BUILD`.

`GameAssembliesToPublicize.cs` contains the three concrete `[assembly: IgnoresAccessChecksTo("…")]` usages that tell the runtime to suppress internal/private access checks for the publicized game assemblies. These must be kept in sync with the `<Publicize>` items in `ClientPlugin.csproj` and `ServerPlugin.csproj` — see [Build-And-Project-Layout.md](./Build-And-Project-Layout.md).

| Assembly publicized | Notes |
|---|---|
| `Sandbox.Game` | Core game logic; required on both client and server. |
| `SpaceEngineers.Game` | Game-specific types; required on both client and server. |
| `Sandbox.Graphics` | Rendering types; only used by the client but the attribute is harmless on the server. |

---

## MultigridProjectorConfig (stub)

_`public static class MultigridProjectorConfig` — namespace `MultigridProjector.Utilities`_ _(currently compiled out with `#if UNUSED`)_

A placeholder for future plugin configuration (block-limit and PCU-limit toggles). The class body is guarded by `#if UNUSED` and contributes nothing to the current build.

---

```json
{
  "module": "shared-utilities",
  "page": "Shared-Utilities.md",
  "overview": "Cross-cutting infrastructure compiled into both the client and server plugin. Covers logging abstraction (IPluginLogger/PluginLog), IL verification at startup (EnsureOriginal), Harmony transpiler helpers (TranspilerHelpers, Hashing, Arithmetic), a spin-based reader/writer lock (RwLock, RwLockDictionary), multiplayer role detection and packet routing (Comms), safe game-thread scheduling and one-shot event helpers (Events), Wine/Proton environment detection (WineDetector), and small math/build-time helpers (OrientationAlgebra, Validation, IgnoresAccessChecksToAttribute, GameAssembliesToPublicize).",
  "files": [
    {"path": "Shared/Utilities/TranspilerHelpers.cs", "summary": "Extension methods on List<CodeInstruction> for searching, mutating, hashing, and recording IL; CodeInstructionNotFound exception."},
    {"path": "Shared/Utilities/Comms.cs", "summary": "Multiplayer role detection, secure-message handler registration, and server-has-plugin handshake."},
    {"path": "Shared/Utilities/EnsureOriginal.cs", "summary": "Class-level attribute that hashes game-method IL at startup and refuses to load if the hash does not match any allowed digest."},
    {"path": "Shared/Utilities/PatchHelpers.cs", "summary": "Applies the plugin's Harmony patches (all / uncategorized / by category) and Info-logs exactly which game methods were patched; supports the dedicated server's two-phase (early + Late category) startup."},
    {"path": "Shared/Utilities/Events.cs", "summary": "InvokeOnGameThread wrapper with release-build safety, plus one-shot game-event subscription helpers."},
    {"path": "Shared/Utilities/RwLock.cs", "summary": "Spin-based reader/writer lock with using-compatible Reader/Writer scope guards."},
    {"path": "Shared/Utilities/Hashing.cs", "summary": "FNV-1a string hash, IL instruction sequence hasher, and hash-code combiner as extension methods."},
    {"path": "Shared/Utilities/WineDetector.cs", "summary": "Detects Wine/Proton via P/Invoke and environment variable inspection."},
    {"path": "Shared/Utilities/OrientationAlgebra.cs", "summary": "Converts (forward, up) direction pair to Vector3I projection rotation via pre-computed lookup tables."},
    {"path": "Shared/Utilities/PluginLog.cs", "summary": "Static logging facade that prepends the plugin name prefix and delegates to the injected IPluginLogger."},
    {"path": "Shared/Utilities/RwLockDictionary.cs", "summary": "Dictionary subclass that embeds an RwLock and exposes Read()/Write() scope methods."},
    {"path": "Shared/Utilities/Arithmetic.cs", "summary": "Stand-alone hash-code combiner used by EnsureOriginal."},
    {"path": "Shared/Utilities/IgnoresAccessChecksToAttribute.cs", "summary": "Conditional declaration of IgnoresAccessChecksToAttribute for non-DEV_BUILD (Pulsar/Magnetar) builds."},
    {"path": "Shared/Utilities/ExecLocation.cs", "summary": "Marker attributes (Everywhere, ServerOnly, ClientOnly) annotating patch methods by execution context."},
    {"path": "Shared/Utilities/Validation.cs", "summary": "EnsureInfo<T> guard converting null AccessTools results to descriptive exceptions."},
    {"path": "Shared/Utilities/MultigridProjectorConfig.cs", "summary": "Stub configuration class compiled out with #if UNUSED; placeholder for future block/PCU-limit settings."},
    {"path": "Shared/Utilities/IPluginLogger.cs", "summary": "Logger interface implemented by the host (Pulsar/Magnetar) and injected into PluginLog.Logger."},
    {"path": "Shared/Utilities/GameAssembliesToPublicize.cs", "summary": "Assembly-level IgnoresAccessChecksTo declarations for Sandbox.Game, SpaceEngineers.Game, and Sandbox.Graphics."}
  ],
  "key_types": [
    "EnsureOriginal — class-level attribute that hashes game-method IL at startup and aborts plugin load on mismatch",
    "PatchHelpers — applies Harmony patches (all/uncategorized/category) with Info-level per-patch logging; LateCategory constant for the dedicated server's two-phase startup",
    "TranspilerHelpers — extension methods for searching/mutating/hashing IL instruction lists in Harmony transpilers",
    "Hashing — FNV-1a string hash and IL instruction-sequence hasher used by TranspilerHelpers and EnsureOriginal",
    "Arithmetic — standalone hash-code combiner used by EnsureOriginal",
    "RwLock — lightweight spin-based reader/writer lock with using-scoped Reader/Writer guards",
    "RwLockDictionary<TKey,TValue> — Dictionary with embedded RwLock and Read()/Write() scope methods",
    "Comms — multiplayer role detection, secure packet routing, and server-has-plugin handshake",
    "Events — InvokeOnGameThread with release-build safety and one-shot game-event subscription helpers",
    "IPluginLogger — logger interface injected by the host; abstracted through PluginLog static facade",
    "PluginLog — static logging facade with plugin-name prefix",
    "WineDetector — detects Wine/Proton via P/Invoke and environment variables",
    "OrientationAlgebra — converts (forward, up) direction pair to projection rotation via lookup tables",
    "IgnoresAccessChecksToAttribute — runtime declaration enabling publicized-assembly access outside DEV_BUILD",
    "ExecLocation (Everywhere/ServerOnly/ClientOnly) — execution-context annotation attributes",
    "Validation.EnsureInfo — null guard for AccessTools reflection results"
  ],
  "depends_on": [
    "HarmonyLib (Harmony 2.x) — CodeInstruction, PatchProcessor, AccessTools, HarmonyPatch",
    "Sandbox.ModAPI — MyAPIGateway, IMyTerminalBlock",
    "Sandbox.Game — MyCubeGrid, MyMechanicalConnectionBlockBase, MyEntities, MySession, MyVisualScriptLogicProvider",
    "VRageMath — Vector3I, Base6Directions",
    "System.Runtime.InteropServices — P/Invoke for WineDetector",
    "System.Threading — Interlocked, SpinWait"
  ],
  "used_by": ["shared-logic", "client-core", "server-core", "shared-patches"],
  "cross_refs": [
    "Docs/Reference/Core-Projection-Engine.md",
    "Docs/Reference/Shared-Patches.md",
    "Docs/Reference/Build-And-Project-Layout.md",
    "Docs/Troubleshooting.md"
  ],
  "notes": "PatchHelpers is the single entry point both plugins use to apply Harmony patches, logging every patched game method at Info (not Debug, which is compiled out of release builds) so patch application and timing can be verified from the shipped logs; PatchAll for the client, PatchUncategorized + PatchCategory(Late) for the dedicated server's two-phase early/late startup. EnsureOriginal hashes game-method IL at plugin load and throws NotSupportedException listing every changed method, preventing silent misbehaviour after game updates. TranspilerHelpers.VerifyCodeHash offers the same safety inline in transpiler methods and can be bypassed with SE_PLUGIN_DISABLE_METHOD_VERIFICATION. RwLock is a pure spin-wait lock with no kernel waits, suited to the short critical sections in projection state access. Comms auto-detects SinglePlayer/MultiplayerServer/MultiplayerClient/DedicatedServer at construction time and sends a 8-byte signature handshake so clients can confirm the server also has the plugin. WineDetector uses P/Invoke on ntdll.dll plus environment-variable fallbacks to distinguish native Windows from Wine/Proton on Linux."
}
```
