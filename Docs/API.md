## Mod & PB API

The plugin exposes an API so mods and in-game (Programmable Block) scripts can query and control
projections.

The API surface lives in the [MultigridProjectorApi](../MultigridProjectorApi/Api)
shared project. Worked examples are included in this repository:

- [ModApiTest](../ModApiTest) — a mod that uses the Mod API via the
  [MultigridProjectorModAgent](../MultigridProjectorApi/Api/MultigridProjectorModAgent.cs)
- [IngameApiTest](../IngameApiTest) — a Programmable Block script that uses the PB API, the script includes the agent.
