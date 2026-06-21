# Server Plugin Core

The server plugin is the dedicated-server counterpart to the client plugin. It is loaded by **Magnetar** (the SE dedicated server host) at startup via VRage's `IPlugin` interface. Because the server has no game UI, all configuration is managed remotely: `PluginConfig` is declared through **Magnetar's PluginSdk** so that **Quasar** can render its settings panel and push changes to the server over the network. The `Shared/` project items are compiled directly into this assembly alongside the server-specific code.

Key differences from the client plugin:

- No graphical UI — configuration is rendered and edited remotely by Quasar via Magnetar.
- Config is persisted to `MultigridProjector.cfg` (XML) in the server's user-data directory through PluginSdk's `ConfigStorage`, and is auto-saved on every property change.
- IL verification (`EnsureOriginal.VerifyAll`) runs on startup under old .NET Framework (pre-.NET 5) **unless** Wine/Proton is detected, preventing false-positive failures on Linux hosts.
- The session component (`PluginSession`) drives the core projection engine per simulation tick using `MyUpdateOrder.AfterSimulation`.
- **Patches are applied early — before world load — not from `IPlugin.Init`.** On the dedicated server `IPlugin.Init` runs only *after* the world (including grids that build from projectors during load) has already loaded, which is far too late for the projector patches. A namespace-less [`Preloader`](../../ServerPlugin/Preloader.cs) class lets Magnetar/Pulsar's bootstrap call into the plugin before the game starts; the plugin then installs a Harmony hook on `MyInitializer.InvokeBeforeRun` and applies its patches the moment the game's filesystem and logger are ready. See [Lifecycle](#lifecycle) and [Preloader](#preloader) below.

---

## Files

| File | Lines | Purpose |
|---|---|---|
| [Plugin.cs](../../ServerPlugin/Plugin.cs) | 253 | `IPlugin` entry point: early-bootstrap install, two-phase patching, config load/save, IL verify |
| [Preloader.cs](../../ServerPlugin/Preloader.cs) | 25 | Namespace-less bootstrap class located via `assembly.GetType("Preloader")`; its `Finish()` hook calls `Plugin.InstallEarlyBootstrap()` before the game starts |
| [PluginConfig.cs](../../ServerPlugin/PluginConfig.cs) | 20 | PluginSdk-declared configuration; exposes options to shared code via `IPluginConfig` |
| [PluginSession.cs](../../ServerPlugin/PluginSession.cs) | 32 | `MySessionComponentBase` that owns and drives `MultigridProjectorSession` |
| [PluginLogger.cs](../../ServerPlugin/PluginLogger.cs) | 33 | `IPluginLogger` implementation backed by `MyLog.Default` (the dedicated server log) |

---

## Lifecycle

Unlike the client, the server splits startup into an **early bootstrap** (before world load) and the
regular `IPlugin.Init` (after world load). The core work — config load, IL verify, patch application —
runs once, as early as possible, in `EarlyStartup()`. `Init` only adds a fallback and a deferred-patch
phase.

### Early bootstrap (the normal path)

1. **`Preloader.Finish()`** runs in Magnetar/Pulsar's `SetupPlugins`, before the game starts. It calls `Plugin.InstallEarlyBootstrap()`.
2. **`Plugin.InstallEarlyBootstrap()`** installs a Harmony **postfix** on `MyInitializer.InvokeBeforeRun` (under a separate `…multigridprojector.bootstrap` Harmony id, with no `[HarmonyPatch]` attribute so the patch scan never re-applies it). `InvokeBeforeRun` is the earliest safe trigger: its body calls `InitFileSystem` (so `MyFileSystem.UserDataPath` becomes available) and assigns `MyLog.Default` (so the game logger works) — both ready by the time the postfix runs. This method itself runs before `MyLog.Default` exists, so it logs failures to the console, not `PluginLog`.
3. When the game later runs `InvokeBeforeRun` (early in dedicated-server startup, before world-load compilation), the postfix **`OnGameInitialized()`** fires and calls `EarlyStartup()`.

### `EarlyStartup()` — one-shot core initialization

Guarded by a static `earlyStarted` flag (both callers run on the main thread, so a plain flag suffices). It:

1. Installs `PluginLogger` into `PluginLog.Logger` (the game logger is ready by now).
2. Resolves `configPath` as `Path.Combine(MyFileSystem.UserDataPath, "MultigridProjector.cfg")` and calls `LoadConfig(configPath)`:
   - On success: deserializes the XML via `ConfigStorage.LoadXml<PluginConfig>`, then immediately re-serializes it (normalizes / round-trips the file).
   - On failure (corrupt or missing file): logs the error, constructs a `new PluginConfig()` with defaults, attempts to save it (failure is silently swallowed), and continues with the default instance.
3. Subscribes `Config.PropertyChanged += OnConfigPropertyChanged` so that any change made by Quasar triggers an immediate `SaveConfig` call.
4. Assigns `MultigridProjector.Config.PluginConfig.Current = config` to expose the server config to all shared code through the `IPluginConfig` interface — **before** the patches run, so they read the configured values from the moment they execute (including during world load).
5. IL verification (old .NET Framework only, non-Wine): calls `EnsureOriginal.VerifyAll()`. If it throws `NotSupportedException`, sets the static `failed` flag, logs the error and **returns** — patches are not applied and the plugin is effectively disabled.
6. Calls `PatchHelpers.PatchUncategorized(Harmony)` to apply every patch **except** the deferred `"Late"` category, before world-load compilation. (See [Shared-Utilities.md → PatchHelpers](./Shared-Utilities.md#patchhelpers).)

Any exception is caught, sets `failed`, and is logged (to `PluginLog` if the logger exists, otherwise the console), so a startup failure never throws back into the game.

### Init (`Plugin.Init`) — fallback + late patches

Runs after the world has loaded. It:

1. Sets `Plugin.Instance`.
2. Calls `EarlyStartup()` again. This is **idempotent** — a no-op if the bootstrap path already ran. It is the fallback for the case where the preloader hook did not execute (expected only in **Magnetar safe mode**). If `failed`, returns immediately.
3. If the early path did *not* already run, logs a **warning** that patches were applied late and projector-dependent functionality may not have worked during world load.
4. Calls `PatchHelpers.PatchCategory(Harmony, PatchHelpers.LateCategory)` to apply any patches deferred to the `"Late"` category — for targets whose assembly is not loaded yet at the early bootstrap point. **Currently no patch uses this category**, so this applies zero patches; the two-phase mechanism is kept for future patches against late-loaded assemblies.

> **Why two phases?** Every patch targets `Sandbox.Game`, which is loaded long before the bootstrap hook, so all patches currently apply in the early phase. A future patch against an assembly not yet loaded at bootstrap can opt into the late phase with `[HarmonyPatchCategory(PatchHelpers.LateCategory)]`.

### Update (`Plugin.Update`)

Empty — no per-frame work is done at the `IPlugin` level. Per-simulation work is handled by `PluginSession`.

### Dispose (`Plugin.Dispose`)

1. Unsubscribes `PropertyChanged`, then calls `SaveConfig()` to persist the final config state.
2. Logs "Unloaded" and clears `PluginLog.Logger`.
3. Nulls out `Instance`.

---

## Plugin

*`public class Plugin : IPlugin` — namespace `ServerPlugin`*

The VRage plugin entry point, instantiated and called by Magnetar. Owns the `PluginConfig` instance and orchestrates startup.

| Member | Kind | Description |
|---|---|---|
| `Name` | `const string` | `"MultigridProjector"` — plugin identifier |
| `Instance` | `static Plugin` (get-only) | Singleton reference set during `Init`, cleared during `Dispose` |
| `Config` | `PluginConfig` (get) | The live configuration instance. Reads the static `config` field, which is loaded early (before the `IPlugin` instance exists); exposed as an instance property so Quasar's remote config UI can still discover it. |
| `InstallEarlyBootstrap()` | Static method | Called from `Preloader.Finish()` before the game starts. Installs the Harmony postfix on `MyInitializer.InvokeBeforeRun`. Falls back to console logging because `MyLog.Default` does not exist yet. |
| `OnGameInitialized()` | Static method | Harmony postfix on `MyInitializer.InvokeBeforeRun`; calls `EarlyStartup()`. Public so Harmony can resolve it; intentionally **not** `[HarmonyPatch]`-decorated so the patch scan never re-applies it. |
| `EarlyStartup()` | Private static method | One-shot core init (logger, config, IL verify, uncategorized patches), guarded by `earlyStarted`. `NoInlining` so `EnsureOriginal.VerifyAll()` resolves the plugin assembly from this stack frame. |
| `Init(object gameInstance)` | Method | Sets `Instance`, runs `EarlyStartup()` as a fallback, then applies the deferred `"Late"` patch category (see Lifecycle above) |
| `Update()` | Method | No-op; per-frame work is handled by `PluginSession` |
| `Dispose()` | Method | Saves config, unsubscribes events, clears logger and `Instance` |
| `LoadConfig(string path)` | Private static method | Deserialize-then-reserialize with fallback to defaults on error |
| `SaveConfig()` | Private static method | Serializes `config` to `configPath` via `ConfigStorage.SaveXml` |
| `OnConfigPropertyChanged(object, PropertyChangedEventArgs)` | Private static method | Calls `SaveConfig()`; logs errors without rethrowing |
| `Harmony` | Private static property | Creates a `new Harmony("com.spaceengineers.multigridprojector")` on each access |
| `config` / `configPath` | Private static fields | Hold the config and its path. Static (not instance) because they are populated in `EarlyStartup` before the `IPlugin` instance exists. |
| `earlyStarted` / `failed` | Private static fields | One-shot guard for `EarlyStartup` and a disabled-plugin flag checked in `Init`. |

---

## Preloader

*`public class Preloader` — **no namespace** (top-level type)*

The bootstrap entry point that lets the plugin run code **before the game starts**. Magnetar (and
Pulsar) locate this class via `assembly.GetType("Preloader")`, which only succeeds for a top-level
type with no namespace — hence the deliberate absence of a `namespace` declaration.

The plugin does **no Cecil pre-patching**, so `Preloader` declares neither `TargetDLLs` nor a `Patch`
method — only the `Finish()` post-hook. Magnetar still runs the hook because `HasPatches` counts
post-hooks.

| Member | Kind | Description |
|---|---|---|
| `Finish()` | Static method | Runs in `SetupPlugins`, before the game starts. Calls `ServerPlugin.Plugin.InstallEarlyBootstrap()`. |

---

## PluginConfig

*`public class PluginConfig : PluginSdk.Config.PluginConfig, IPluginConfig` — namespace `ServerPlugin`*

Declares all server-side configuration options. Inheriting from `PluginSdk.Config.PluginConfig` makes properties visible to Quasar's remote UI renderer. Implementing `MultigridProjector.Config.IPluginConfig` exposes them to shared code without a direct dependency on PluginSdk.

Properties use `SetField(ref field, value)` (provided by the PluginSdk base class) to raise `INotifyPropertyChanged.PropertyChanged`, which triggers auto-save in `Plugin.OnConfigPropertyChanged`.

Options are annotated with PluginSdk attributes that Quasar uses to build the settings panel:

| Member | Kind | Description |
|---|---|---|
| `PreviewBlockVisuals` | `bool` property, default `true` | **[BoolOption]** Controls whether the plugin manages the visual appearance of not-yet-built (preview) blocks. When enabled: buildable blocks appear as semi-transparent ghosts; blocks that cannot be built yet appear as holograms (or are hidden when "Show only buildable" is on); already-built blocks are hidden; and the projector's working sound and emissive state are driven accordingly. Disable only for compatibility with mods that manage preview-block transparency themselves. |

> **PluginSdk declaration note:** The `[BoolOption(...)]` attribute on `PreviewBlockVisuals` carries the full human-readable description shown in Quasar's UI. Magnetar reads this attribute at runtime to build the settings panel without any additional UI code in the plugin.

For the shared `IPluginConfig` interface definition and how shared code consumes `PluginConfig.Current`, see [Configuration.md](./Configuration.md).

---

## PluginSession

*`[MySessionComponentDescriptor(MyUpdateOrder.AfterSimulation)] public class PluginSession : MySessionComponentBase` — namespace `MultigridProjectorDedicated`*

A VRage session component registered with `MyUpdateOrder.AfterSimulation`. It owns the core projection engine and relays the VRage session lifecycle into it.

| Member | Kind | Description |
|---|---|---|
| `mgpSession` | Private `MultigridProjectorSession` | The shared core engine instance; see [Core-Projection-Engine.md](./Core-Projection-Engine.md) |
| `Init(MyObjectBuilder_SessionComponent)` | Override | Constructs `new MultigridProjectorSession()` |
| `UnloadData()` | Override | Calls `mgpSession.Dispose()` and nulls the field |
| `UpdateAfterSimulation()` | Override | Calls `mgpSession?.Update()` every simulation tick |

---

## PluginLogger

*`internal class PluginLogger : IPluginLogger` — namespace `MultigridProjectorDedicated`*

Bridges the shared `IPluginLogger` interface to the dedicated server's `MyLog.Default` logger. All methods are `[MethodImpl(AggressiveInlining)]` to eliminate call overhead.

| Member | Kind | Description |
|---|---|---|
| `Info(string msg)` | Method | Forwards to `MyLog.Default.Info` |
| `Debug(string msg)` | Method | Forwards to `MyLog.Default.Debug` |
| `Warn(string msg)` | Method | Forwards to `MyLog.Default.Warning` |
| `Error(string msg)` | Method | Forwards to `MyLog.Default.Error` |

For the `IPluginLogger` interface definition and the `PluginLog` static facade used throughout the codebase, see [Shared-Utilities.md](./Shared-Utilities.md).

---

## Cross-references

- [Core-Projection-Engine.md](./Core-Projection-Engine.md) — `MultigridProjectorSession` driven by `PluginSession`
- [Server-Patches.md](./Server-Patches.md) — Harmony patches applied early (before world load) via `PatchHelpers.PatchUncategorized`
- [Configuration.md](./Configuration.md) — `IPluginConfig` interface and `PluginConfig.Current` static accessor used by shared code
- [Shared-Utilities.md](./Shared-Utilities.md) — `PatchHelpers`, `IPluginLogger`, `PluginLog`, `EnsureOriginal`, `WineDetector`
- [../Installation.md](../Installation.md) — Server installation, config file location, Magnetar setup
