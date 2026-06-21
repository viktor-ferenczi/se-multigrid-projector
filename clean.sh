#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

rm -rf "$SCRIPT_DIR/ClientPlugin/bin" "$SCRIPT_DIR/ClientPlugin/obj"
rm -rf "$SCRIPT_DIR/ServerPlugin/bin" "$SCRIPT_DIR/ServerPlugin/obj"
