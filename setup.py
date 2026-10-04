#!/usr/bin/env python3
"""
Replaces project GUIDs and renames the solution
Requires Python 3.12 or newer.
"""

import os
import re
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path
import sys
from typing import Iterator, Tuple

if sys.platform == "win32":
    import winreg

DRY_RUN = False

TEMPLATE_NAME = 'PluginTemplate'

PT_PROJECT_NAME = r"^([A-Z][a-z_0-9]+)+$"
RX_PROJECT_NAME = re.compile(PT_PROJECT_NAME)

PROJECT_NAMES = (
    "ClientPlugin",
    "ServerPlugin",
    "Shared",
)

# Steam app ids of the games providing the build references
GAME_APP_ID = "244850"  # Space Engineers (Bin64)
DEDICATED_APP_ID = "298740"  # Space Engineers Dedicated Server (DedicatedServer64)

# Local folder path overrides imported by Directory.Build.props, not committed
USER_PROPS = "Directory.Build.props.user"

USER_PROPS_TEMPLATE = """\
<Project>
  <PropertyGroup>
    <!-- Folder containing SpaceEngineers.exe (empty = auto-detect from Steam) -->
    <Bin64>{bin64}</Bin64>

    <!-- Folder containing SpaceEngineersDedicated.exe (empty = auto-detect from Steam) -->
    <Dedicated64>{dedicated64}</Dedicated64>

    <!-- Pulsar folder to deploy the client plugin into after each build (empty = no deployment),
         for example $(APPDATA)\\Pulsar on Windows or $(HOME)/.config/Pulsar on Linux -->
    <Pulsar></Pulsar>

    <!-- Magnetar installation folder, holds the launchers (empty = auto-detect) -->
    <Magnetar></Magnetar>

    <!-- Magnetar config folder to deploy the server plugin into after each build,
         usually the Magnetar subfolder of the folder above (empty = no deployment) -->
    <MagnetarData></MagnetarData>
  </PropertyGroup>
</Project>
"""


def _generate_guid() -> str:
    return str(uuid.uuid4())


def _replace_text_in_file(replacements: dict[str, str], path: str) -> None:
    is_project = (
        path.endswith(".sln") or path.endswith(".csproj") or path.endswith(".shproj")
    )
    encoding = "utf-8-sig" if is_project else "utf-8"

    with open(path, "rt", encoding=encoding) as f:
        text = f.read()

    original = text

    for k, v in replacements.items():
        text = text.replace(k, v)

    if DRY_RUN or text == original:
        return

    with open(path, "wt", encoding=encoding) as f:
        f.write(text)


def _input_plugin_name() -> str:
    while True:
        plugin_name = input("Name of the plugin (in CapitalizedWords format): ")
        if not plugin_name:
            break

        if RX_PROJECT_NAME.match(plugin_name):
            break

        print("Invalid plugin name, it must match regexp: " + PT_PROJECT_NAME)

    return plugin_name


def _input_question(prompt: str, default: bool | None = None) -> bool:
    while True:
        response = input(prompt).lower()

        if default is not None and len(response) == 0:
            return default

        if response in ["n", "no"]:
            return False

        if response in ["y", "yes"]:
            return True

        print("Unknown response (Y/N)")


def _rename_project(name: str) -> None:
    replacements = {
        TEMPLATE_NAME: name,
        "A061FC6C-713E-42CD-B413-151AC8A5074C": _generate_guid().upper(),
        "FFB7FCA3-B168-43F4-8DBF-6247C0D331C8": _generate_guid().upper(),
        "C5784FE0-CF0A-4870-9DEF-7BEA8B64C01A": _generate_guid().upper(),
    }

    def iter_paths() -> Iterator[Tuple[str, str]]:
        print("Solution:")
        for filename in (
            f'{TEMPLATE_NAME}.sln',
            f'{TEMPLATE_NAME}Client.xml',
            f'{TEMPLATE_NAME}Server.xml',
        ):
            if os.path.exists(filename):
                yield filename, filename

        for project_name in PROJECT_NAMES:
            print()
            print(f"{project_name}:")

            for dirpath, _, filenames in os.walk(project_name):
                parts = set(Path(dirpath).parts)
                if "obj" in parts or "bin" in parts:
                    continue

                for filename in filenames:
                    ext = filename.rsplit(".")[-1]
                    if ext in ("xml", "xaml", "cs", "sln", "csproj", "shproj"):
                        path = os.path.join(dirpath, filename)
                        yield filename, path

    rename_files: list[tuple[str, str]] = []
    for filename, path in iter_paths():
        print(f"  {filename}")
        _replace_text_in_file(replacements, path)
        if TEMPLATE_NAME in filename:
            rename_files.append((filename, path))

    if not DRY_RUN:
        for filename, path in rename_files:
            dir_path = os.path.dirname(path)
            dst_name = filename.replace(TEMPLATE_NAME, name)
            dst_path = os.path.join(dir_path, dst_name)
            os.rename(path, dst_path)


def _get_windows_steam_path() -> str | None:
    reg = winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE)
    key = winreg.OpenKey(reg, r"SOFTWARE\WOW6432Node\Valve\Steam")
    (path, _) = winreg.QueryValueEx(key, "InstallPath")
    return path


def _get_linux_steam_path() -> str | None:
    candidates = []

    for env_name in ("STEAM_DIR", "STEAM_HOME"):
        env_path = os.environ.get(env_name)
        if env_path:
            candidates.append(Path(env_path).expanduser())

    home = Path.home()
    candidates.extend(
        [
            home / ".steam" / "steam",
            home / ".local" / "share" / "Steam",
            home
            / ".var"
            / "app"
            / "com.valvesoftware.Steam"
            / ".local"
            / "share"
            / "Steam",
        ]
    )

    for path in candidates:
        if (path / "steamapps" / "libraryfolders.vdf").is_file():
            return str(path)

    for path in candidates:
        if path.exists():
            return str(path)

    return None


def _get_steam_path() -> str | None:
    if sys.platform == "win32":
        return _get_windows_steam_path()

    return _get_linux_steam_path()


def _parse_valve_key_values(vdf: str) -> dict[str, object]:
    tokens = re.findall(r'"((?:\\.|[^"\\])*)"|([{}])', vdf)
    index = 0

    def decode_value(value: str) -> str:
        return value.replace(r"\\", "\\").replace(r"\"", '"')

    def read_token() -> str:
        nonlocal index
        if index >= len(tokens):
            raise ValueError("Unexpected end of Valve VDF data")

        quoted, brace = tokens[index]
        index += 1
        return decode_value(quoted) if quoted else brace

    def read_object() -> dict[str, object]:
        result: dict[str, object] = {}

        while index < len(tokens):
            key = read_token()
            if key == "}":
                return result

            value = read_token()
            if value == "{":
                result[key] = read_object()
            elif value == "}":
                raise ValueError("Unexpected closing brace in Valve VDF data")
            else:
                result[key] = value

        return result

    return read_object()


def _get_install_locations(vdf_path: str, ids: list[str]) -> dict[str, str | None]:
    with open(vdf_path, "r", encoding="UTF-8") as file:
        libraryfolders = _parse_valve_key_values(file.read())["libraryfolders"]

    game_drives: dict[str, str | None] = {game_id: None for game_id in ids}
    assert isinstance(libraryfolders, dict)

    for folder in libraryfolders.values():
        assert isinstance(folder, dict)
        assert isinstance(folder["apps"], dict)
        assert isinstance(folder["path"], str)

        for game in ids:
            if game in folder["apps"]:
                game_drives[game] = folder["path"]

    game_install: dict[str, str | None] = {}
    for game_id, drive in game_drives.items():

        if drive is None:
            game_install[game_id] = None

        else:
            path = Path(drive) / "steamapps" / f"appmanifest_{game_id}.acf"
            with open(path, "r", encoding="UTF-8") as file:
                manifest = _parse_valve_key_values(file.read())

            app_state = manifest["AppState"]
            assert isinstance(app_state, dict)
            install_dir = app_state["installdir"]
            assert isinstance(install_dir, str)

            game_install[game_id] = str(
                Path(drive) / "steamapps" / "common" / install_dir
            )

    return game_install


def _set_prop(group: ET.Element, name: str, value: str) -> None:
    """Set an MSBuild property in the group, adding the element if missing."""
    element = group.find(name)

    if element is None:
        element = ET.SubElement(group, name)
        element.tail = "\n    "

    element.text = value


def _update_props(
    game_dir: str | None = None,
    server_dir: str | None = None,
) -> None:
    """Write the detected paths into the git-ignored local overrides file."""
    if not game_dir and not server_dir:
        return

    bin64_dir = str(Path(game_dir) / "Bin64") if game_dir else ""
    dedicated64_dir = (
        str(Path(server_dir) / "DedicatedServer64") if server_dir else ""
    )

    if not os.path.isfile(USER_PROPS):
        with open(USER_PROPS, "w", encoding="UTF-8", newline="\n") as file:
            file.write(
                USER_PROPS_TEMPLATE.format(
                    bin64=bin64_dir, dedicated64=dedicated64_dir
                )
            )
        print(f"Created {USER_PROPS}")
        return

    # Keep any other overrides the developer may have added
    parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))
    tree = ET.parse(USER_PROPS, parser)
    root = tree.getroot()

    group = root.find("PropertyGroup")
    if group is None:
        group = ET.SubElement(root, "PropertyGroup")

    if bin64_dir:
        _set_prop(group, "Bin64", bin64_dir)

    if dedicated64_dir:
        _set_prop(group, "Dedicated64", dedicated64_dir)

    tree.write(USER_PROPS)
    print(f"Updated {USER_PROPS}")


def main() -> None:
    """Run the setup."""

    if os.path.isfile(f"{TEMPLATE_NAME}.sln"):
        plugin_name = _input_plugin_name()

        if plugin_name:
            _rename_project(plugin_name)
        else:
            print("Skipping project rename")

    if _input_question("Auto-detect reference locations? (Y/N) [Y]: ", True):
        steam_path = _get_steam_path()
        if steam_path is None:
            print("Could not find Steam install location.")
            input("Done. (Press any key to exit)")
            return

        vdf_path = str(Path(steam_path) / "steamapps" / "libraryfolders.vdf")
        locations = _get_install_locations(vdf_path, [GAME_APP_ID, DEDICATED_APP_ID])

        if locations[GAME_APP_ID] is not None:
            print(f"Found Space Engineers under {locations[GAME_APP_ID]}")
        else:
            print("Could not find Space Engineers install location.")

        if locations[DEDICATED_APP_ID] is not None:
            print(f"Found Dedicated Server under {locations[DEDICATED_APP_ID]}")
        else:
            print("Could not find Dedicated Server install location.")

        _update_props(locations[GAME_APP_ID], locations[DEDICATED_APP_ID])
    else:
        print(f"Please add the paths manually to '{USER_PROPS}'")

    input("Done. (Press any key to exit)")


if __name__ == "__main__":
    main()
