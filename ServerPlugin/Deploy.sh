#!/usr/bin/env sh
set -eu

# Linux/macOS equivalent of Deploy.bat for the server plugin.
# Copies the built plugin DLL into the Magnetar "Local" plugin folder.
# On Linux Magnetar stores its data under ~/.config/Magnetar (no "Legacy" subfolder).
# Usage: Deploy.sh <NAME> <SOURCE>
#   NAME   - plugin DLL file name (e.g. MyPlugin.dll)
#   SOURCE - directory containing the built DLL

if [ "$#" -lt 2 ]; then
    echo "ERROR: Missing required parameters" >&2
    exit 1
fi

NAME=$1
SOURCE=$2

# Resolve the source file: prefer "SOURCE/NAME", fall back to SOURCE itself.
SRCFILE="$SOURCE/$NAME"
if [ ! -f "$SRCFILE" ]; then
    if [ -f "$SOURCE" ]; then
        SRCFILE=$SOURCE
    else
        echo "ERROR: Source not found: $SOURCE or $SOURCE/$NAME" >&2
        exit 1
    fi
fi

MAGNETAR_DIR="$HOME/.config/Magnetar"
if [ ! -d "$MAGNETAR_DIR" ]; then
    echo "Missing Magnetar folder: $MAGNETAR_DIR" >&2
    echo "Magnetar not installed?" >&2
    exit 2
fi

PLUGIN_DIR="$MAGNETAR_DIR/Local"
mkdir -p "$PLUGIN_DIR"

# Copy the plugin, retrying in case the file is temporarily locked by a running server.
echo "Copying \"$SRCFILE\" to \"$PLUGIN_DIR/\""
i=1
while [ "$i" -le 10 ]; do
    if cp -f "$SRCFILE" "$PLUGIN_DIR/"; then
        exit 0
    fi
    sleep 1
    i=$((i + 1))
done

echo "ERROR: Could not copy \"$NAME\"." >&2
exit 1
