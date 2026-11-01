#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec swipl -q -s "$SCRIPT_DIR/../tests/doc_tables.pl" -g main -t halt -- "$1"
