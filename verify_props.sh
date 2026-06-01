#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

for path in "$@"; do
    if [ ! -e "$path" ]; then
        printf 'ERROR: Invalid path "%s" in "%s/Directory.Build.props"\n' "$path" "$SCRIPT_DIR" >&2
    fi
done

exit 0
