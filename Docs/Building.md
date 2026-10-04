# Building from source

> Part of the [Documentation Handbook](Handbook.md). For the solution structure, multi-targeting,
> publicizer setup and deploy pipeline behind these commands, see
> [Build & Project Layout](Reference/Build-And-Project-Layout.md).

## Prerequisites

- [Space Engineers](https://store.steampowered.com/app/244850/Space_Engineers/) (for the client plugin)
- [Space Engineers Dedicated Server](https://store.steampowered.com/app/298740/) (for the server plugin)
- [.NET 10 SDK](https://dotnet.microsoft.com/en-us/download/dotnet/10.0)
- On Windows, also the
  [.NET Framework 4.8.1 Developer Pack](https://dotnet.microsoft.com/en-us/download/dotnet-framework/net481)
  (the client plugin multi-targets `net48` and `net10.0`; on Linux only `net10.0` is built)
- [Pulsar](https://github.com/SpaceGT/Pulsar) — to load and test the client plugin
- [Magnetar](https://magnetar.se) — to load and test the server plugin (provides `PluginSdk.dll`)
- [JetBrains Rider](https://jetbrains.com) or Visual Studio (optional)

## Project layout

- `Shared` — shared project with the general data model, logic, patches and the Mod/PB API of MGP.
  Compiled into both targets.
- `ClientPlugin` — the client target, loaded by Pulsar. Configuration uses the in-game settings
  dialog (`ClientPlugin/Config.cs` + `ClientPlugin/Settings`).
- `ServerPlugin` — the server target, loaded by Magnetar. Configuration uses Magnetar's PluginSdk
  (`ServerPlugin/PluginConfig.cs`), edited remotely via Quasar.
- `Shared/Config/IPluginConfig.cs` — the shared configuration interface both targets implement, so
  shared code can read configuration without knowing which mechanism backs it.

## Configure local paths

The build references the game, the Dedicated Server and Magnetar's `PluginSdk.dll` through folders
declared in `Directory.Build.props`. They are auto-detected from Steam and the default Magnetar
location. If that fails, override them in `Directory.Build.props.user` next to it (gitignored, so
each developer keeps their own paths). Run `setup.py` to create that file with the detected game
and server folders.

- `Bin64`: folder containing `SpaceEngineers.exe`
- `Dedicated64`: folder containing `SpaceEngineersDedicated.exe` (`DedicatedServer64`)
- `Magnetar`: the Magnetar installation folder, holding `Libraries/<launcher>/PluginSdk.dll`

## Build

```sh
dotnet build MultigridProjector.sln -c Debug
```

A build deploys nothing by default. To test your working copy, load it through a loader
development folder instead: start Pulsar or Magnetar with `-sources` and add the repository with
the Sources button. The loader then compiles the plugin from source.

To deploy the build output anyway, set the target folders in `Directory.Build.props.user` or pass
them on the command line:

```sh
dotnet build MultigridProjector.sln -p:Pulsar=$HOME/.config/Pulsar -p:MagnetarData=$HOME/.config/Magnetar/Magnetar
```

- `Pulsar`: the client goes to `<Pulsar>/Legacy/Local/MultigridProjector/` (`net48`) or
  `<Pulsar>/Interim/Local/MultigridProjector/` (`net10.0`)
- `MagnetarData`: the server goes to `<MagnetarData>/Local/`
- `Mods` and `IngameScripts`: the API example mod and script, see
  [Examples](Reference/Examples.md)

For a release build use `-c Release`. Always test a release build before publishing — Pulsar compiles
the client plugin from source on the player's machine, so behavior can differ from a local build.

## Notes

- Both targets produce an assembly named `MultigridProjector.dll`.
- The shared core keeps its own logging (`PluginLog`) and game-code verification (`EnsureOriginal`)
  rather than the template defaults, to stay a faithful port.
- If a deploying build fails to copy the DLL, a game or server process is probably locking the
  file. Close it and rebuild.
