# Client GUI Dialogs

This module contains the MyGui-based modal dialogs that surface client-side features to the player inside the Space Engineers game client. Each dialog is implemented as a static factory class that constructs and returns a `MyGuiScreenMessageBox` (hijacked to avoid building a full screen from scratch), then registers callbacks and additional controls on the returned instance before it is pushed onto the screen stack by the calling feature class.

Three dialogs are provided: `CraftDialog` pairs with the `CraftProjection` feature (Bill of Materials / assemble workflow), `AlignerDialog` pairs with the `ProjectorAligner` feature (interactive projection alignment), and `ProjectionDialog` pairs with the `RepairProjection` feature (compatibility-mode welding warnings). All three live in the `MultigridProjectorClient.Menus` namespace.

See [Client-Features.md](./Client-Features.md) for the feature classes that drive these dialogs, and [Client-Settings.md](./Client-Settings.md) for the `Config` values that `ProjectionDialog` reads to decide which sections to include.

---

## Files

| File | Lines | Dialog | Purpose |
|------|-------|--------|---------|
| [CraftDialog.cs](../../ClientPlugin/Menus/CraftDialog.cs) | 281 | `CraftDialog` | Bill-of-Materials viewer and assemble dispatcher for the Assemble Projection feature |
| [AlignerDialog.cs](../../ClientPlugin/Menus/AlignerDialog.cs) | 137 | `AlignerDialog` | Keybind reference sheet shown when the Projection Alignment mode is entered |
| [ProjectionDialog.cs](../../ClientPlugin/Menus/ProjectionDialog.cs) | 106 | `ProjectionDialog` | Compatibility-mode and unsupported-welding warning dialogs for the Repair Projection feature |

---

## CraftDialog

*`internal static class CraftDialog` — namespace `MultigridProjectorClient.Menus`*

Paired feature: `CraftProjection` (see [Client-Features.md](./Client-Features.md)).

`CraftDialog` presents the player with a sortable component table showing what is missing, what is already in inventory, and what is required by the blueprint. It is built by repurposing a `MyGuiScreenMessageBox` (Info style, YES/NO/CANCEL buttons), injecting a four-column `MyGuiControlTable` and adding a fourth "Assemble All" button. The three original buttons are relabelled and their click handlers replaced.

**What the player can do:**

| Button | Action |
|--------|--------|
| **Assemble Missing** (Yes) | Queues all rows whose Missing column > 0 to the selected assembler |
| **Assemble Selected** (No) | Queues the highlighted row (enabled only when a row with Missing > 0 is selected) |
| **Copy BoM** (Cancel) | Copies an Isy-compatible Bill of Materials text to the clipboard; does **not** close the dialog |
| **Assemble All** (extra) | Queues all Blueprint-column quantities to the assembler regardless of inventory |

Column header clicks sort the table: numeric columns sort descending by default, the Component (name) column sorts ascending. Clicking the same column again reverses the order.

### Member Table

| Member | Kind | Description |
|--------|------|-------------|
| `CreateDialog(assemblerName, rows, bomLines, assembleFunc, onClosing)` | `public static MyGuiScreenMessageBox` | Factory method; builds and returns the fully configured dialog. `assembleFunc` is `null` when no assembler is selected (assemble buttons are then disabled). `onClosing` is forwarded to `MyGuiSandbox.CreateMessageBox`. |
| `Assemble(assembleFunc, table, column)` | `private static void` | Iterates every row in `table` and dispatches `assembleFunc` with the `MyDefinitionId` and the integer value from `column`. |
| `Assemble(assembleFunc, row, column)` | `private static void` | Single-row overload used by the "Assemble Selected" handler. |
| `CopyBom(bomLines)` | `private static void` | Joins `bomLines` with newlines, writes to the system clipboard via `MyClipboardHelper`, and shows a 6-second HUD notification. |
| `GetCellText(row, column)` | `private static string` | Reads the display text from a table cell. |
| `GetCellData<T>(row, column)` | `private static T` | Reads the typed `UserData` payload from a table cell (used to extract `MyDefinitionId` and `int` quantities). |
| `SortRows(ref rows, column, inverse)` | `private static void` | Sorts a `List<Row>` in place; numeric cells sort by value (ties break by name), string cells sort alphabetically; optionally reversed. |
| `SortByColumn(table, column, inverse)` | `private static void` | Removes all rows from the live table, re-inserts them in sorted order, and restores the previously selected row. |

**Table columns** (indices 0–3):

| Index | Header | Content type |
|-------|--------|-------------|
| 0 | Component | `string` display / `MyDefinitionId` UserData |
| 1 | Missing | `int` (total components lacking from inventory) |
| 2 | Inventory | `int` (components already held) |
| 3 | Blueprint | `int` (total required by blueprint) |

---

## AlignerDialog

*`internal static class AlignerDialog` — namespace `MultigridProjectorClient.Menus`*

Paired feature: `ProjectorAligner` (see [Client-Features.md](./Client-Features.md)).

`AlignerDialog` is a read-only reference dialog shown when the player enters the interactive projection-alignment mode. It explains that all keyboard/mouse input will be captured, describes the suspend-with-Sprint mechanic, and lists the six translation and six rotation keybinds drawn live from the player's current input bindings. The dialog has a single "Acknowledge" button. When the dialog is dismissed (via `DataUnloading`) the `onClosing` callback notifies the feature class so it can stop the alignment session.

The layout uses three overlapping `MyGuiControlMultilineText` panels:

| Panel | Alignment | Content |
|-------|-----------|---------|
| `messageBoxText` (existing) | Left | Descriptive text and action labels |
| `keybindText` (injected) | Right | Resolved key/button name strings for each action |
| `centerText` (injected) | Center | Section headings ("Translation Controls:", "Rotation Controls:") |

Keybind resolution queries `MyInput.Static.GetGameControl` for each `MyControlsSpace` entry and assembles primary key, secondary key, and mouse button names separated by ` | `.

### Member Table

| Member | Kind | Description |
|--------|------|-------------|
| `CreateDialog(onClosing)` | `public static MyGuiScreenMessageBox` | Factory method. Returns the configured dialog; hooks `DataUnloading` to `onClosing`. |
| `GetControlType(controlEnums)` | `private static string` | Resolves one or more `MyStringId` game controls to a ` | `-separated string of bound key/button names; returns an empty string when nothing is bound. |
| `MessageCaption` | `private static readonly StringBuilder` | Caption: "Multigrid Projector - Projection Alignment". |
| `HeadingText` | `private static readonly StringBuilder` | Center-aligned section headings with blank-line padding to align with the label rows. |
| `MessageText` | `private static readonly StringBuilder` | Left-aligned description and per-action label lines. |
| `KeybindText` | `private static readonly StringBuilder` | Right-aligned resolved keybind strings, computed once at class initialization. |
| `KeySplitter` | `private const string` | `" | "` — separator between multiple bindings for one action. |

---

## ProjectionDialog

*`internal static class ProjectionDialog` — namespace `MultigridProjectorClient.Menus`*

Paired feature: `RepairProjection` (see [Client-Features.md](./Client-Features.md)).

`ProjectionDialog` produces two distinct dialogs depending on the server state detected at runtime.

**`CreateDialog()`** — Compatibility-mode notice. Shown when the server does **not** have the Multigrid Projector plugin and the client falls back to manual block placement. The dialog body always contains a base explanation and a block-compatibility note; two optional sections are appended based on `Config.Current` (see [Client-Settings.md](./Client-Settings.md)):

| Config flag | Section appended | Height added |
|-------------|-----------------|-------------|
| `Config.Current.ShipWelding == true` | "Ship Welders" — explains server-side welder handling | +0.10 |
| `Config.Current.ConnectSubgrids == true` | "Connect Subgrids" — explains mechanical-block subpart copying | +0.15 |

The single button is relabelled "Acknowledge".

**`CreateUnsupportedDialog()`** — Welding-unsupported notice. Shown when client welding is disabled **and** the server has no MGP plugin. Fixed size (0.65 × 0.25), one-sentence message, "Acknowledge" button.

Both dialogs increase `BackgroundColor` opacity and set text alignment to left-top.

### Member Table

| Member | Kind | Description |
|--------|------|-------------|
| `CreateDialog()` | `public static MyGuiScreenMessageBox` | Returns the compatibility-mode dialog; body is assembled at call time based on `Config.Current`. |
| `CreateUnsupportedDialog()` | `public static MyGuiScreenMessageBox` | Returns the minimal "welding unsupported" dialog for when neither client welding nor server MGP is available. |
| `MessageCaption` | `private static readonly StringBuilder` | Caption: "Multigrid Projector - Compatibility Mode". |
| `MessageText` | `private static readonly StringBuilder` | Base paragraph always shown: explains compatibility mode and its limitations. |
| `ShipWeldingText` | `private static readonly StringBuilder` | Optional section appended when `Config.Current.ShipWelding` is true. |
| `ConnectSubgridsText` | `private static readonly StringBuilder` | Optional section appended when `Config.Current.ConnectSubgrids` is true. |
| `CompatibilityText` | `private static readonly StringBuilder` | Closing section listing vanilla/modded block support; always appended last. |

---

## Cross-References

- [Client-Features.md](./Client-Features.md) — `CraftProjection`, `ProjectorAligner`, and `RepairProjection` are the feature classes that construct and push these dialogs.
- [Client-Settings.md](./Client-Settings.md) — `Config.Current.ShipWelding` and `Config.Current.ConnectSubgrids` control which sections `ProjectionDialog.CreateDialog()` includes.
- [Client-Utilities.md](./Client-Utilities.md) — shared utility helpers available to client-side code.
