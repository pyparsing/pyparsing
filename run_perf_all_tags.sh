#!/usr/bin/env bash

# Run tests/perf_pyparsing.py against multiple pyparsing versions and consolidate
# results into perf_pyparsing.csv on Ubuntu (bash).
#
# Requirements:
#   - Ubuntu/Linux with bash
#   - One or more Python interpreters installed (python3.9, python3.10, ...)
#   - Internet access to install specific pyparsing versions from PyPI
#
# Notes:
#   - This script does NOT checkout git tags. It installs each requested version
#     into an isolated venv and runs the current repo's tests/perf_pyparsing.py,
#     which will import pyparsing from the installed package (not this checkout).
#   - The perf script supports appending CSV rows using the --append-csv option.

set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$SCRIPT_DIR"
CSV="$REPO_DIR/perf_pyparsing.csv"

# pyparsing versions to test (3.1.1 through 3.3.0)
VERSIONS=(
  3.1.1
  3.1.2
  3.1.3
  3.1.4
  3.2.0
  3.2.1
  3.2.3
  3.2.5
  3.3.0
)

# Python versions to use
PY_VERSIONS=(3.9 3.10 3.11 3.12 3.13 3.14)

# ---- Summary of planned run ----
echo
echo "=============================================="
echo "=== pyparsing perf matrix: planned targets ==="
echo "=============================================="
echo -n "Python versions:   "
printf '%s ' "${PY_VERSIONS[@]}"
echo
echo -n "pyparsing versions: "
printf '%s ' "${VERSIONS[@]}"
echo
echo "Output CSV:        $CSV"
echo "=============================================="
echo

# Remove any previous consolidated CSV (do this once for the full matrix run)
rm -f "$CSV"

# Start cumulative timer
START_TS=$(date +%s)

find_python_for_version() {
  local pv="$1"  # e.g., 3.12
  # Prefer python<ver> on PATH (Ubuntu convention)
  if command -v "python$pv" >/dev/null 2>&1; then
    echo "python$pv"
    return 0
  fi
  # Fallback: try py launcher if present (less common on Linux)
  if command -v py >/dev/null 2>&1; then
    if py -"$pv" -c 'import sys; print(sys.version)' >/dev/null 2>&1; then
      echo "py -$pv"
      return 0
    fi
  fi
  return 1
}

for pv in "${PY_VERSIONS[@]}"; do
  echo
  echo "*******************************"
  echo "*** Python $pv matrix entry ***"
  echo "*******************************"

  if ! interp_cmd=$(find_python_for_version "$pv"); then
    echo "Python $pv not found on PATH (nor via 'py'), skipping this interpreter."
    continue
  fi

  VENV_DIR="$REPO_DIR/.venv-perf-$pv"
  if [ -d "$VENV_DIR" ]; then
    rm -rf "$VENV_DIR"
  fi

  echo "Creating virtual environment for Python $pv..."
  if [[ "$interp_cmd" == py* ]]; then
    # Using the Windows-style py launcher (rare on Ubuntu), invoke as: py -3.12 -m venv
    eval "$interp_cmd -m venv \"$VENV_DIR\"" || { echo "Failed to create venv for Python $pv, skipping..."; continue; }
  else
    "$interp_cmd" -m venv "$VENV_DIR" || { echo "Failed to create venv for Python $pv, skipping..."; continue; }
  fi

  PYTHON="$VENV_DIR/bin/python"
  PIP="$VENV_DIR/bin/pip"
  VENV_TMP="$VENV_DIR/_tmp"

  echo "Upgrading pip and installing dependencies for Python $pv..."
  if ! "$PYTHON" -m pip install --upgrade pip setuptools wheel >/dev/null; then
    echo "Failed to upgrade pip for Python $pv, skipping this interpreter."
    continue
  fi
  if ! "$PIP" install littletable >/dev/null; then
    echo "Failed to install littletable for Python $pv, skipping this interpreter."
    continue
  fi
  if ! "$PIP" install rich >/dev/null; then
    echo "Failed to install rich for Python $pv, skipping this interpreter."
    continue
  fi

  # Prepare temp location for running the perf script outside the repo
  rm -rf "$VENV_TMP"
  mkdir -p "$VENV_TMP"
  cp -f "$REPO_DIR/tests/perf_pyparsing.py" "$VENV_TMP/perf_pyparsing.py"

  for v in "${VERSIONS[@]}"; do
    echo
    echo "=== Running perf for Python $pv, pyparsing $v ==="
    "$PIP" uninstall -y pyparsing >/dev/null 2>&1 || true
    if ! "$PIP" install "pyparsing==$v"; then
      echo "Failed to install pyparsing $v on Python $pv, skipping..."
      continue
    fi

    export PYTHONUTF8=1
    if ! "$PYTHON" "$VENV_TMP/perf_pyparsing.py" --append-csv "$CSV"; then
      echo "perf run failed for pyparsing $v on Python $pv, continuing..."
      continue
    fi
  done

  # ---- Cumulative elapsed time after this matrix entry ----
  NOW_TS=$(date +%s)
  ELAPSED=$((NOW_TS - START_TS))
  ELAPSED_MIN=$((ELAPSED / 60))
  ELAPSED_SEC=$((ELAPSED % 60))
  printf 'Cumulative elapsed: %d:%02d\n' "$ELAPSED_MIN" "$ELAPSED_SEC"
done

echo
echo "Consolidated results written to:"
echo "  $CSV"

# ---- Total elapsed time for full run ----
END_TS=$(date +%s)
TOTAL=$((END_TS - START_TS))
T_MIN=$((TOTAL / 60))
T_SEC=$((TOTAL % 60))
printf 'Total elapsed: %d:%02d\n' "$T_MIN" "$T_SEC"

exit 0
