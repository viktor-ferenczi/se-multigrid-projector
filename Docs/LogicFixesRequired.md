# Logic Fixes Required — `magnetar` branch review

Review of every change on the `magnetar` branch relative to `main`. The branch goal was to:

- remove Torch and Dedicated Server support,
- add a Magnetar server plugin,
- rework the configuration mechanism,
- apply renamings,
- use the Krafs publicizer instead of reflection wherever practical.

This document records whether any plugin logic or Harmony patch that must be kept for correct
in‑game behavior (client or server) was lost or broken during that work, and lists the fixes
needed.

> Code-only review. Nothing was modified. A documentation effort is in progress in parallel; only
> source files were read, so the conclusions here are not affected by doc changes.

---

## Verdict

**No core game logic or Harmony patch is missing or broken.** The migration is clean:

- All Harmony patches (client, server, shared) are present and correct.
- The server session lifecycle, the in‑game Mod API / Programmable‑Block API, the shared
  projection logic, and `EnsureOriginal` patch‑safety verification are all preserved.
- Every reflection → publicizer conversion that was checked resolves to a publicized game member
  with a matching signature (verified against the decompiled game code).

The only discrepancies found are **minor client‑side UI regressions** and **cosmetic naming
leftovers** from the rename. None of them break in‑game functionality. They are listed below with
recommended fixes; all are optional/low priority.

The single thing this review **cannot** confirm without the game assemblies is that both projects
actually compile (`$(Dedicated64)` / `$(Bin64)` are not available here). A build of `ClientPlugin`
and `ServerPlugin` on a machine with the game installed is the recommended final check — see
[Verification](#verification-recommended).

---

## What was verified intact

| Area | Result |
|------|--------|
| Shared patches (`Shared/Patches/`, 6 files) | Identical to `main` (`MultigridProjector/Patches`) — pure moves |
| Client patches (`ClientPlugin/Patches/`, 22 files) | Same set as `main`; 3 changed files are clean reflection→publicizer conversions, rest identical |
| Server patches (`ServerPlugin/Patches/`, 16 files) | **Identical to `main`'s Dedicated (Harmony) versions**, except `MyProjectorBase_Remap.cs` which is a correct Torch‑PatchShim→Harmony conversion |
| Patch application | `Harmony.PatchAll(Assembly.GetExecutingAssembly())` in both `ClientPlugin/Plugin.cs` and `ServerPlugin/Plugin.cs`; shared patches are compiled into both assemblies via `Shared.projitems`, so they are picked up |
| Server session lifecycle | Preserved via `ServerPlugin/PluginSession.cs` (`MySessionComponentBase`, `AfterSimulation`) — it creates, updates and disposes `MultigridProjectorSession`, replacing the old Torch `SessionStateChanged` wiring |
| In‑game Mod API / PB API | `Shared/Logic/MultigridProjectorSession.cs` is byte‑identical to `main`; it registers the mod‑message handler and the PB API. The session runs on the server, so the API works there |
| `EnsureOriginal` verification | Attribute‑based (hashes of patched method bodies); 39 `EnsureOriginal(...)` attributes in both branches. `VerifyAll()` still called in both plugins |
| Config null‑safety | `Shared/Config/PluginConfig.Current` defaults to `DefaultPluginConfig` (`PreviewBlockVisuals => true`), so `MultigridProjection.SetPreviewBlockVisuals` is safe before the plugins assign `Current` |
| `SetPreviewBlockVisuals` | Old Torch‑only field replaced by `=> PluginConfig.Current.PreviewBlockVisuals`; server exposes it via PluginSdk (`ServerPlugin/PluginConfig.cs`), client hard‑codes `true` |
| Extension reflection→publicizer rewrites | `MyProjectorBaseExtensions`, `MyCubeBlockExtensions`, `MyCubeGridExtensions`, `MyBlockGroupExtensions`, `MyMechanicalConnectionBlockBaseExtensions` — every removed wrapper's call site was checked; the game methods are publicized and (where the wrapper supplied defaults) carry matching default parameter values: `AddGroup`, `Attach`, `RecreateTop`, `SetAngleToPhysics`, `SelectAvailableBlocks`/`SelectButton`, `RemoveProjection`, `SendNewBlueprint`, `UpdateSounds`/`UpdateText`, `SetTransparency`, `SetRotation`, `CheckMissingDlcs`, `IsProjecting`, `RayCastBlocksAllOrdered`, etc. |
| `Construction.cs` / `UpdateBlock.cs` | Reflection/Expression‑tree spawn path replaced by direct publicized calls (`MyCubeBuilder.BuildData/Author/GridSpawnRequestData`, `MyMultiplayer.RaiseStaticEvent`). **Correctly keeps reflection for the `OnBlockAdded` event** (events are intentionally excluded from publicizing) |
| Menus/Extra | Pure config‑API renames (`Config.CurrentConfig.X` → `Config.Current.X`) plus field→property swaps verified to be exact pass‑throughs (`MyGuiScreenBase.Controls => m_controls`, `MyShipToolBase.DetectorSphere => m_detectorSphere`) |
| Publicizer config | `Sandbox.Game`, `SpaceEngineers.Game` (both), `Sandbox.Graphics` (client) publicized; events explicitly `DoNotPublicize`d; `IgnoresAccessChecksTo` entries match. `LangVersion` 14 supports the `field` keyword used in `ServerPlugin/PluginConfig.cs` |
| `Shared.projitems` | Exactly matches the 47 `.cs` files on disk — no omissions, no phantom entries. Imported by both `ClientPlugin.csproj` and `ServerPlugin.csproj` |
| `.il` reference files removed | Were `#if DEBUG`‑only developer dumps written by `TranspilerHelpers.RecordCode` (never read for verification) — safe to delete |

---

## Discrepancies and fixes

### D1 — Client config dialog lost the "Reset to Default" button  *(low, client UX)*

- **Was:** `MultigridProjectorClient/Menus/ConfigMenu.cs` repurposed the message‑box "No" button as
  **"Reset to Default"**, calling `Config.ResetConfig()`.
- **Now:** `ClientPlugin/Settings/SettingsScreen.cs` shows only a Close button; there is no reset
  affordance.
- **Impact:** Users can no longer reset settings to defaults from the UI. No functional/game impact.
- **Fix (optional):** Add a `Button` element (the framework already has
  `ClientPlugin/Settings/Elements/Button.cs`) to `Config.cs` / the `Simple` layout that copies each
  property from `Config.Default` onto `Config.Current` and refreshes the dialog. Or accept the loss
  and note it in the changelog.

### D2 — Client config dialog lost the inter‑option gating *(low, client UX)*

- **Was:** the old dialog disabled (greyed out) **"Ship Welding"** and **"Connect Subgrids"** while
  **"Client Welding"** was unchecked, and toggled them live (`ClientWeldingSetter`).
- **Now:** the attribute‑driven `Config.cs` renders the three checkboxes independently; any
  combination can be set.
- **Impact:** Cosmetic only. The runtime checks each flag independently (`Construction.cs`,
  `ShipWelding.cs`), so the "Ship/Connect on, Client Welding off" combination is pointless but not
  harmful — no crash path was found.
- **Fix (optional):** Either (a) leave as‑is and document, or (b) if the gating is desired, add a
  dependency mechanism to the settings framework (e.g. a predicate that disables dependent
  checkboxes). Recommended: confirm with a quick in‑game test that the un‑gated combination is inert,
  then accept (a).

### D3 — Client config file root element renamed, resets settings on upgrade *(low, one‑time)*

- **Was:** serialized as `<ConfigObject>` (`MultigridProjectorClient/Utilities/Config.cs`).
- **Now:** serialized as `<Config>` (`ClientPlugin/Settings/ConfigStorage.cs`). Same file path
  (`%AppData%/SpaceEngineers/Storage/MultigridProjector.cfg`) and same per‑setting element names; only
  the **root element** differs.
- **Impact:** An existing user's old file fails to deserialize; `ConfigStorage.Load()` catches the
  exception and returns `Config.Default`, so settings silently reset to defaults **once** after the
  upgrade. (Most defaults are `true`, limiting the surprise.)
- **Fix (optional):** Add `[XmlRoot("ConfigObject")]` to `Config` (or a tiny one‑time migration that
  reads the old root) if preserving existing users' settings matters; otherwise document the one‑time
  reset.

### D4 — Stale namespaces / usings left over from the rename *(cosmetic, no functional impact)*

The directories were renamed (`MultigridProjector→Shared`, `MultigridProjectorClient→ClientPlugin`,
`MultigridProjector{Server,Dedicated}→ServerPlugin`) but several namespaces/usings still carry the
old names:

- `ServerPlugin/PluginSession.cs` is in `namespace MultigridProjectorDedicated`.
- `ServerPlugin/Plugin.cs` has `using MultigridProjectorDedicated;`,
  `using MultigridProjectorClient;`, and `using MultigridProjectorServer.MultigridProjector.Utilities;`.
- `ServerPlugin/Patches/MyProjectorBase_Remap.cs` is in `namespace MultigridProjector.Patches`
  (the other server patches are in `MultigridProjector.Patches` too, mixed with `…Server…`).
- Moved shared/client files keep their original `MultigridProjector*` / `MultigridProjectorClient.*`
  namespaces under the new folders.

- **Impact:** None. C# namespaces are independent of folders, and `Harmony.PatchAll` is
  namespace‑agnostic. This is purely a tidiness/consistency item.
- **Fix (optional):** Normalize namespaces if desired, in a dedicated mechanical commit. **Do not**
  rename or alter the `EnsureOriginal`/patch types or their hash attributes while doing so — leave
  patch identity untouched. Because this is broad and risk‑for‑no‑gain, it is reasonable to defer.

---

## Intentional removals — confirmed correct (no action needed)

Listed for completeness; each was checked and is safe to drop on a Torch‑free, Magnetar‑only branch:

- **Torch + Dedicated plugin shells** (`MultigridProjectorPlugin.cs` ×2), `Properties/AssemblyInfo.cs`
  — replaced by `ClientPlugin/Plugin.cs` and `ServerPlugin/Plugin.cs` (assembly version now set in
  `Plugin.cs` / csproj).
- **Torch‑PatchShim server patch copies** (`MultigridProjectorServer/Patches/*`) — these were
  duplicates of the Dedicated Harmony patches, which are the ones carried forward into `ServerPlugin`.
- **`EnsureOriginalTorch.cs`** — Torch‑specific; the one patch that used it (`MyProjectorBase_Remap`)
  was converted to standard `[HarmonyPatch]` + `[EnsureOriginal("73db0d9e")]`.
- **`MultigridProjectorTorchAgent.cs`** — exposed the API to *other Torch plugins* via reflection;
  irrelevant without Torch. The in‑game Mod/PB API (used by scripts and mods) is unaffected.
- **`ConfigView.xaml(.cs)` + `MultigridProjectorConfig.cs` (Torch)** — Torch WPF config UI; replaced
  by PluginSdk config (`ServerPlugin/PluginConfig.cs`) rendered remotely by Quasar.
- **`MultigridProjectorCommands.cs`** — was entirely inside `#if INCOMPLETE_UNTESTED` (dead,
  never‑compiled code referencing config options that no longer exist).
- **`MyMotorStatorExtensions.cs`** — the single `SetAngleToPhysics()` reflection wrapper; the call
  site now invokes the publicized `MyMotorStator.SetAngleToPhysics()` directly.
- **`*.original.il` / `*.patched.il`** — DEBUG‑only IL dumps (see table above).
- **`.run/*` (Torch/Dedicated/Pulsar legacy)**, `LinkPulsar.bat`, old solution files — tooling, no
  runtime effect.

---

## Verification (recommended)

Because the game assemblies are not available in this review environment, run these on a machine with
the game/dedicated server installed:

1. **Build both plugins** (`net48` and `net10.0`):
   - `ClientPlugin` against `$(Bin64)` — confirms all client‑side publicizer conversions resolve.
   - `ServerPlugin` against `$(Dedicated64)` — confirms the shared code (incl. `ReferenceFixer`'s
     `SelectAvailableBlocks`/`SelectButton`, which need `SpaceEngineers.Game` publicized and
     `Sandbox.Graphics` referenced — both present) compiles for the server target.
2. **Client smoke test:** load a multigrid blueprint into a projector, weld subgrids, connect
   subgrids, repair/align/craft/highlight features, and open the settings dialog (verify save on
   close).
3. **Server smoke test (Magnetar):** confirm the plugin loads, `EnsureOriginal.VerifyAll()` passes,
   `MultigridProjectorSession` ticks, subgrid welding works, and the `PreviewBlockVisuals` PluginSdk
   option toggles preview visuals.
4. **Mod/PB API:** run a Programmable Block script against the MGP API on a Magnetar server to confirm
   the API is registered server‑side.

---

## Summary

The `magnetar` branch preserves all functional plugin logic and Harmony patches. The reflection→
publicizer migration was done carefully and correctly. The outstanding items (D1–D4) are minor
client‑UI regressions and cosmetic naming leftovers, all optional. The recommended next step is a
compile + in‑game smoke test, since compilation is the one thing that could not be checked here.
