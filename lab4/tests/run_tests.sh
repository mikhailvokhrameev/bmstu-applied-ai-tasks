#!/usr/bin/env bash
# Isolated T04-T10 engine checks: --ontology FILE --evidence-dir NEW_DIRECTORY.
# Set PYTHON_BIN to a Python >=3.10 executable when python3 is older.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/../DELIVERY_MANIFEST.json" ]; then
  PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
else
  PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
fi
cd "$PROJECT_ROOT"
exec "${PYTHON_BIN:-python3}" -m lab4.optimizer.release "$@"
