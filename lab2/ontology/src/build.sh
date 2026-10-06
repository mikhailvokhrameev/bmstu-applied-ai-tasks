#!/usr/bin/env bash
# Builds ontology/videocard.owl: ontology_data.py -> build_ontology.py (FSS)
# -> tests/harness ConvertFss (RDF/XML, UTF-8). Deterministic; safe to rerun.
set -euo pipefail
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$(dirname "$SRC")")"
FSS="$SRC/build/videocard.fss"   # intermediate, git-ignored

python3 "$SRC/build_ontology.py" "$FSS"
bash "$ROOT/tests/harness/convert.sh" "$FSS" "$ROOT/ontology/videocard.owl"
