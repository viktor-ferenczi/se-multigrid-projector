#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

for project in ClientPlugin ServerPlugin IngameApiTest ModApiTest; do
    rm -rf "$SCRIPT_DIR/$project/bin" "$SCRIPT_DIR/$project/obj"
done
