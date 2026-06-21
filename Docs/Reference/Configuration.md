# Configuration

Multigrid Projector has **two configuration mechanisms** — one per target — unified behind a
single shared interface so the engine in [Core-Projection-Engine.md](./Core-Projection-Engine.md)
never needs to know which side it is running on.

- The **client** is configured from the in-game settings dialog (built by the
  [Client Settings Framework](./Client-Settings.md) from attributes on
  [`ClientPlugin/Config.cs`](../../ClientPlugin/Config.cs)).
- The **server** is configured through Magnetar's **PluginSdk**
  ([`ServerPlugin/PluginConfig.cs`](../../ServerPlugin/PluginConfig.cs)), edited remotely via Quasar.

Both implement `IPluginConfig`, and shared code reads only that interface via the static
`PluginConfig.Current` slot.

For the user-facing view of these settings (where the files live, how to edit them, what each
option means in play) see [../Installation.md](../Installation.md) and
[../Troubleshooting.md](../Troubleshooting.md).

## Files

| File | Lines | Purpose |
| ---- | ----: | ------- |
| [Shared/Config/IPluginConfig.cs](../../Shared/Config/IPluginConfig.cs) | 22 | The shared configuration contract both targets implement. |
| [Shared/Config/PluginConfig.cs](../../Shared/Config/PluginConfig.cs) | 16 | Static `Current` slot + safe `DefaultPluginConfig` used until a target assigns it. |
| [ClientPlugin/Config.cs](../../ClientPlugin/Config.cs) | 128 | Client config: feature toggles, attributed for the settings dialog, persisted as XML. |
| [ServerPlugin/PluginConfig.cs](../../ServerPlugin/PluginConfig.cs) | 20 | Server config: PluginSdk-declared option(s) rendered remotely by Quasar. |

## The shared interface

*`interface IPluginConfig` — namespace `MultigridProjector.Config` (in the
[Shared](./Core-Projection-Engine.md) project).*

The interface is deliberately tiny: it exposes only what shared code must branch on at runtime.
Everything else (the client feature toggles) is client-only and never reaches shared code.

| Member | Kind | Description |
| ------ | ---- | ----------- |
| `PreviewBlockVisuals` | bool (get) | Whether the plugin manages the appearance of not-yet-built (preview) blocks: buildable blocks as semi-transparent ghosts, unbuildable as holograms (or hidden under *Show only buildable*), built blocks hidden, and the projector's sound/emissive state driven to match. When `false` the plugin leaves preview visuals untouched (mod compatibility). Always `true` on the client; server-configurable. |

*`static class PluginConfig`* holds the active implementation:

| Member | Kind | Description |
| ------ | ---- | ----------- |
| `PluginConfig.Current` | static `IPluginConfig` | The active config. Assigned by each plugin's `Init`. Defaults to `DefaultPluginConfig` (all-defaults) until then, so shared code is always safe to read. |
| `DefaultPluginConfig` | internal class | Fallback returning `PreviewBlockVisuals => true`. |

## Client configuration

*`class Config : INotifyPropertyChanged, IPluginConfig` — namespace `ClientPlugin`.*

The client config is a plain object whose properties are annotated with attributes from the
[Client Settings Framework](./Client-Settings.md). `SettingsGenerator` reflects over it to build the
dialog, and `ConfigStorage` serialises it to
`%AppData%/SpaceEngineers/Storage/MultigridProjector.cfg` (Windows) or the Linux equivalent. The
client wires `Config.Current` into `PluginConfig.Current` in
[`Plugin.Init`](./Client-Plugin.md).

All toggles default to **on**. They are grouped under three separators in the dialog:

| Group | Property | Dialog label | Effect |
| ----- | -------- | ------------ | ------ |
| Core | `ShowDialogs` | Show Warning Dialogs | Show the plugin's warning dialogs (see [Client-Menus.md](./Client-Menus.md)). |
| Compatibility Mode | `ClientWelding` | Client Welding | Place blocks and copy properties client-side when the server has no plugin ([ShipWelding / Construction](./Client-Features.md)). |
| Compatibility Mode | `ShipWelding` | Ship Welding | Extend client welding to welders on the piloted craft's grids/subgrids. |
| Compatibility Mode | `ConnectSubgrids` | Connect Subgrids | Reconnect subgrids by removing wrong heads and placing correct ones ([ConnectSubgrids](./Client-Features.md)). |
| Extra Features | `RepairProjection` | Repair Projection | Load a copy of a ship into the projector for rebuilding ([RepairProjection](./Client-Features.md)). |
| Extra Features | `ProjectorAligner` | Align Projection | Align projections with the normal block-placement keys ([ProjectorAligner](./Client-Features.md)). |
| Extra Features | `BlockHighlight` | Highlight Blocks | Highlight projected blocks by status/completion ([BlockHighlight](./Client-Features.md)). |
| Extra Features | `CraftProjection` | Assemble Projections | View a projection's component cost and queue it for assembly ([CraftProjection](./Client-Features.md)). |

`PreviewBlockVisuals` is hard-coded to `true` on the client and is **not** exposed in the dialog —
only the server may disable it for mod compatibility. The class also carries the standard
`INotifyPropertyChanged` boilerplate (`SetField`, `OnPropertyChanged`) so control changes persist
immediately, plus the static `Default` and `Current` instances.

## Server configuration

*`class PluginConfig : PluginSdk.Config.PluginConfig, IPluginConfig` — namespace `ServerPlugin`.*

The server config derives from Magnetar's `PluginSdk.Config.PluginConfig`. Each option is declared
with a PluginSdk attribute (e.g. `[BoolOption(description)]`), and **Quasar renders the settings UI
remotely from those attributes** — the plugin contains no server-side UI code. The
[server Plugin](./Server-Plugin.md) loads/saves it through PluginSdk's `ConfigStorage` as
`MultigridProjector.cfg` in the server user-data directory, and re-saves automatically on every
`PropertyChanged`.

| Option | Type | Default | Description |
| ------ | ---- | ------- | ----------- |
| `PreviewBlockVisuals` | bool | `true` | Implements the shared-interface member above. Turn **off** only for compatibility with mods that drive projector / preview-block transparency themselves. |

If the config file is missing or corrupt the server recreates it with defaults (the corrupt file is
moved aside) — see [../Troubleshooting.md](../Troubleshooting.md).

## See also

- [Client Plugin Core](./Client-Plugin.md) — where the client assigns `PluginConfig.Current`.
- [Server Plugin Core](./Server-Plugin.md) — config load/save lifecycle and PluginSdk wiring.
- [Client Settings Framework](./Client-Settings.md) — how the client dialog is generated.
- [../Installation.md](../Installation.md) — user-facing client and server configuration.
