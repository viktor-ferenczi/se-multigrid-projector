# Architecture

A high-level map of how Multigrid Projector is put together. Read this first, then drill into any
[reference page](Handbook.md) for the details. Every link below points either to a subsystem
reference page (under `Reference/`) or to a source file.

## What the plugin does

Space Engineers' stock projector can only build a **single grid**. Multigrid Projector (MGP) makes a
projector build and repair **blueprints that contain multiple subgrids** — grids joined by
mechanical connections (rotors, hinges, pistons, wheels) and connectors — so PDCs, mechs, articulated
ships and the like can be welded up directly from a projection, in survival or creative, single-player
or multiplayer. It also adds projector quality-of-life features (alignment, highlighting, bill of
materials, repair projection, client-side welding).

It ships as **two plugins built from one shared core**:

- a **client plugin** loaded by [Pulsar](https://github.com/SpaceGT/Pulsar) in the game client, and
- a **server plugin** loaded by [Magnetar](https://magnetar.se) on the dedicated server (configured
  remotely through Quasar).

In multiplayer the server plugin is authoritative; the client plugin alone still provides most
multigrid welding through a client-side "compatibility mode".

## The big picture

```
                         ┌──────────────────────────────────────────────┐
                         │            Shared/  (one source set)          │
                         │                                               │
   Game (patched) ──────▶│  Patches ──▶  Core Projection Engine          │◀── Mod / PB API
   methods               │  (Harmony)    (Shared/Logic)                  │    consumers
                         │                 MultigridProjection           │
                         │                 Subgrid · ProjectedBlock       │
                         │                 Connection · ReferenceFixer    │
                         │                 + Extensions · Utilities       │
                         └───────▲──────────────────────▲────────────────┘
                                 │ compiled into          │ compiled into
                    ┌────────────┴───────────┐ ┌──────────┴──────────────┐
                    │      ClientPlugin       │ │       ServerPlugin       │
                    │ (Pulsar, game client)   │ │ (Magnetar, dedicated)    │
                    │ Patches · Extra features │ │ Patches (authoritative)  │
                    │ Menus · Settings dialog  │ │ PluginSdk config (Quasar)│
                    │ Utilities                │ │                          │
                    └─────────────────────────┘ └──────────────────────────┘
```

The same engine and patch *patterns* run on both sides; the side-specific behaviour is selected at
runtime via `[Everywhere]` / `[ServerOnly]` / `[ClientOnly]` markers and `Comms` role detection.

## The shared core

The heart is the **[Core Projection Engine](Reference/Core-Projection-Engine.md)** in `Shared/Logic`.

- **`MultigridProjection`** ([source](../Shared/Logic/MultigridProjection.cs), ~2300 lines) is a
  per-projector state machine, registered statically by the projector's `EntityId`. It owns the list
  of subgrids, the build/placement logic, the update loop, and every Harmony entry point the patches
  call into.
- **`Subgrid`** is one blueprint grid: its preview ("hologram") grid, its built grid (if any), its
  per-block models, and its mechanical connections.
- **`ProjectedBlock`** pairs a preview block with its builder and classifies each block's
  [`BlockState`](Reference/Public-API.md) (buildable / being built / fully built / mismatch / …),
  driving preview transparency.
- **`Connection` / `BaseConnection` / `TopConnection`** represent one side of a mechanical link that
  holds two subgrids together.
- **`ReferenceFixer`** restores inter-block references (toolbars, controllers, weapon/tool links) on
  welded blocks by mapping blueprint ids to live `EntityId`s.
- **`MultigridProjectorApiProvider`** turns all of this into the in-process, Mod, and PB APIs.

The engine leans on two supporting subsystems, also in `Shared/`:

- **[Shared Extension Methods](Reference/Shared-Extensions.md)** — thin wrappers over game types
  (`MyCubeGrid`, `MyCubeBlock`, `MyProjectorBase`, object builders) that centralise access to
  publicized fields and blueprint preparation, insulating the engine from game-version field renames.
- **[Shared Utilities & Infrastructure](Reference/Shared-Utilities.md)** — logging (`PluginLog`),
  startup IL verification (`EnsureOriginal`), Harmony transpiler helpers, the spin
  reader/writer lock (`RwLock`), hashing, multiplayer role detection and packet routing (`Comms`),
  game-thread scheduling (`Events`), and Wine/Proton detection.

## How the game is hooked

MGP changes the game purely through **Harmony patches** — it never modifies game files. Patches come
in three sets:

- **[Shared Harmony Patches](Reference/Shared-Patches.md)** (6) — compiled into both targets; placement
  validation, mechanical-block construction (extending `topSize` with sentinel values), and crash
  guards.
- **[Client Harmony Patches](Reference/Client-Patches.md)** (22) — projector/welder/blueprint-screen
  hooks plus terminal-control and toolbar injection for the client.
- **[Server Harmony Patches](Reference/Server-Patches.md)** (16) — the server-authoritative
  counterparts that actually place blocks, create mechanical tops/bases, and remap entity ids.

Most patches follow the same shape: *guard on whether this projector has a `MultigridProjection`; if so,
delegate to the engine and suppress the vanilla single-grid logic; otherwise fall through to vanilla.*
A few must use **transpilers** instead of prefixes — notably `BuildInternal`, where prefixing a
multiplayer event handler would crash Harmony.

Patches that rewrite IL are guarded by **`EnsureOriginal`**: at load the plugin hashes the IL of the
game methods it patches and refuses to load if any changed, turning a future game update into a clean
"please update the plugin" message instead of a crash (see [../Docs/Troubleshooting.md](Troubleshooting.md)).
This check is skipped under Wine/Proton and can be disabled with
`SE_PLUGIN_DISABLE_METHOD_VERIFICATION`.

## The update cycle

Each frame, the projector's patched `UpdateAfterSimulation` drives the engine:

1. A cooldown / force-flag decides whether to start a **background scan**
   (`MultigridUpdateWork`, built on `ParallelTasks`). The worker computes per-subgrid block states,
   stats, and a state hash **off the main thread**, writing only into dedicated per-subgrid fields.
2. On completion, work resumes on the **game thread**: bump the scan number, promote/attach
   mechanical connections (on the server, build any missing heads/bases), flood-fill which subgrids
   are connected to the projector, aggregate `ProjectionStats`, refresh preview visuals, and queue
   `ReferenceFixer` work.

Shared collections are guarded by `RwLock`/`RwLockDictionary`; the static projection registry is an
`RwLockDictionary`. `ScanNumber` and `StateHash` give external consumers (and the plugin itself) a
cheap way to detect change without re-reading everything.

## Multiplayer model

`Comms` ([source](../Shared/Utilities/Comms.cs)) detects the runtime role (single-player, MP client,
MP server, dedicated) and performs a small handshake so a client can tell whether the **server also
has the plugin**:

- **Server + client both have MGP** → full, seamless multigrid building for everyone.
- **Client only** → "compatibility mode": the [Client Extra Features](Reference/Client-Features.md)
  (client welding, ship welding, connect subgrids) reproduce as much as possible locally using
  networked build calls, with warning dialogs explaining the limits.

## The client target

[ClientPlugin](Reference/Client-Plugin.md) (`IPlugin`, loaded by Pulsar) initialises logging, bridges
its [Config](Reference/Configuration.md) into the shared `PluginConfig.Current` slot, optionally runs
`EnsureOriginal`, and `PatchAll`s. A `PluginSession` drives the per-frame feature loops. On top of the
engine it layers:

- **[Extra Features](Reference/Client-Features.md)** — ConnectSubgrids, CraftProjection (bill of
  materials / assemble), ProjectorAligner, BlockHighlight, ShipWelding, ApplyPaint, RepairProjection,
  ToolbarFix. Each is gated by a config toggle and most inject terminal controls / toolbar actions.
- **[GUI Dialogs](Reference/Client-Menus.md)** — the craft (BoM), aligner keybind, and projection
  warning dialogs.
- **[Settings Framework](Reference/Client-Settings.md)** — an attribute-driven generator that builds
  the in-game config dialog from the `Config` class and persists it as XML.
- **[Client Utilities](Reference/Client-Utilities.md)** — client-side block construction/welding,
  terminal-property replay, reflection and terminal-control helpers.

## The server target

[ServerPlugin](Reference/Server-Plugin.md) (`IPlugin`, loaded by Magnetar) is leaner: no GUI. It loads
its [PluginConfig](Reference/Configuration.md) through Magnetar's **PluginSdk** (so **Quasar** renders
the settings panel remotely), auto-saves on change, optionally runs `EnsureOriginal`, and `PatchAll`s.
Its [server patches](Reference/Server-Patches.md) are the authoritative half of the build pipeline —
they are the only side that remaps entity ids.

## The public API

The **[Public Mod & PB API](Reference/Public-API.md)** (the `MultigridProjectorApi` shared project)
lets external **mods** and in-game **Programmable Block scripts** query and control projections —
subgrid counts, preview/built grids, per-block states, mechanical connections, completion, plus a YAML
dump and change-detection hashes. Mods get the delegate array through a `SendModMessage` handshake;
PB scripts embed the same agent and read a block property. When the plugin is absent, a single-grid
`MultigridProjectorModShim` keeps consumers working. Two worked
[examples](Reference/Examples.md) (a mod and a PB script) ship in the repo.

## Subsystem dependency map

| Subsystem | Depends on | Used by |
| --------- | ---------- | ------- |
| [Core Projection Engine](Reference/Core-Projection-Engine.md) | Extensions, Utilities, Config, Public-API (types) | Client & server patches, Public-API |
| [Public Mod & PB API](Reference/Public-API.md) | Core engine (provider) | Examples, external mods/scripts |
| [Shared Patches](Reference/Shared-Patches.md) | Core engine, Utilities | Both plugins |
| [Shared Extensions](Reference/Shared-Extensions.md) | Utilities | Core engine, both plugins |
| [Shared Utilities](Reference/Shared-Utilities.md) | — | Everything |
| [Client Plugin Core](Reference/Client-Plugin.md) | Core engine, Utilities, Settings, Config | Client patches & features |
| [Client Patches](Reference/Client-Patches.md) | Core engine, client core/utilities/features | — |
| [Client Features](Reference/Client-Features.md) | Core engine, client utilities/menus | — |
| [Client Menus](Reference/Client-Menus.md) | Client features, settings | Client features |
| [Client Settings](Reference/Client-Settings.md) | Client core (Config) | Client core |
| [Client Utilities](Reference/Client-Utilities.md) | Core engine | Client features/patches/menus |
| [Server Plugin Core](Reference/Server-Plugin.md) | Core engine, Utilities, Config | Server patches |
| [Server Patches](Reference/Server-Patches.md) | Core engine, server core | — |
| [Examples](Reference/Examples.md) | Public-API | — |

The machine-readable form of this graph lives in
[`data/reference_graph.json`](data/reference_graph.json).

## Where to go next

- The full subsystem list and table of contents: **[Handbook.md](Handbook.md)**.
- Every source file, grouped and linked: **[Index.md](Index.md)**.
- Install / build / API / troubleshooting (user-facing): [Installation](Installation.md) ·
  [Building](Building.md) · [API](API.md) · [Troubleshooting](Troubleshooting.md).
