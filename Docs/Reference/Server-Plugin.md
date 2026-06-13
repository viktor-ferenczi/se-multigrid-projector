# Server Plugin Core

The server plugin is the dedicated-server counterpart to the client plugin. It is loaded by **Magnetar** (the SE dedicated server host) at startup via VRage's `IPlugin` interface. Because the server has no game UI, all configuration is managed remotely: `PluginConfig` is declared through **Magnetar's PluginSdk** so that **Quasar** can render its settings panel and push changes to the server over the network. The `Shared/` project items are compiled directly into this assembly alongside the server-specific code.

Key differences from the client plugin:

- No graphical UI — configuration is rendered and edited remotely by Quasar via Magnetar.
- Config is persisted to `MultigridProjector.cfg` (XML) in the server's user-data directory through PluginSdk's `ConfigStorage`, and is auto-saved on every property change.
- IL verification (`EnsureOriginal.VerifyAll`) runs on startup under old .NET Framework (pre-.NET 5) **unless** Wine/Proton is detected, preventing false-positive failures on Linux hosts.
- The session component (`PluginSession`) drives the core projection engine per simulation tick using `MyUpdateOrder.AfterSimulation`.

---

## Files

| File | Lines | Purpose |
|---|---|---|
| [Plugin.cs](../../ServerPlugin/Plugin.cs) | 142 | `IPlugin` entry point: config load/save, IL verify, `Harmony.PatchAll` |
| [PluginConfig.cs](../../ServerPlugin/PluginConfig.cs) | 20 | PluginSdk-declared configuration; exposes options to shared code via `IPluginConfig` |
| [PluginSession.cs](../../ServerPlugin/PluginSession.cs) | 32 | `MySessionComponentBase` that owns and drives `MultigridProjectorSession` |
| [PluginLogger.cs](../../ServerPlugin/PluginLogger.cs) | 33 | `IPluginLogger` implementation backed by `MyLog.Default` (the dedicated server log) |

---

## Lifecycle

### Init (`Plugin.Init`)

1. Sets `Plugin.Instance` and installs `PluginLogger` into `PluginLog.Logger`.
2. Resolves `configPath` as `Path.Combine(MyFileSystem.UserDataPath, "MultigridProjector.cfg")`.
3. Calls `LoadConfig(configPath)`:
   - On success: deserializes the XML via `ConfigStorage.LoadXml<PluginConfig>`, then immediately re-serializes it (normalizes / round-trips the file).
   - On failure (corrupt or missing file): logs the error, constructs a `new PluginConfig()` with defaults, attempts to save it (failure is silently swallowed), and continues with the default instance.
4. Subscribes `Config.PropertyChanged += OnConfigPropertyChanged` so that any change made by Quasar triggers an immediate `SaveConfig` call.
5. Assigns `MultigridProjector.Config.PluginConfig.Current = Config` to expose the server config to all shared code through the `IPluginConfig` interface.
6. IL verification (old .NET Framework only, non-Wine): calls `EnsureOriginal.VerifyAll()`. If it throws `NotSupportedException`, the plugin logs the error and **returns early** — Harmony patches are not applied and the plugin is effectively disabled.
7. Calls `Harmony.PatchAll(Assembly.GetExecutingAssembly())` to install all server-side Harmony patches.

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
| `Config` | `PluginConfig` (get) | The live configuration instance |
| `Init(object gameInstance)` | Method | Full startup sequence: config, IL verify, `PatchAll` (see Lifecycle above) |
| `Update()` | Method | No-op; per-frame work is handled by `PluginSession` |
| `Dispose()` | Method | Saves config, unsubscribes events, clears logger and `Instance` |
| `LoadConfig(string path)` | Private method | Deserialize-then-reserialize with fallback to defaults on error |
| `SaveConfig()` | Private method | Serializes `Config` to `configPath` via `ConfigStorage.SaveXml` |
| `OnConfigPropertyChanged(object, PropertyChangedEventArgs)` | Private method | Calls `SaveConfig()`; logs errors without rethrowing |
| `Harmony` | Private static property | Creates a `new Harmony("com.spaceengineers.multigridprojector")` on each access |

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
- [Server-Patches.md](./Server-Patches.md) — Harmony patches installed by `Plugin.Init` via `PatchAll`
- [Configuration.md](./Configuration.md) — `IPluginConfig` interface and `PluginConfig.Current` static accessor used by shared code
- [Shared-Utilities.md](./Shared-Utilities.md) — `IPluginLogger`, `PluginLog`, `EnsureOriginal`, `WineDetector`
- [../Installation.md](../Installation.md) — Server installation, config file location, Magnetar setup
