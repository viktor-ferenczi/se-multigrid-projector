# Multigrid Projector for Space Engineers

Enables seamless building projections with multiple subgrids, also provides a few projector related QoL improvements.

- Build and repair PDCs, mechs and more
- Works both in survival and creative
- Works both in single player and multiplayer

- **Client plugin** — loaded by [Pulsar](https://github.com/SpaceGT/Pulsar) in the game client.
- **Server plugin** — loaded by [Magnetar](https://magnetar.se) on the dedicated server, managed
  remotely via [Quasar](https://github.com/viktor-ferenczi/Quasar).

_In multiplayer full functionality is supported only if the server also has the Multigrid Projector plugin loaded.
If only the client has the plugin, then some limited functionality is still available, but it is not seamless._

For support please join the [Pulsar Discord](https://discord.gg/z8ZczP2YZY).

Please consider supporting my work on [Patreon](https://www.patreon.com/semods) or one time via [PayPal](https://www.paypal.com/paypalme/vferenczi/).

*Thank you and enjoy!*

## Installation

### Client

Have [Pulsar](https://github.com/SpaceGT/Pulsar) installed. Link to the Installer is in the README there.

1. Enable the **Multigrid Projector** plugin from the **Plugins** dialog.
2. Apply and restart the game.

### Server

<details>
<summary>Quasar</summary>

Have [Quasar](https://github.com/viktor-ferenczi/Quasar) installed and a server created.

1. Enable the **Multigrid Projector** plugin in your config profile(s).
2. Restart the server, so it picks up the plugin

The configuration is on Quasar's Web UI.
</details>

<details>
<summary>Magnetar</summary>

For standalone [Magnetar](https://github.com/viktor-ferenczi/Magnetar/)
you need to reference the Performance plugin from the `Current` profile.

Edit the profile:
- Linux: `~/.config/Magnetar/Profiles/Current.xml`
- Windows: `%AppData%\Magnetar\Logacy\Profiles\Current.xml`

Directly inside the `<GitHub>` element insert:
```xml
    <GitHubPluginConfig>
      <Id>viktor-ferenczi/se-multigrid-projector</Id>
    </GitHubPluginConfig>
```

Configuration file is `MultigridProjector.cfg`, created in the `SpaceEngineersDedicated` folder.
**FIXME:** Include a default config here, because only the ones with non-default values are saved.
</details>

## Documentation

Full documentation lives in the [Docs](Docs) folder. Start at the
**[Documentation Handbook](Docs/Handbook.md)** — the entry point to everything below.

**User guides**

- [Installation](Docs/Installation.md) — client (Pulsar) and server (Quasar / standalone Magnetar)
- [Troubleshooting](Docs/Troubleshooting.md) — common issues, Proton/Linux notes, getting help
- [Building from source](Docs/Building.md) — prerequisites and local build/deploy
- [Mod & PB API](Docs/API.md) — scripting API for mods and programmable blocks

**Developer reference**

- [Handbook](Docs/Handbook.md) — table of contents for all docs
- [Architecture](Docs/Architecture.md) — how the plugin fits together (read this first)
- [Source File Index](Docs/Index.md) — every source file, grouped and linked
- [Reference pages](Docs/Reference) — per-subsystem developer reference (engine, patches, API, client, server, …)

- [Credits](#credits)

## Installation

- **Client:** install via [Pulsar](https://github.com/SpaceGT/Pulsar) — see
  [Docs/Installation.md](Docs/Installation.md#client-plugin-pulsar).
- **Server:** install via [Quasar](https://github.com/viktor-ferenczi/Quasar), or into a standalone
  [Magnetar](https://magnetar.se) by editing its profile — see
  [Docs/Installation.md](Docs/Installation.md#server-plugin-magnetar--quasar).

Torch and the legacy Dedicated Server plugin loader are no longer supported.

## Want to know more?

- [SE Mods Discord](https://discord.gg/PYPFPGf3Ca) — FAQ, troubleshooting, support, bug reports, discussion
- [Pulsar Discord](https://discord.gg/z8ZczP2YZY) — everything about plugins
- [Test world (Rings)](https://steamcommunity.com/sharedfiles/filedetails/?id=2420963329)

## Credits

### Contributors
- Viktor Ferenczi
- @SpaceGT
  * Client side welding without server plugin
  * Enqueue missing parts into assemblers (Assemble Projection)
  * Highlighting weldable or incomplete projected blocks (Highlight Blocks)
  * Build system fixes, better linking of dependencies
- @mkaito
  * Crash fix
  * Copy BoM
- @Pas2704
  * Bug fixes

### Patreon Supporters

#### Admiral level
- BetaMark
- Mordith - Guardians SE
- Robot10
- Casinost
- wafoxxx

#### Captain level
- CaptFacepalm
- Diggz
- lazul
- jiringgot
- Kam Solastor
- Linux123123
- NeonDrip
- NeVaR
- opesoorry
- jiringgot
- N CG
- NeVaR
- Jimbo

#### Testers
- Robot10 - Test Lead
- Radar5k
- LTP
- Mike Dude
- CMDR DarkSeraphim88
- ced
- Precorus
- opesoorry
- Spitfyre.pjs
- Random000
- gamemasterellison
- Babyboarder
- LordJ

### Creators
- Space - Pulsar, Multigrid Projector client side build support and extras
- avaness - Plugin Loader, Racing Display
- SwiftyTech - Stargate Dimensions
- Mike Dude - Guardians SE
- Fred XVI - Racing maps
- Kamikaze - M&M mod
- Keleios
- LTP

**Thank you very much for all your support and hard work on testing!**

## License

See [LICENSE](LICENSE).
