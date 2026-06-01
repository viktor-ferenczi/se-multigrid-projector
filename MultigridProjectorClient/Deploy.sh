#!/usr/bin/env sh
set -eu

if [ "$#" -lt 2 ]; then
    echo "ERROR: Missing required parameters" >&2
    exit 1
fi

NAME=$1
SOURCE=${2%/}

DLL_PATH="$SOURCE/$NAME"
if ! [ -f "$DLL_PATH" ]; then
    echo "ERROR: Source not found: $DLL_PATH" >&2
    exit 1
fi

PLUGIN_DIR="$HOME/.config/Pulsar/Local"
if [ -n "${PULSAR_LOCAL_DIR:-}" ]; then
    PLUGIN_DIR="$PULSAR_LOCAL_DIR"
    return
fi

if [ ! -d "$PLUGIN_DIR" ]; then
    echo "Missing Local plugin folder: $PLUGIN_DIR" >&2
    echo "Set PULSAR_LOCAL_DIR to your Pulsar Legacy/Interim Local folder if it is elsewhere." >&2
    exit 2
fi

echo "Copying \"$DLL_PATH\" to \"$PLUGIN_DIR/\""
cp -f "$DLL_PATH" "$PLUGIN_DIR/"
