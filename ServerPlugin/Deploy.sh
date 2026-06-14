#!/usr/bin/env sh
set -eu

# Linux/macOS equivalent of Deploy.bat for the server plugin.
# Copies the built plugin DLL into the Magnetar "Local" plugin folder, routed by
# target framework:
#   net4x  (.NET Framework) -> Magnetar/Legacy/Local
#   others (.NET 5+)        -> Magnetar/Interim/Local when the Interim edition exists
# Usage: Deploy.sh <NAME> <SOURCE> [TFM]
#   NAME   - plugin DLL file name (e.g. MyPlugin.dll)
#   SOURCE - directory containing the built DLL
#   TFM    - target framework moniker (e.g. net48, net10.0)

if [ "$#" -lt 2 ]; then
    echo "ERROR: Missing required parameters" >&2
    exit 1
fi

NAME=$1
SOURCE=${2%/}
TFM=${3:-}

SRCFILE="$SOURCE/$NAME"
if [ ! -f "$SRCFILE" ]; then
    echo "ERROR: Source not found: $SRCFILE" >&2
    exit 1
fi

MAGNETAR="$HOME/.config/Magnetar"

# Determine the destination Local plugin folder.
# Priority: explicit override -> per-framework routing.
if [ -n "${MAGNETAR_LOCAL_DIR:-}" ]; then
    PLUGIN_DIR="$MAGNETAR_LOCAL_DIR"
    mkdir -p "$PLUGIN_DIR"
else
    case "$TFM" in
        net4*)
            PLUGIN_DIR="$MAGNETAR/Legacy/Local"
            if [ ! -d "$PLUGIN_DIR" ]; then
                echo "Missing Local plugin folder: $PLUGIN_DIR" >&2
                echo "Set MAGNETAR_LOCAL_DIR to your Magnetar Local folder if it is elsewhere." >&2
                exit 2
            fi
            ;;
        *)
            if [ -d "$MAGNETAR/Interim" ]; then
                PLUGIN_DIR="$MAGNETAR/Interim/Local"
                mkdir -p "$PLUGIN_DIR"
            elif [ -d "$MAGNETAR/Local" ]; then
                PLUGIN_DIR="$MAGNETAR/Local"
            else
                echo "Magnetar Interim not installed, skipping $TFM deploy: $MAGNETAR/Interim" >&2
                echo "Set MAGNETAR_LOCAL_DIR to your Magnetar Local folder if it is elsewhere." >&2
                exit 0
            fi
            ;;
    esac
fi

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
