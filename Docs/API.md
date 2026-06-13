## Mod & PB API

The plugin exposes an API so mods and in-game (Programmable Block) scripts can query and control
projections.

The API surface lives in the [MultigridProjectorApi](../MultigridProjectorApi/Api)
shared project. Worked examples are included in this repository:

- [ModApiTest](../ModApiTest) — a mod that uses the Mod API via the
  [MultigridProjectorModAgent](../MultigridProjectorApi/Api/MultigridProjectorModAgent.cs)
- [IngameApiTest](../IngameApiTest) — a Programmable Block script that uses the PB API, the script includes the agent.

## Developer reference

For the full API contract and how it is consumed, see the developer reference:

- [Public Mod & PB API](Reference/Public-API.md) — every API method, the mod/PB handshake, versioning, and the fallback shim.
- [API Examples (Mod & PB)](Reference/Examples.md) — walkthrough of the two worked examples above.
- [Core Projection Engine](Reference/Core-Projection-Engine.md) — `MultigridProjectorApiProvider`, which produces the API on the plugin side.

See the [Documentation Handbook](Handbook.md) for everything else.
