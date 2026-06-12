# Building from source

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

The build references the game assemblies and the Pulsar/Magnetar installations through paths in
`Directory.Build.props`. On most setups they are auto-detected (Steam install locations, the default
Pulsar/Magnetar directories). If auto-detection fails, edit `Directory.Build.props` and fill in the
paths:

- `Bin64` — folder containing `SpaceEngineers.exe` (client `Bin64`)
- `Dedicated64` — folder containing `SpaceEngineersDedicated.exe` (`DedicatedServer64`)
- `Pulsar` — the Pulsar installation folder (holds `Libraries/...`)
- `Magnetar` — the Magnetar installation folder (holds `Bin/PluginSdk.dll`)

You can also run `setup.py` to fill these in interactively.

## Build

```sh
# Client plugin
dotnet build ClientPlugin/ClientPlugin.csproj -c Debug

# Server plugin
dotnet build ServerPlugin/ServerPlugin.csproj -c Debug
```

On a successful build each project's `Deploy` script (`Deploy.bat` on Windows, `Deploy.sh` on Linux,
run as a post-build step) copies the resulting DLL to the matching local plugin folder:

- Client → Pulsar's `Local` plugins folder
- Server → Magnetar's `Local` plugins folder

For a release build use `-c Release`. Always test a release build before publishing — Pulsar compiles
the client plugin from source on the player's machine, so behaviour can differ from a local build.

## Notes

- Both targets produce an assembly named `MultigridProjector.dll`.
- The shared core keeps its own logging (`PluginLog`) and game-code verification (`EnsureOriginal`)
  rather than the template defaults, to stay a faithful port.
- If a build cannot deploy (it loops or fails to copy the DLL), a game or server process is probably
  locking the file — close it and rebuild.
