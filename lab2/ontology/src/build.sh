#!/usr/bin/env bash
# Builds ontology/videocard.owl: ontology_data.py -> build_ontology.py (FSS)
# -> tests/harness ConvertFss (RDF/XML, UTF-8). Deterministic; safe to rerun.
#
#   build.sh                         final ontology -> ontology/videocard.owl
#   build.sh --mutate T06 [out.owl]  one negative-test copy (default out: tests/negative/<name>.owl)
#   build.sh --negatives             all four copies T06..T09 -> tests/negative/
set -euo pipefail
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$(dirname "$SRC")")"
BUILD="$SRC/build"   # intermediate, git-ignored

negative_name() {
  case "$1" in
    T06) echo "T06_active_and_passive.owl" ;;
    T07) echo "T07_two_gpus.owl" ;;
    T08) echo "T08_negative_volume.owl" ;;
    T09) echo "T09_missing_hasMemory.owl" ;;
    *) echo "unknown mutation: $1 (expected T06|T07|T08|T09)" >&2; return 2 ;;
  esac
}

mutate() {  # mutate <id> [out.owl]
  local id="$1" out="${2:-}"
  [ -n "$out" ] || out="$ROOT/tests/negative/$(negative_name "$id")"
  python3 "$SRC/build_ontology.py" --mutate "$id" "$BUILD/$id.fss"
  bash "$ROOT/tests/harness/convert.sh" "$BUILD/$id.fss" "$out"
}

case "${1:-}" in
  "")
    python3 "$SRC/build_ontology.py" "$BUILD/videocard.fss"
    bash "$ROOT/tests/harness/convert.sh" "$BUILD/videocard.fss" "$ROOT/ontology/videocard.owl"
    ;;
  --mutate)
    [ $# -ge 2 ] || { echo "usage: $0 --mutate T06|T07|T08|T09 [out.owl]" >&2; exit 2; }
    mutate "$2" "${3:-}"
    ;;
  --negatives)
    for id in T06 T07 T08 T09; do mutate "$id"; done
    ;;
  *)
    echo "usage: $0 [--mutate T06|T07|T08|T09 [out.owl] | --negatives]" >&2
    exit 2
    ;;
esac
