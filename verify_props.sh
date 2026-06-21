#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
STATUS=0

for path in "$@"; do
    if [ ! -e "$path" ]; then
        printf 'ERROR: Invalid path "%s" in "%s/Directory.Build.props" or "%s/Directory.Build.targets"\n' "$path" "$SCRIPT_DIR" "$SCRIPT_DIR" >&2
        STATUS=1
    fi
done

exit "$STATUS"
