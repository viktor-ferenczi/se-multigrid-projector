# Troubleshooting

In case of problems join the [SE Mods Discord](https://discord.gg/PYPFPGf3Ca) to get help. If you
use a 3rd party game server hosting provider, please follow their documentation on how to install
server plugins or contact their support.

## The plugin refuses to load after a game update

To avoid crashing after a game update, the plugin verifies the IL code of the game methods it
patches. If any of them changed, the plugin refuses to load (and logs an error) instead of crashing
later. You can detect this case by looking in the game's log file for:

```
Refusing to load the plugin due to potentially incompatible code changes in the game
```

When this happens the plugin needs an update for the new game version. Please report it on the
[SE Mods Discord](https://discord.gg/PYPFPGf3Ca).

## Linux / Proton

The IL code verification tends to cause issues on Linux (Wine/Proton). The plugin automatically
skips it when it detects it is running under Wine/Proton. You can also disable it explicitly by
defining the environment variable:

```
SE_PLUGIN_DISABLE_METHOD_VERIFICATION=1
```

Set it on the host running the game (client) or the dedicated server.

## Multiplayer behaviour

- With only the **client** plugin installed, most multigrid welding already works.
- Installing the **server** plugin as well enables full functionality for everyone connected.
- Make your players aware of Pulsar so they can install the client plugin.

## Configuration files

- **Client:** `%AppData%/SpaceEngineers/Storage/MultigridProjector.cfg` (or the equivalent under your
  game user data directory on Linux). Edited through the in-game Pulsar config dialog.
- **Server:** `MultigridProjector.cfg` in the dedicated server's user data directory. Edited remotely
  through Quasar, or directly on disk for a standalone Magnetar install.

If a configuration file becomes corrupted it is moved aside (with a `.corrupted.<timestamp>.txt`
suffix) and recreated with defaults.

## IDE / build issues

See [Building from source](Building.md) for build and deployment troubleshooting.
