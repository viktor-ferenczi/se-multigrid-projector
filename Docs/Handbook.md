# Multigrid Projector — Documentation Handbook

This is the entry point to all documentation for the **Multigrid Projector** plugin for Space
Engineers — both the user-facing guides and the developer reference for the codebase.

Multigrid Projector lets in-game projectors build and repair blueprints that contain **multiple
subgrids** (joined by rotors, hinges, pistons and connectors), in survival and creative, single-player
and multiplayer. It ships as a **client plugin** (loaded by [Pulsar](https://github.com/SpaceGT/Pulsar))
and a **server plugin** (loaded by [Magnetar](https://magnetar.se), configured via Quasar), both built
from one shared core.

New to the codebase? Start with **[Architecture](Architecture.md)** for the big picture, then follow
the links below.

## User guides

| Guide | What it covers |
| ----- | -------------- |
| [Installation](Installation.md) | Installing and configuring the client (Pulsar) and server (Quasar / standalone Magnetar) plugins. |
| [Building from source](Building.md) | Prerequisites and local build/deploy commands. |
| [Mod & PB API](API.md) | Short summary of the scripting API for mods and programmable blocks. |
| [Troubleshooting](Troubleshooting.md) | Common issues, the IL-verification check, Proton/Linux notes, getting help. |

## Developer reference

Start here: **[Architecture](Architecture.md)** — how everything fits together.

### Shared core (compiled into both plugins)

| Subsystem | Description |
| --------- | ----------- |
| [Core Projection Engine](Reference/Core-Projection-Engine.md) | `Shared/Logic` — the projection state machine, subgrids, block states, connections, update loop, reference fixing, API provider. **The heart of the plugin.** |
| [Public Mod & PB API](Reference/Public-API.md) | The supported API surface for external mods and Programmable Block scripts. |
| [Shared Harmony Patches](Reference/Shared-Patches.md) | Game patches compiled into both targets (placement, mechanical blocks, crash guards). |
| [Shared Extension Methods](Reference/Shared-Extensions.md) | Helper extensions over game types used throughout the engine. |
| [Shared Utilities & Infrastructure](Reference/Shared-Utilities.md) | Logging, IL verification, locks, hashing, comms, transpiler helpers, environment detection. |
| [Configuration](Reference/Configuration.md) | The shared `IPluginConfig` and the client/server config mechanisms behind it. |

### Client plugin (Pulsar)

| Subsystem | Description |
| --------- | ----------- |
| [Client Plugin Core](Reference/Client-Plugin.md) | Entry point, lifecycle, session, logging. |
| [Client Harmony Patches](Reference/Client-Patches.md) | Client-side projector/welder/UI patches. |
| [Client Extra Features](Reference/Client-Features.md) | Welding, alignment, highlighting, bill of materials, repair projection, paint, toolbar fix. |
| [Client GUI Dialogs](Reference/Client-Menus.md) | In-game dialogs for the extra features. |
| [Client Settings Framework](Reference/Client-Settings.md) | Attribute-driven generator for the in-game config dialog. |
| [Client Utilities](Reference/Client-Utilities.md) | Client-side construction, property replay, reflection, terminal-control helpers. |

### Server plugin (Magnetar)

| Subsystem | Description |
| --------- | ----------- |
| [Server Plugin Core](Reference/Server-Plugin.md) | Entry point, lifecycle, PluginSdk config (edited via Quasar). |
| [Server Harmony Patches](Reference/Server-Patches.md) | Server-authoritative projector/welder/mechanical patches. |

### Building & examples

| Subsystem | Description |
| --------- | ----------- |
| [Build & Project Layout](Reference/Build-And-Project-Layout.md) | Solution structure, multi-targeting, publicizer, deploy pipeline. |
| [API Examples (Mod & PB)](Reference/Examples.md) | The `ModApiTest` mod and `IngameApiTest` PB script that consume the API. |

## Indexes

- **[Source File Index](Index.md)** — every tracked source/project file, grouped by subsystem, linked
  to its source and reference page.
- **Reference graph** — machine-readable subsystem dependencies in
  [`data/reference_graph.json`](data/reference_graph.json).

## About this documentation

The reference pages were generated with the `structured-documentation` workflow and are kept cheap to
refresh: the working data (manifest with per-file SHA256 hashes, module summaries, reference graph,
generator scripts) lives under [`data/`](data/) and is excluded from version control. After code
changes, re-run `python3 data/build_manifest.py` and `python3 data/generate_index.py`; only files
whose hash changed need re-documenting. See [`data/progress.md`](data/progress.md) for pipeline state.
