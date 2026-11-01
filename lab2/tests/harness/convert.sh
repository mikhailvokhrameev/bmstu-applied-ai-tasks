#!/usr/bin/env bash
# Converts an OWL 2 Functional Syntax file to RDF/XML via the harness' ConvertFss.
# Reuses fetch_libs.sh and the same classpath/compile steps as run_tests.sh.
# Usage: tests/harness/convert.sh input.fss output.owl
set -euo pipefail
HARNESS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ $# -eq 2 ] || { echo "usage: $0 input.fss output.owl" >&2; exit 2; }
IN="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
mkdir -p "$(dirname "$2")"
OUT="$(cd "$(dirname "$2")" && pwd)/$(basename "$2")"

bash "$HARNESS/fetch_libs.sh" >/dev/null
mkdir -p "$HARNESS/out"
javac -encoding UTF-8 -cp "$HARNESS/lib/*" -d "$HARNESS/out" "$HARNESS"/src/*.java
java -Dfile.encoding=UTF-8 -Dslf4j.internal.verbosity=ERROR -cp "$HARNESS/out:$HARNESS/lib/*" ConvertFss "$IN" "$OUT"
