# Build & Project Layout

This page documents the **solution structure, MSBuild wiring, publicizer setup, and deploy
pipeline** — the "how the repository is assembled" view for contributors. For step-by-step build
instructions (prerequisites, commands, release notes) see the user-facing
[../Building.md](../Building.md); this page is its developer-oriented companion.

## Solution structure

The product is **two plugin assemblies built from one shared core**. Both output an assembly named
`MultigridProjector.dll`.

| Project | Kind | Role | Reference page |
| ------- | ---- | ---- | -------------- |
| [`Shared`](../../Shared/Shared.shproj) | Shared project (`.shproj`/`.projitems`) | Engine, patches, extensions, utilities, config interface — compiled into **both** targets. | [Core-Projection-Engine.md](./Core-Projection-Engine.md), [Shared-Patches.md](./Shared-Patches.md), [Shared-Extensions.md](./Shared-Extensions.md), [Shared-Utilities.md](./Shared-Utilities.md), [Configuration.md](./Configuration.md) |
| [`MultigridProjectorApi`](../../MultigridProjectorApi/MultigridProjectorApi.shproj) | Shared project | The public Mod/PB API surface — compiled into both targets and copied into mods/scripts. | [Public-API.md](./Public-API.md) |
| [`ClientPlugin`](../../ClientPlugin/ClientPlugin.csproj) | `Microsoft.NET.Sdk` library | Client target, loaded by Pulsar. Imports both shared projects. | [Client-Plugin.md](./Client-Plugin.md) |
| [`ServerPlugin`](../../ServerPlugin/ServerPlugin.csproj) | `Microsoft.NET.Sdk` library | Server target, loaded by Magnetar. Imports both shared projects. | [Server-Plugin.md](./Server-Plugin.md) |
| [`ModApiTest`](../../ModApiTest/ModApiTest.csproj) / [`IngameApiTest`](../../IngameApiTest/IngameApiTest.csproj) | library / script | Worked API examples. | [Examples.md](./Examples.md) |

The two `.shproj` projects contribute their sources via `<Import .../Shared.projitems>` and
`<Import .../MultigridProjectorApi.projitems>` at the bottom of each plugin `.csproj`, so the same
source compiles into each target rather than being shared as a binary.

## Build / tooling files

| File | Lines | Purpose |
| ---- | ----: | ------- |
| [MultigridProjector.sln](../../MultigridProjector.sln) | 92 | Visual Studio / Rider solution tying the projects together. `Version.Build.props` is included as a solution item. |
| [Version.Build.props](../../Version.Build.props) | 8 | **Committed.** Single source of the plugin `Version` (`AssemblyVersion`/`FileVersion`); shared by all contributors and imported by `Directory.Build.props`. |
| [Directory.Build.props](../../Directory.Build.props) | 133 | **Committed.** Imports `Version.Build.props` and the optional, gitignored `Directory.Build.props.user`, declares the overridable folders (`Bin64`, `Dedicated64`, `Pulsar`, `Magnetar`, `MagnetarData`, `Mods`, `IngameScripts`) and auto-detects the compile-time ones (`Bin64`, `Dedicated64`, `Magnetar`, hence `MagnetarBin` holding `PluginSdk.dll`). Follows the server plugin template. |
| [setup.py](../../setup.py) | 381 | Interactive helper that writes the detected `Bin64` and `Dedicated64` into `Directory.Build.props.user`. |
| [clean.sh](../../clean.sh) / [Clean.bat](../../Clean.bat) | 8 / 13 | Remove `bin`/`obj` build output. |
| [.github/FUNDING.yml](../../.github/FUNDING.yml) | 14 | GitHub sponsor links. |

## Target frameworks

Both plugin projects declare:

```xml
<TargetFrameworks Condition="$([MSBuild]::IsOSPlatform('Windows'))">net48;net10.0</TargetFrameworks>
<TargetFramework  Condition="!$([MSBuild]::IsOSPlatform('Windows'))">net10.0</TargetFramework>
```

- On **Windows** they multi-target `net48` (the framework the shipping game/server still uses) and
  `net10.0`.
- On **Linux** only `net10.0` is built.

`LangVersion` is 14 and `GenerateAssemblyInfo` is on (so the SDK emits assembly attributes — the
example projects keep a hand-written `AssemblyInfo.cs`, the plugins do not). The version (`0.9.2`)
is defined in one place — [`Version.Build.props`](../../Version.Build.props) — and imported into both
plugins via `Directory.Build.props`. For Pulsar/Magnetar source-compiled builds (where the props
import may not apply) the same version is asserted via an `[assembly: AssemblyVersion]` guarded by
`#if !LOCAL_BUILD` in [`ClientPlugin/Plugin.cs`](../../ClientPlugin/Plugin.cs) and
[`ServerPlugin/Plugin.cs`](../../ServerPlugin/Plugin.cs).

### Build constants

| Constant | Where | Meaning |
| -------- | ----- | ------- |
| `LOCAL_BUILD` | both plugins, all configs | A local developer build (as opposed to a Pulsar/Magnetar source-compile). Gates e.g. the [`IgnoresAccessChecksToAttribute`](./Shared-Utilities.md) declaration. |
| `DEDICATED` | server plugin only | Server/dedicated-side code paths. |
| `DEBUG` / `TRACE` | per configuration | Standard. |

## Game assembly references & the publicizer

Each plugin references the SE game assemblies it actually needs **directly from the install folder**
(`$(Bin64)` for the client, `$(Dedicated64)` for the server) with `<Private>False</Private>` so they
are not copied to the output. The .NET facade assemblies (`System.Runtime`, `System.Collections`,
…) are deliberately **not** referenced from the game folder — they come from the target framework —
to avoid `MSB3243/MSB3245/MSB3277` conflict warnings.

Because the plugin patches and reads many non-public game members, both projects use the
**[Krafs.Publicizer](https://github.com/krafs/Publicizer)** package to expose `Sandbox.Game`,
`SpaceEngineers.Game` (and, on the client, `Sandbox.Graphics`) members as public at compile time:

```xml
<PublicizerRuntimeStrategies>Unsafe;IgnoresAccessChecksTo</PublicizerRuntimeStrategies>
<Publicize Include="Sandbox.Game"/>
<Publicize Include="SpaceEngineers.Game"/>
```

A list of **`<DoNotPublicize>`** entries excludes C# *events* — publicizing an event would expose its
backing delegate field and cause `CS0229` ambiguity at every `+=`/`-=`/`?.Invoke` site. The runtime
side of this is the [`IgnoresAccessChecksToAttribute`](./Shared-Utilities.md) declaration plus
[`GameAssembliesToPublicize.cs`](../../Shared/Utilities/GameAssembliesToPublicize.cs).

> Where the publicizer makes a member directly accessible, the code calls it directly; the
> [Shared Extension Methods](./Shared-Extensions.md) remain only for the access that still needs a
> wrapper. Older reflection-based access has largely been replaced by publicized access
> (see commit history).

> **Caveat — `protected virtual` game members.** The two publicizers do not agree on every member.
> Krafs (local `LOCAL_BUILD`) publicizes everything, so a local build compiles even when a member is
> `protected virtual`. The Pulsar/Magnetar **source-compile** publicizer, however, leaves
> `protected virtual`/`override`/`abstract` members `protected` — widening a virtual member's
> accessibility would break override chains, since a C# `override` cannot change accessibility.
> A direct call to such a member therefore builds locally but fails the production source-compile
> with `CS0122`. These members (currently `MyProjectorBase.SetTransparency` and
> `MyMechanicalConnectionBlockBase.Attach`, both `protected virtual`) must stay behind the
> reflection wrappers in [Shared Extension Methods](./Shared-Extensions.md). Plain (non-virtual)
> `protected`, `private`, and `internal` members are exposed by both publicizers and can be called
> directly.

Other key package references: **Lib.Harmony 2.4.2** (patching) and **Mono.Cecil 0.11.6** (IL
inspection for the [`EnsureOriginal`](./Shared-Utilities.md) / [transpiler](./Shared-Utilities.md)
machinery).

## Validation and deployment

The plugin projects have two MSBuild targets, taken from the server plugin template, and the
API example projects follow the same pattern:

1. **`ValidateProps`** (before the build) fails with a clear message if `Bin64`, `Dedicated64` or
   Magnetar's `PluginSdk.dll` cannot be found.
2. **`DeployPlugin`** (after a successful build) copies the plugin into the loader's `Local`
   folder, but only if the loader folder is set explicitly. A plain build deploys nothing.

| Project | Property | Deployed to |
| ------- | -------- | ----------- |
| `ClientPlugin` | `Pulsar` | `<Pulsar>/Legacy/Local/MultigridProjector/` (`net48`) or `<Pulsar>/Interim/Local/MultigridProjector/` (`net10.0`, falls back to `Legacy`), as `plugin.dll`, `plugin.pdb` and `plugin.xml` |
| `ServerPlugin` | `MagnetarData` | `<MagnetarData>/Local/` as `MultigridProjector.dll`, `.pdb` and `.dll.xml` (`net10.0` build only) |
| `ModApiTest` | `Mods` | `<Mods>/Multigrid Projector Mod API Test/`, completed with the API sources, see [Examples.md](./Examples.md) |
| `IngameApiTest` | `IngameScripts` | `<IngameScripts>/Multigrid Projector Ingame API Test/`, see [Examples.md](./Examples.md) |

Set these in `Directory.Build.props.user` or pass them to a single build with `-p:`. To test a
working copy, prefer a loader development folder over deployment, see [../Building.md](../Building.md).

## See also

- [../Building.md](../Building.md) — prerequisites and build commands (user-facing).
- [Shared Utilities & Infrastructure](./Shared-Utilities.md) — `EnsureOriginal`, publicizer runtime glue.
- [Public-API.md](./Public-API.md) — how the API project is consumed downstream.
