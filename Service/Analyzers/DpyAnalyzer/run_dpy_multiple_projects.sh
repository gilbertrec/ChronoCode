#!/usr/bin/env bash
set -euo pipefail

# ------------------------------------------------------------
# Run DPy on each specific leaf folder under an input root,
# mirroring the input structure into an output root.
#
# It specifically targets folders that contain source code files
# in the deep structure: {Agent}/{Repo}/{Status}/{SHA}/{Path}
#
# Supports parallel execution if GNU parallel is installed.
# ------------------------------------------------------------

usage() {
  cat <<EOF
Usage:
  $(basename "$0") -i <input_root> -o <output_root> [-d <dpy_cmd>] [-j <jobs>]

Options:
  -i <input_root>     Root folder containing the dataset (scanned recursively)
  -o <output_root>    Root folder where results will be written (mirrors input structure)
  -d <dpy_cmd>        DPy command/path (default: ./DPy)
  -j <jobs>           Number of parallel jobs (default: 4, requires GNU parallel)
                      If 'parallel' is not found, runs sequentially.
EOF
}

DPY_CMD="./DPy"
INPUT_ROOT=""
OUTPUT_ROOT=""
JOBS=4
SKIP_EXISTING=0

# --- parse args ---
while [[ $# -gt 0 ]]; do
  case "$1" in
    -i) INPUT_ROOT="${2:-}"; shift 2 ;;
    -o) OUTPUT_ROOT="${2:-}"; shift 2 ;;
    -d) DPY_CMD="${2:-}"; shift 2 ;;
    -j) JOBS="${2:-}"; shift 2 ;;
    --skip-existing) SKIP_EXISTING=1; shift 1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1"; usage; exit 1 ;;
  esac
done

if [[ -z "$INPUT_ROOT" || -z "$OUTPUT_ROOT" ]]; then
  usage
  exit 1
fi

if [[ ! -d "$INPUT_ROOT" ]]; then
  echo "ERROR: input root not found: $INPUT_ROOT" >&2
  exit 1
fi

# Resolve absolute paths
INPUT_ROOT_ABS="$(cd "$INPUT_ROOT" && pwd)"
mkdir -p "$OUTPUT_ROOT"
OUTPUT_ROOT_ABS="$(cd "$OUTPUT_ROOT" && pwd)"
DPY_CMD_ABS="$(readlink -f "$DPY_CMD" || echo "$DPY_CMD")"

echo "Input root : $INPUT_ROOT_ABS"
echo "Output root: $OUTPUT_ROOT_ABS"
echo "DPy cmd    : $DPY_CMD_ABS"
echo "Jobs       : $JOBS"
echo "Skip Existing: $SKIP_EXISTING"
echo

# ---------------------------------------------------------
# 1. Find all relevant directories to scan.
# We are looking for the leaf directories that contain files.
# Structure: .../{Status}/{SHA}/{...files...}
#
# A simple heuristic: Find directories that contain at least one .py file.
# BUT we want to run DPy on the *root* of the cloned content for that commit.
# The structure is: base/{Agent}/{Repo}/{Status}/{SHA}/...
# We want to run DPy on `base/{Agent}/{Repo}/{Status}/{SHA}`.
#
# So we look for directories that are strictly 4 levels deep relative to
# Agent/Repo/Status/SHA? No, Repo is owner$repo.
# Let's find the SHA directories.
# Structure: {Agent}/{Owner$Repo}/{Status}/{SHA}
# That is depth 4 from input root (assuming input root contains Agents).
# Example: 1. Collecting/.../before_change / Claude_Code / owner$repo / modified / SHA
# Input root should be "before_change" or "after_change" ideally, or the parent.
#
# Let's assume Input Root is "1. Collecting.../before_change".
# Then: Agent (d1) / Repo (d2) / Status (d3) / SHA (d4)
# We want to run on d4.
# ---------------------------------------------------------

echo "Scanning for SHA directories (depth 4)..."
TARGET_DIRS_FILE=$(mktemp)

# Find directories at depth 4 (Agent/Repo/Status/SHA)
find "$INPUT_ROOT_ABS" -mindepth 4 -maxdepth 4 -type d > "$TARGET_DIRS_FILE"

count=$(wc -l < "$TARGET_DIRS_FILE")
echo "Found $count directories to process."

export DPY_CMD_ABS INPUT_ROOT_ABS OUTPUT_ROOT_ABS SKIP_EXISTING

process_dir() {
    local dir="$1"
    # Compute relative path
    local rel="${dir#$INPUT_ROOT_ABS/}"
    local out_dir="$OUTPUT_ROOT_ABS/$rel"

    if [[ "$SKIP_EXISTING" -eq 1 ]]; then
        if ls "$out_dir"/*smell*.json >/dev/null 2>&1; then
             echo "[SKIP] $rel"
             return 0
        fi
    fi

    mkdir -p "$out_dir"

    # Only run if there are actual python files inside `dir` (recursive)
    if ! find "$dir" -name "*.py" -print -quit | grep -q .; then
        # echo "[SKIP] $rel (no py files)"
        return 0
    fi

    if "$DPY_CMD_ABS" analyze -i "$dir" -o "$out_dir" > "$out_dir/dpy_stdout.log" 2> "$out_dir/dpy_stderr.log"; then
        echo "[DONE] $rel"
    else
        echo "[FAIL] $rel"
    fi
}
export -f process_dir

# ---------------------------------------------------------
# 2. Execution
# ---------------------------------------------------------

if command -v parallel >/dev/null 2>&1; then
    echo "GNU parallel detected. Running with $JOBS jobs..."
    # strict blocking to avoid mixed output
    cat "$TARGET_DIRS_FILE" | parallel --bar -j "$JOBS" process_dir {}
else
    echo "GNU parallel NOT found. Running sequentially."
    while read -r d; do
        process_dir "$d"
    done < "$TARGET_DIRS_FILE"
fi

echo "All tasks completed."
rm "$TARGET_DIRS_FILE"
exit 0
