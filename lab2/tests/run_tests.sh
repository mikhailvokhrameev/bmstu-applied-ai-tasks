#!/usr/bin/env bash
# Single entry point for the test suite. Works from any cwd and from a fresh
# clone: fetches the pinned jars if missing, compiles the harness, runs the
# runner and tees the output to tests/results/run_tests.log.
#
# To add tests: drop a class implementing TestGroup into tests/harness/src/ and
# register it in Main.GROUPS. Nothing in this script needs to change.
set -euo pipefail

TESTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$TESTS_DIR")"
HARNESS="$TESTS_DIR/harness"
RESULTS="$TESTS_DIR/results"

bash "$HARNESS/fetch_libs.sh"

rm -rf "$HARNESS/out"
mkdir -p "$HARNESS/out" "$RESULTS"
javac -encoding UTF-8 -cp "$HARNESS/lib/*" -d "$HARNESS/out" "$HARNESS"/src/*.java

# pipefail: the runner's exit status survives the pipe to tee.
# slf4j.internal.verbosity: no SLF4J binding is shipped; silence its "no providers" notice.
java -Dfile.encoding=UTF-8 -Dslf4j.internal.verbosity=ERROR -cp "$HARNESS/out:$HARNESS/lib/*" Main "$ROOT_DIR" 2>&1 | tee "$RESULTS/run_tests.log"
