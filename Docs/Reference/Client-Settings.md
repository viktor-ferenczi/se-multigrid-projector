# Client Settings Framework

A reusable, attribute-driven framework (originating from the plugin template) that builds the plugin's in-game configuration dialog entirely from the `Config` class. Placing a GUI-element attribute on a `Config` property (or method) is sufficient to make it appear as an interactive control in the settings screen — no manual wiring required. `SettingsGenerator` reflects over `Config` at startup, constructs typed `Element` wrappers for each annotated member, hands them to a `Layout` that arranges them inside a `SettingsScreen`, and `ConfigStorage` persists the resulting `Config` object to an XML file when the dialog closes.

See [Client-Plugin.md](./Client-Plugin.md) for the `Config` class that this framework renders, and [Configuration.md](./Configuration.md) for the persisted configuration format.

---

## Files

| File | Lines | Purpose |
|------|-------|---------|
| [SettingsGenerator.cs](../../ClientPlugin/Settings/SettingsGenerator.cs) | 149 | Reflects `Config`; orchestrates element creation, layout, and dialog lifecycle |
| [SettingsScreen.cs](../../ClientPlugin/Settings/SettingsScreen.cs) | 70 | `MyGuiScreenBase` subclass; saves config on close |
| [ConfigStorage.cs](../../ClientPlugin/Settings/ConfigStorage.cs) | 44 | XML serialise/deserialise of `Config` to `%UserData%/Storage/<Plugin>.cfg` |
| [Elements/Element.cs](../../ClientPlugin/Settings/Elements/Element.cs) | 10 | `IElement` interface — contract all attribute types implement |
| [Elements/Control.cs](../../ClientPlugin/Settings/Elements/Control.cs) | 30 | Layout metadata wrapper around a `MyGuiControlBase` instance |
| [Elements/Checkbox.cs](../../ClientPlugin/Settings/Elements/Checkbox.cs) | 35 | `[Checkbox]` attribute — `bool` toggle |
| [Elements/Slider.cs](../../ClientPlugin/Settings/Elements/Slider.cs) | 111 | `[Slider]` attribute — `float`/`int` range control with manual-entry dialog |
| [Elements/Dropdown.cs](../../ClientPlugin/Settings/Elements/Dropdown.cs) | 70 | `[Dropdown]` attribute — `enum` combo-box, un-camel-cases member names |
| [Elements/Color.cs](../../ClientPlugin/Settings/Elements/Color.cs) | 86 | `[Color]` attribute — hex text-box + colour swatch for `VRageMath.Color` |
| [Elements/Keybind.cs](../../ClientPlugin/Settings/Elements/Keybind.cs) | 166 | `[Keybind]` attribute — key + Ctrl/Alt/Shift for a `Binding` value |
| [Elements/Button.cs](../../ClientPlugin/Settings/Elements/Button.cs) | 36 | `[Button]` attribute — clickable button bound to a `void` `Config` method |
| [Elements/Textbox.cs](../../ClientPlugin/Settings/Elements/Textbox.cs) | 36 | `[Textbox]` attribute — free-text input for `string` properties |
| [Elements/Separator.cs](../../ClientPlugin/Settings/Elements/Separator.cs) | 46 | `[Separator]` attribute — visual section divider with optional caption |
| [Layouts/Layout.cs](../../ClientPlugin/Settings/Layouts/Layout.cs) | 37 | Abstract base for layout strategies |
| [Layouts/Simple.cs](../../ClientPlugin/Settings/Layouts/Simple.cs) | 108 | Scrollable single-column layout; fills available width proportionally |
| [Layouts/None.cs](../../ClientPlugin/Settings/Layouts/None.cs) | 31 | Pass-through layout (no positioning); controls placed at origin |
| [Tools/Tools.cs](../../ClientPlugin/Settings/Tools/Tools.cs) | 77 | Static helpers: PascalCase→label conversion, hex colour parse/format |
| [Tools/Binding.cs](../../ClientPlugin/Settings/Tools/Binding.cs) | 40 | `Binding` value-type: key + modifier state, press detection |

---

## How it works

```
Config properties/methods
   └─ [CheckboxAttribute] / [SliderAttribute] / [KeybindAttribute] / …
          │  (implements IElement)
          ▼
   SettingsGenerator.ExtractAttributes()
          │  reflects typeof(Config); builds List<AttributeInfo>
          │  each AttributeInfo carries: IElement, property name,
          │  Getter: Func<object>, Setter: Action<object>
          ▼
   SettingsGenerator.CreateConfigControls()
          │  calls IElement.GetControls(name, getter, setter)
          │  each element returns List<Control> (one row)
          ▼
   Layout  (Simple / None)
          │  RecreateControls() — creates parent/scroll panel
          │  LayoutControls()  — positions every Control in its row
          ▼
   SettingsScreen  (MyGuiScreenBase)
          │  adds caption + layout controls to the screen
          │  OnRemoved → ConfigStorage.Save(Config.Current)
          ▼
   ConfigStorage
          XML serialise → %UserData%/Storage/<Plugin>.cfg
          XML deserialise ← on plugin load
```

Each element attribute wires the control's change event directly to the `Setter` delegate (which calls `propertyInfo.SetValue(Config.Current, value)`), so every user interaction is immediately reflected in `Config.Current`. The full config is flushed to disk only when the dialog closes.

---

## Core

### `IElement`

*`interface IElement`*

The contract that every GUI element attribute must satisfy. `SettingsGenerator` discovers attributes by casting to this interface.

| Member | Kind | Description |
|--------|------|-------------|
| `GetControls(name, getter, setter)` | method | Returns the row of `Control` wrappers that represent this element in the dialog |
| `SupportedTypes` | property | List of property types this element can bind to; validated at startup |

---

### `SettingsGenerator`

*`internal class SettingsGenerator`*

Central orchestrator. Constructed once per plugin session; owns the dialog and the active layout.

| Member | Kind | Description |
|--------|------|-------------|
| `Name` | field | Display title taken from `Config.Current.Title` |
| `Dialog` | property | The `SettingsScreen` instance to open |
| `ActiveLayout` | property | Currently active `Layout`; defaults to `None` |
| `SettingsGenerator()` | ctor | Calls `ExtractAttributes()`, creates the initial `None` layout and the dialog |
| `ExtractAttributes()` | static method | Iterates `typeof(Config)` properties and methods; collects `AttributeInfo` for each `IElement` attribute found; validates property types against `SupportedTypes` |
| `CreateConfigControls()` | method | Calls `IElement.GetControls` for every `AttributeInfo`; stores result as `List<List<Control>>` |
| `OnRecreateControls()` | method | Callback given to `SettingsScreen`; invokes `CreateConfigControls`, `RecreateControls`, and `LayoutControls` in order |
| `SetLayout<T>()` | method | Replaces `ActiveLayout` with a new instance of layout type `T`; resizes the dialog |
| `RefreshLayout()` | method | Re-runs `LayoutControls()` on the active layout without recreating controls |

**`AttributeInfo`** (internal helper class):

| Field | Type | Description |
|-------|------|-------------|
| `ElementType` | `IElement` | The attribute instance that created this entry |
| `Name` | `string` | Property or method name from `Config` |
| `Getter` | `Func<object>` | Reads current value from `Config.Current` |
| `Setter` | `Action<object>` | Writes new value to `Config.Current`; `null` for method entries |

---

### `SettingsScreen`

*`internal class SettingsScreen : MyGuiScreenBase`*

The actual in-game dialog window. Thin wrapper: delegates control creation to `SettingsGenerator` via the `GetControls` callback, and triggers a config save on close.

| Member | Kind | Description |
|--------|------|-------------|
| `FriendlyName` | field | Dialog title string |
| `GetControls` | field | Callback supplied by `SettingsGenerator.OnRecreateControls` |
| `UpdateSize(size)` | method | Changes the screen size and forces the close button to refresh |
| `LoadContent()` | override | Triggers `RecreateControls(true)` on load |
| `RecreateControls(constructor)` | override | Adds the caption and then each control returned by `GetControls` |
| `OnRemoved()` | override | Calls `ConfigStorage.Save(Config.Current)` before unloading |

---

### `ConfigStorage`

*`public static class ConfigStorage`*

Persists the `Config` object as XML. The file path is `%UserData%/Storage/<Plugin.Name>.cfg` (resolved via `MyFileSystem.UserDataPath`).

| Member | Kind | Description |
|--------|------|-------------|
| `ConfigFileName` | static field | `"<Plugin.Name>.cfg"` |
| `ConfigFilePath` | static property | Full path: `UserDataPath/Storage/<Plugin.Name>.cfg` |
| `Save(config)` | static method | XML-serialises `config` to `ConfigFilePath`; creates the `Storage` directory if missing |
| `Load()` | static method | Deserialises from `ConfigFilePath`; returns `Config.Default` if the file is absent or malformed (logs a warning on error) |

---

## Elements

### `Control`

*`internal class Control`*

Thin layout-metadata wrapper around a raw `MyGuiControlBase`. Element attributes return `List<Control>` (one per row column). The `Layout` reads the metadata to compute positions and widths.

| Member | Kind | Description |
|--------|------|-------------|
| `LabelMinWidth` | static field | `0.18f` — global minimum width for label columns |
| `GuiControl` | field | The underlying `MyGuiControlBase` |
| `FixedWidth` | field | If set, overrides all sizing calculations |
| `MinWidth` | field | Minimum width when no fixed size is given |
| `FillFactor` | field | Proportional share of remaining row width |
| `OriginAlign` | field | Alignment anchor for position calculations |
| `Offset` | field | Fine-grained positional nudge applied after layout |
| `RightMargin` | field | Gap added to the right of this control |

---

### `CheckboxAttribute`

*`[Checkbox(label?, description?)] : Attribute, IElement`*

Boolean toggle. Supported type: `bool`.

Emits a `MyGuiControlLabel` + `MyGuiControlCheckbox` pair. The checkbox `IsCheckedChanged` event writes to the setter immediately.

---

### `SliderAttribute`

*`[Slider(min, max, step?, type?, label?, description?)] : Attribute, IElement`*

Numeric range control. Supported types: `float`, `int`.

| Constructor parameter | Description |
|----------------------|-------------|
| `Min`, `Max` | Value range |
| `Step` | Minimum slider increment; also controls decimal places for `Float` type |
| `Type` | `SliderType.Integer` or `SliderType.Float` (default) |
| `Label`, `Description` | Override label and tooltip text |

Emits a label, a `MyGuiControlSlider`, and a numeric value label. Secondary click on the slider opens `MyGuiScreenDialogAmount` for keyboard entry. Decimal places are computed as `max(1, ceil(-log10(2 * step)))`.

---

### `DropdownAttribute`

*`[Dropdown(visibleRows?, label?, description?)] : Attribute, IElement`*

Enum selector combo-box. Supported type: `Enum` (any enum).

Populates a `MyGuiControlCombobox` from `Enum.GetNames`; converts PascalCase member names to spaced words via double regex substitution. Selection change writes the parsed enum value to the setter.

| Constructor parameter | Description |
|----------------------|-------------|
| `VisibleRows` | Max visible rows before scrolling (default 20) |

---

### `ColorAttribute`

*`[Color(hasAlpha?, label?, description?)] : Attribute, IElement`*

Hex colour picker. Supported type: `VRageMath.Color`.

| Constructor parameter | Description |
|----------------------|-------------|
| `HasAlpha` | If `true`, accepts 8-digit RGBA hex; otherwise 6-digit RGB |

Emits a label, a square colour-swatch button (border coloured with the current value), and a `MyGuiControlTextbox` for hex input. The text-box `TextChanged` event validates the hex, updates the swatch, and writes to the setter. Invalid input turns the text-box border red without updating the config.

---

### `KeybindAttribute`

*`[Keybind(label?, description?)] : Attribute, IElement`*

Keyboard shortcut picker. Supported type: `Binding`.

Emits five controls per row:
1. Label
2. Key-binding button (shows bound key name; primary click opens `MyGuiScreenOptionsMouseKeyboard.MyGuiControlAssignKeyMessageBox` to rebind; secondary click prompts to unbind)
3. Ctrl checkbox
4. Alt checkbox
5. Shift checkbox

All three modifier checkboxes wire their `IsCheckedChanged` events to read the current `Binding` from the getter, flip the appropriate flag, and write the modified struct back via the setter. After rebind or unbind the button label is refreshed from `MyControl.AppendBoundButtonNames`.

---

### `ButtonAttribute`

*`[Button(label?, description?)] : Attribute, IElement`*

Clickable action button. Supported type: `Delegate` (applied to `Config` methods returning `void`).

The getter returns the method as a `Delegate`; the button `ButtonClicked` handler casts it to `Action` and invokes it. Label defaults to the PascalCase-to-words conversion of the method name.

---

### `TextboxAttribute`

*`[Textbox(label?, description?)] : Attribute, IElement`*

Free-text input. Supported type: `string`.

Emits a label and a `MyGuiControlTextbox` with `fillFactor: 1f`. `TextChanged` writes to the setter on every keystroke.

---

### `SeparatorAttribute`

*`[Separator(caption?)] : Attribute, IElement`*

Visual section divider. Supported type: `object` (apply to any dummy property).

Emits an optional orange caption label and a thin semi-transparent horizontal line that fills the remaining row width. Does not read or write any config value.

---

## Layouts

### `Layout`

*`internal abstract class Layout`*

Base class for all layout strategies. Holds a `GetControls` delegate that retrieves the current `List<List<Control>>` from `SettingsGenerator`.

| Member | Kind | Description |
|--------|------|-------------|
| `SettingsPanelSize` | abstract property | Preferred `Vector2` size for the `SettingsScreen` |
| `GetControls` | protected field | Delegate returning the current list of control rows |
| `RecreateControls()` | abstract method | Creates and returns layout-specific container controls; must add element controls to appropriate parents |
| `LayoutControls()` | abstract method | Positions existing controls; must not create new ones |

---

### `Simple`

*`internal class Simple : Layout`*

The standard scrollable layout. Panel size: `(0.5, 0.7)`.

Wraps all element controls in a `MyGuiControlParent` housed inside a `MyGuiControlScrollablePanel`. Row height is the maximum control height in that row plus `ElementPadding` (0.01). Column widths are computed per-row: fixed-width controls take their exact size; fill-factor controls share the remaining width proportionally; min-width controls clamp to their minimum. Right margins are included in width accounting.

---

### `None`

*`internal class None : Layout`*

Trivial pass-through layout. Panel size: `(0.5, 0.5)`. Adds all controls flat to the screen (no parent wrapper); positions every control at `Vector2.Zero`. Used as the default before `SetLayout<T>()` is called.

---

## Tools

### `Tools` (static class)

*`public static class Tools`*

Utility helpers used by element attributes.

| Member | Kind | Description |
|--------|------|-------------|
| `GetLabelOrDefault(name, label?)` | static method | Returns `label` if non-null; otherwise splits `name` (PascalCase) into words using `[A-Z][a-z]*` regex, lowercases all but the first, and joins with spaces |
| `ToHexStringRgb(color)` | extension method | Formats a `Color` as 6-digit uppercase hex (`RRGGBB`) |
| `ToHexStringRgba(color)` | extension method | Formats a `Color` as 8-digit uppercase hex (`RRGGBBAA`) |
| `TryParseColorFromHexRgb(hex, out color)` | extension method | Parses a 6-digit hex string into a `Color` (alpha forced to 255); returns false on mismatch |
| `TryParseColorFromHexRgba(hex, out color)` | extension method | Parses an 8-digit hex string into a `Color`; returns false on mismatch |

---

### `Binding`

*`public struct Binding`*

Value type representing a keyboard shortcut: one `MyKeys` key plus optional Ctrl/Alt/Shift modifiers. Serialised as part of `Config` (XML). Used exclusively by `KeybindAttribute`.

| Member | Kind | Description |
|--------|------|-------------|
| `Key` | field | `MyKeys` value; `MyKeys.None` means unbound |
| `Ctrl`, `Alt`, `Shift` | fields | Modifier flags |
| `Binding(key, ctrl?, alt?, shift?)` | ctor | Positional constructor |
| `ToString()` | override | Returns `"None"` or a formatted string like `"Ctrl+Alt+F5"` |
| `IsPressed(input)` | method | True when the key is held and all modifiers match exactly |
| `HasPressed(input)` | method | True on the frame the key is first pressed (new key press) with matching modifiers |
| `AreModifiersMatch(input)` | private method | Checks exact Ctrl/Alt/Shift state against live input |

---

```json
{"module":"client-settings","page":"Client-Settings.md","overview":"A reusable, attribute-driven framework that builds the plugin's in-game configuration dialog entirely from the Config class. SettingsGenerator reflects over Config at startup, discovers IElement attributes on properties and methods, constructs typed GUI controls for each, and passes them to a Layout that arranges them inside a SettingsScreen. Binding two-way-connects each control's change event directly to Config.Current, and ConfigStorage persists the config as XML when the dialog is closed. The framework is a plugin-template piece, not specific to Multigrid Projector.","files":[{"path":"ClientPlugin/Settings/SettingsGenerator.cs","summary":"Reflects Config; builds AttributeInfo list; orchestrates element creation, layout, and dialog lifecycle"},{"path":"ClientPlugin/Settings/SettingsScreen.cs","summary":"MyGuiScreenBase subclass that adds controls from the generator callback and saves config on removal"},{"path":"ClientPlugin/Settings/ConfigStorage.cs","summary":"XML serialise/deserialise of Config to %UserData%/Storage/<Plugin>.cfg"},{"path":"ClientPlugin/Settings/Elements/Element.cs","summary":"IElement interface: GetControls and SupportedTypes"},{"path":"ClientPlugin/Settings/Elements/Control.cs","summary":"Layout-metadata wrapper (FixedWidth, MinWidth, FillFactor, Offset, RightMargin) around a MyGuiControlBase"},{"path":"ClientPlugin/Settings/Elements/Checkbox.cs","summary":"[Checkbox] attribute for bool properties"},{"path":"ClientPlugin/Settings/Elements/Slider.cs","summary":"[Slider] attribute for float/int with range, step, manual-entry dialog"},{"path":"ClientPlugin/Settings/Elements/Dropdown.cs","summary":"[Dropdown] attribute for enum properties using MyGuiControlCombobox"},{"path":"ClientPlugin/Settings/Elements/Color.cs","summary":"[Color] attribute for VRageMath.Color with hex textbox and swatch"},{"path":"ClientPlugin/Settings/Elements/Keybind.cs","summary":"[Keybind] attribute for Binding values with rebind/unbind dialog and modifier checkboxes"},{"path":"ClientPlugin/Settings/Elements/Button.cs","summary":"[Button] attribute for void Config methods"},{"path":"ClientPlugin/Settings/Elements/Textbox.cs","summary":"[Textbox] attribute for string properties"},{"path":"ClientPlugin/Settings/Elements/Separator.cs","summary":"[Separator] attribute for visual section dividers with optional orange caption"},{"path":"ClientPlugin/Settings/Layouts/Layout.cs","summary":"Abstract base for layout strategies: SettingsPanelSize, RecreateControls, LayoutControls"},{"path":"ClientPlugin/Settings/Layouts/Simple.cs","summary":"Scrollable single-column layout with proportional fill-factor width distribution"},{"path":"ClientPlugin/Settings/Layouts/None.cs","summary":"Pass-through layout placing all controls at Vector2.Zero; default before SetLayout is called"},{"path":"ClientPlugin/Settings/Tools/Tools.cs","summary":"Static helpers: PascalCase-to-label conversion, hex colour parse and format extensions"},{"path":"ClientPlugin/Settings/Tools/Binding.cs","summary":"Keyboard binding value type: MyKeys + Ctrl/Alt/Shift modifiers, IsPressed/HasPressed detection"}],"key_types":["SettingsGenerator — reflects Config, drives the full dialog build pipeline","IElement — interface all GUI-element attributes implement","Control — layout metadata wrapper around a MyGuiControlBase used by Layout","Binding — key + modifier struct serialised in Config and edited by KeybindAttribute","ConfigStorage — XML persist/load for Config to %UserData%/Storage/<Plugin>.cfg","Simple — the standard scrollable row layout used in production"],"depends_on":["client-core"],"used_by":["client-core"],"cross_refs":["Docs/Reference/Client-Plugin.md","Docs/Reference/Configuration.md"],"notes":"All element attributes live in ClientPlugin.Settings.Elements and are discovered purely by reflection at startup. The config file path is %UserData%/Storage/<Plugin.Name>.cfg using MyFileSystem.UserDataPath. SupportedTypes on each IElement is validated at startup and throws if a property type is incompatible. Separator applies to object-typed dummy properties and is the only element that ignores getter/setter entirely."}
```
