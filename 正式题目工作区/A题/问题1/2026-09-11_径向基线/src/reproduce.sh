#!/bin/bash
# Reproduce in a NEW directory. Never overwrite the retained evidence directory.
set -euo pipefail
Q1_SOURCE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
if [ "$#" -ne 1 ]; then echo 'Usage: bash src/reproduce.sh /absolute/path/to/NEW-run-directory' >&2; exit 2; fi
Q1_DEST_DIR="$1"
if [ -e "$Q1_DEST_DIR" ]; then echo 'Destination already exists; choose a new directory.' >&2; exit 2; fi
Q1_PYTHON="${Q1_PYTHON:-/Users/hanqimo/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3}"
Q1_NODE="${Q1_NODE:-/Users/hanqimo/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node}"
Q1_NODE_MODULES="${Q1_NODE_MODULES:-/Users/hanqimo/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules}"
mkdir -p "$Q1_DEST_DIR"
Q1_DEST_DIR="$(cd "$Q1_DEST_DIR" && pwd)"
cp -R "$Q1_SOURCE_DIR/inputs" "$Q1_SOURCE_DIR/model" "$Q1_SOURCE_DIR/src" "$Q1_DEST_DIR/"
mkdir -p "$Q1_DEST_DIR/runs" "$Q1_DEST_DIR/verification" "$Q1_DEST_DIR/results"
Q1_BUILD_DIR="$(mktemp -d /private/tmp/a-q1-reproduce.XXXXXX)"
trap 'rm -rf "$Q1_BUILD_DIR"' EXIT
clang++ -O3 -std=c++17 "$Q1_DEST_DIR/src/solver.cpp" -o "$Q1_BUILD_DIR/solver"
"$Q1_PYTHON" "$Q1_DEST_DIR/src/replay_cases.py" "$Q1_BUILD_DIR/solver"
"$Q1_PYTHON" "$Q1_DEST_DIR/src/check_inputs.py"
"$Q1_PYTHON" "$Q1_DEST_DIR/src/verify.py" > "$Q1_DEST_DIR/verification/checks_console.log"
"$Q1_PYTHON" "$Q1_DEST_DIR/src/prepare_results.py" > "$Q1_DEST_DIR/verification/selection_console.log"
cp "$Q1_DEST_DIR/src/build_workbook.mjs" "$Q1_BUILD_DIR/"
ln -s "$Q1_NODE_MODULES" "$Q1_BUILD_DIR/node_modules"
Q1_ROOT="$Q1_DEST_DIR" "$Q1_NODE" "$Q1_BUILD_DIR/build_workbook.mjs" > "$Q1_DEST_DIR/verification/workbook_build.log" 2>&1
"$Q1_PYTHON" "$Q1_DEST_DIR/src/check_workbook.py"
"$Q1_PYTHON" "$Q1_DEST_DIR/src/write_report.py"
echo "Reproduction saved to $Q1_DEST_DIR"
