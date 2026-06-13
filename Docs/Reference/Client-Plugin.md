# Client Plugin Core

The client plugin is the entry point for Multigrid Projector when loaded by **Pulsar** into the Space Engineers game client. It implements the VRage `IPlugin` interface and is responsible for bootstrapping the entire client-side feature set: initialising logging, bridging `Config` into the shared `IPluginConfig` interface, optionally running IL integrity verification, applying all Harmony patches, and presenting the in-game settings dialog. A companion `PluginSession` session component registers itself with the game engine and drives the per-frame update loop for the projection engine, block highlighting, and ship welding. The Shared/ source tree is compiled directly into this assembly and relies on the plugin for its configuration and logging dependencies.

See also:
- [Core-Projection-Engine.md](./Core-Projection-Engine.md) — the `MultigridProjectorSession` / `MultigridProjection` engine wired by `PluginSession`.
- [Client-Settings.md](./Client-Settings.md) — the Settings framework that generates the in-game config dialog.
- [Client-Patches.md](./Client-Patches.md) — all Harmony patches applied during `Init`.
- [Client-Features.md](./Client-Features.md) — extra client features (block highlight, ship welding, projector aligner, craft projection).
- [Configuration.md](./Configuration.md) — shared config storage and the `IPluginConfig` contract.
- [Shared-Utilities.md](./Shared-Utilities.md) — `PluginLog`, `EnsureOriginal`, `WineDetector`.
- [../Installation.md](../Installation.md) — how Pulsar loads this assembly.

---

## Files

| File | Lines | Purpose |
|------|-------|---------|
| [Plugin.cs](../../ClientPlugin/Plugin.cs) | 80 | `IPlugin` entry point: logging setup, config bridge, IL verification, `Harmony.PatchAll`, config dialog. |
| [Config.cs](../../ClientPlugin/Config.cs) | 128 | Persistent user configuration; implements `IPluginConfig`; exposes all feature-toggle properties with Settings UI attributes. |
| [PluginSession.cs](../../ClientPlugin/PluginSession.cs) | 52 | `MySessionComponentBase` session object: constructs/disposes `MultigridProjectorSession`; drives per-frame update of highlight, welding, and projection engine. |
| [PluginLogger.cs](../../ClientPlugin/PluginLogger.cs) | 46 | `IPluginLogger` implementation that forwards to `MyLog.Default`; surfaces errors to the player via `MyAPIGateway.Utilities.ShowMessage`. |

---

## Lifecycle

```
Pulsar loads assembly
        │
        ▼
Plugin.Init(gameInstance)
  ├─ Plugin.Instance = this
  ├─ new SettingsGenerator()          ← prepares config dialog
  ├─ PluginLog.Logger = new PluginLogger()
  ├─ MultigridProjector.Config.PluginConfig.Current = Config.Current
  │                                   ← bridges client Config into shared code
  ├─ [net48 only, not Wine/Proton, env var not set]
  │    EnsureOriginal.VerifyAll()     ← throws NotSupportedException if game IL changed
  └─ Harmony.PatchAll(Assembly.GetExecutingAssembly())
                                      ← all [HarmonyPatch] classes in the assembly
        │
        ▼  (game running)
Plugin.Update()                       ← called each frame (currently no-op; logic is in PluginSession)

Pulsar calls Plugin.OpenConfigDialog()  (optional, user-triggered)
  └─ settingsGenerator.SetLayout<Simple>()
     MyGuiSandbox.AddScreen(settingsGenerator.Dialog)

        │
        ▼  (game session starts — VRage session component lifecycle)
PluginSession.Init(sessionComponent)
  ├─ MultigridProjection.EnsureNoProjections()
  ├─ mgpSession = new MultigridProjectorSession()
  └─ ProjectorAligner.Initialize()

PluginSession.UpdateAfterSimulation()   ← called each simulation tick
  ├─ mgpSession?.Update()
  ├─ [Config.BlockHighlight]  BlockHighlight.HighlightLoop()
  └─ [Config.ShipWelding]     ShipWelding.WeldLoop()

PluginSession.UnloadData()
  ├─ mgpSession.Dispose(); mgpSession = null
  ├─ MultigridProjection.EnsureNoProjections()
  └─ [Config.ProjectorAligner]  ProjectorAligner.Instance?.Dispose()

        │
        ▼  (Pulsar unloads plugin)
Plugin.Dispose()
  ├─ NOTE: Harmony patches are intentionally NOT removed.
  │    Unpatching caused problems for other plugins; keeping patches installed
  │    is standard practice with plugin loaders.
  └─ Plugin.Instance = null
```

**Key design notes:**

- IL verification (`EnsureOriginal.VerifyAll`) runs only on .NET Framework (major version < 5) because the game on Windows ships with net48. It is skipped on Wine/Proton (Linux) and can be suppressed via the `SE_PLUGIN_DISABLE_METHOD_VERIFICATION` environment variable.
- `Plugin.Update()` is intentionally empty; per-frame work is delegated to `PluginSession.UpdateAfterSimulation`, which is called by the VRage session component system after each simulation tick.
- Unpatching in `Dispose` is deliberately omitted to avoid interoperability issues with other Harmony-based plugins.

---

## Plugin

*`public class Plugin : IPlugin` — namespace `ClientPlugin`*

The top-level `IPlugin` implementation. Pulsar instantiates exactly one instance and calls its lifecycle methods. It acts as a composition root: it wires the logger, bridges config to shared code, gates IL verification, and triggers `Harmony.PatchAll`.

| Member | Kind | Description |
|--------|------|-------------|
| `Name` | `public const string` | Plugin identifier string `"MultigridProjector"`. |
| `Instance` | `public static Plugin` | Singleton reference set during `Init`, cleared during `Dispose`. |
| `Init(object gameInstance)` | `public void` | Entry point called by Pulsar at load time. Sets up logging, config bridge, optional IL verification, and Harmony patches. Marked `NoInlining` to ensure a stable call site. |
| `OpenConfigDialog()` | `public void` | Called by Pulsar when the user opens the plugin settings. Applies the `Simple` layout and pushes the settings screen onto the GUI stack via `MyGuiSandbox`. |
| `Update()` | `public void` | Per-frame callback from Pulsar (no-op; work is in `PluginSession`). |
| `Dispose()` | `public void` | Plugin teardown. Harmony patches are intentionally left installed. Clears `Instance`. |

---

## Config

*`public class Config : INotifyPropertyChanged, IPluginConfig` — namespace `ClientPlugin`*

Persistent, user-editable configuration loaded from disk by `ConfigStorage.Load()`. Each property is annotated with Settings UI attributes (`[Checkbox]`, `[Separator]`) that `SettingsGenerator` reads to build the in-game dialog. Changes fire `PropertyChanged` for live data-binding. The instance is published to shared code through `MultigridProjector.Config.PluginConfig.Current` so that shared/server code can read feature flags without a hard dependency on the client assembly.

| Member | Kind | Description |
|--------|------|-------------|
| `Title` | `public readonly string` | Display title shown in the settings dialog: `"Multigrid Projector"`. |
| `Default` | `public static readonly Config` | A pristine default-value instance (all options `true`). |
| `Current` | `public static readonly Config` | The active instance loaded from persistent storage via `ConfigStorage.Load()`. |
| `ShowDialogs` | `public bool` | **Core.** When `true`, Multigrid Projector's warning dialogs are shown to the player. Disabling suppresses all warnings. Default: `true`. |
| `ClientWelding` | `public bool` | **Compatibility Mode.** Enables client-side welding: places blocks and copies over their properties for projections that could not be welded without a server-side plugin. Default: `true`. |
| `ShipWelding` | `public bool` | **Compatibility Mode.** Extends client welding to welders on grids and subgrids of the craft the player is currently piloting. Requires `ClientWelding`. Default: `true`. |
| `ConnectSubgrids` | `public bool` | **Compatibility Mode.** Attempts to connect subgrids by removing incorrect mechanical heads and placing corrected ones. Default: `true`. |
| `RepairProjection` | `public bool` | **Extra Features.** Allows loading a copy of a ship into a projector so it can be rebuilt after damage. Default: `true`. |
| `ProjectorAligner` | `public bool` | **Extra Features.** Enables intuitive alignment of projections using the standard block-placement alignment keys. Default: `true`. |
| `BlockHighlight` | `public bool` | **Extra Features.** Highlights projected blocks using colour coding based on their build status and completion. Default: `true`. |
| `CraftProjection` | `public bool` | **Extra Features.** Shows component cost for a projection and allows queuing it for assembly. Default: `true`. |
| `PreviewBlockVisuals` | `public bool` (interface) | Implements `IPluginConfig`. Always returns `true` on the client; the server may return `false` for mod compatibility. Not exposed in the settings dialog. |
| `PropertyChanged` | `event PropertyChangedEventHandler` | Raised by `SetField` whenever a property value changes. Used by the Settings framework for live UI binding. |

### Configuration groups (UI separators)

| Separator | Properties |
|-----------|-----------|
| Core | `ShowDialogs` |
| Compatibility Mode | `ClientWelding`, `ShipWelding`, `ConnectSubgrids` |
| Extra Features | `RepairProjection`, `ProjectorAligner`, `BlockHighlight`, `CraftProjection` |

---

## PluginSession

*`[MySessionComponentDescriptor(MyUpdateOrder.AfterSimulation)] public class PluginSession : MySessionComponentBase` — namespace `MultigridProjectorClient`*

A VRage session component registered at `AfterSimulation` update order. It owns the `MultigridProjectorSession` (the core projection engine) for the duration of a game session and drives the per-tick loops for block highlighting, ship welding, and the projector aligner. It also gates initialisation and teardown with `MultigridProjection.EnsureNoProjections()` to assert a clean projection state.

| Member | Kind | Description |
|--------|------|-------------|
| `Init(MyObjectBuilder_SessionComponent)` | `public override void` | Called when a session starts. Asserts no stale projections, creates a new `MultigridProjectorSession`, and initialises `ProjectorAligner`. |
| `UnloadData()` | `protected override void` | Called on session end. Disposes `MultigridProjectorSession`, asserts clean state, and disposes `ProjectorAligner` if enabled. |
| `UpdateAfterSimulation()` | `public override void` | Called each simulation tick. Calls `mgpSession.Update()`; conditionally calls `BlockHighlight.HighlightLoop()` and `ShipWelding.WeldLoop()` based on `Config.Current`. |

---

## PluginLogger

*`internal class PluginLogger : IPluginLogger` — namespace `MultigridProjectorClient`*

The client-side implementation of the shared `IPluginLogger` interface. All methods are `AggressiveInlining` for minimal call overhead. Log output goes to `MyLog.Default` (the game's standard log file). In the `Error` path the message is additionally shown as an in-game HUD notification via `MyAPIGateway.Utilities.ShowMessage`, prompting the player to report the exception. A compile-time `USE_SHOW_MESSAGE_FOR_DEBUGGING` flag (defined under `#if DEBUG`) can also route `Debug` messages to the HUD.

| Member | Kind | Description |
|--------|------|-------------|
| `Info(string msg)` | `public void` | Writes to `MyLog.Default.Info`. |
| `Debug(string msg)` | `public void` | Writes to `MyLog.Default.Debug`; optionally shows HUD message when `USE_SHOW_MESSAGE_FOR_DEBUGGING` is defined. |
| `Warn(string msg)` | `public void` | Writes to `MyLog.Default.Warning`. |
| `Error(string msg)` | `public void` | Writes to `MyLog.Default.Error` and shows a "Please report this exception" HUD message if a session is active. |
