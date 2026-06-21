# Installation

> Part of the [Documentation Handbook](Handbook.md). Developers: see
> [Configuration](Reference/Configuration.md) for how these settings are implemented.

Multigrid Projector ships as two plugins:

- a **client plugin** loaded by [Pulsar](https://github.com/SpaceGT/Pulsar) in the game client, and
- a **server plugin** loaded by [Magnetar](https://magnetar.se) on the dedicated server.

They work together but can be used independently. In multiplayer the client plugin alone already
provides most of the multigrid welding; installing the server plugin as well enables full
functionality for everyone on the server.

> Torch and the legacy Dedicated Server plugin loader are **no longer supported**. Use Pulsar on the
> client and Magnetar (optionally managed by Quasar) on the server.

## Client plugin (Pulsar)

1. Install [Pulsar](https://github.com/SpaceGT/Pulsar) (the plugin & mod loader for the game client).
   On Windows the [Pulsar installer](https://github.com/StarCpt/Pulsar-Installer) sets up Steam for
   you; otherwise download the latest release and configure the Steam launch options as described in
   the Pulsar README.
2. Start the game through Pulsar.
3. Open the **Plugins** menu from the Main Menu.
4. Add the **Multigrid Projector** plugin (it is listed from the
   [PluginHub](https://github.com/StarCpt/PluginHub)).
5. Click **Save**, then **Restart**.

After enabling the plugin it is active for all single player worlds you load, and for multiplayer.

### Client configuration

Open the plugin's configuration dialog from the Pulsar plugin list (the **Config** button next to
the plugin). The dialog lets you toggle the client-side features:

- **Core** — Show Warning Dialogs
- **Compatibility Mode** — Client Welding, Ship Welding, Connect Subgrids
- **Extra Features** — Repair Projection, Align Projection, Highlight Blocks, Assemble Projections

Hover over an option to see a short description. Settings are saved to
`%AppData%/SpaceEngineers/Storage/MultigridProjector.cfg` (Windows) or the equivalent under your
game user data directory on Linux.

## Server plugin (Magnetar / Quasar)

The server plugin runs inside [Magnetar](https://magnetar.se), the plugin loader for the Space
Engineers Dedicated Server. There are two ways to install it.

### Recommended: via Quasar

[Quasar](https://github.com/viktor-ferenczi/Quasar) is the control plane (web UI) that manages
Magnetar servers. It lists the Magnetar-compatible plugins from the
[MagnetarHub](https://github.com/viktor-ferenczi/MagnetarHub) and lets you enable and configure them
remotely.

1. Open your Quasar web UI and select the server.
2. Enable the **Multigrid Projector** plugin for that server.
3. Adjust its configuration in the plugin's settings panel (rendered by Quasar from the plugin's
   declared options — see [Server configuration](#server-configuration) below).
4. Save and (re)start the server from Quasar.

### Standalone Magnetar (editing the profile)

If you run Magnetar without Quasar you enable the plugin by editing the active **profile**. Magnetar
stores profiles as XML files under its configuration directory:

- Windows: `%AppData%\Magnetar\Profiles\`
- Linux: `~/.config/Magnetar/Profiles/`

`Current.xml` is the active profile. Add the Multigrid Projector plugin entry (by its MagnetarHub
plugin id) to the enabled plugins in `Current.xml`, then start Magnetar in place of
`SpaceEngineersDedicated.exe`. Magnetar downloads/compiles the plugin and loads it on startup.

See the Magnetar documentation for the exact profile entry format and for adding plugin sources.

### Server configuration

The server plugin's configuration is declared through Magnetar's PluginSdk and edited remotely via
Quasar. The local configuration file is `MultigridProjector.cfg` in the server's user data
directory.

| Option | Default | Description |
| ------ | ------- | ----------- |
| Preview block visuals | On | See below. |

#### Preview block visuals

Controls whether the plugin manages how the **not-yet-built (preview) blocks** of a multigrid
projection look. When enabled (the default), the plugin keeps each projected block's appearance in
sync with its build state:

- **Buildable** blocks are shown as semi-transparent "ghost" blocks.
- Blocks that **cannot be built yet** (missing the block they attach to, or mismatched) are shown as
  holograms — or hidden entirely when the projector's *Show only buildable* option is on.
- Blocks that are **already built** are hidden, so the real block shows through.
- The projector's working **sound** and **emissive (lit) state** are updated to match.

Turn it **off** only if you run mods that set projector or preview-block transparency themselves and
you want the plugin to stay out of their way. When off, the plugin does not touch preview block
visuals at all. This is a server-side compatibility switch; on the client the visuals are always on.

## Linux (Proton) note

On Linux you may need to define the `SE_PLUGIN_DISABLE_METHOD_VERIFICATION` environment variable to
disable the plugin's game-code (IL) verification. See [Troubleshooting](Troubleshooting.md) for the
details and the reasoning behind the check.
