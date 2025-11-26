# Testing during Development
     
After forking the pyparsing repo, and cloning your fork locally, install the libraries needed to run tests

    pip install -Ur tests/requirements.txt
    pre-commit install
         
Run the simple unit tests to ensure your environment is setup 
     
    python tests/test_simple_unit.py

Use `tox` to run the full test suite on all supported Python versions

    # run a specific test environment
    tox -e py312-unit
    tox -e py312-doctest

    # run all test environments
    tox

    # run all test environments in parallel
    tox -p

To run `mypy` standalone

    tox -e mypy-check

# Performance benchmarks

This directory includes a performance benchmark suite to compare behavior across
different versions of Python and pyparsing. You can run it directly, or via helper
scripts that iterate a matrix of interpreter and package versions and append results
to a consolidated CSV file.

## Run the benchmark directly

- From the repository root, run:

  ```bash
  python tests/perf_pyparsing.py
  ```

  This prints a summary table and a CSV export of per‑benchmark timings to stdout.

- To append the CSV rows to a consolidated file, either:

  - Pass the output path on the command line:

    ```bash
    python tests/perf_pyparsing.py --append-csv perf_pyparsing.csv
    ```

  - Or set an environment variable and run without flags:

    ```powershell
    # Windows (CMD/PowerShell)
    set PERF_PYPARSING_CSV=perf_pyparsing.csv
    python tests/perf_pyparsing.py
    ```

    ```bash
    # Linux/macOS (bash/zsh)
    export PERF_PYPARSING_CSV=perf_pyparsing.csv
    python tests/perf_pyparsing.py
    ```

  If the destination file already exists, the benchmark will append new rows and avoid
  duplicating the CSV header line.

## Matrix runners (Windows and Ubuntu)

Two scripts are provided to run the benchmark suite across a matrix of Python and
pyparsing versions, and to collect all results into `perf_pyparsing.csv` in the repo root.

- Windows (CMD or PowerShell): `run_perf_all_tags.bat`

  - Requirements: Windows, the `py` launcher on PATH, and internet access.
  - What it does:
    - Shows a summary of planned Python versions and pyparsing versions to test, and the
      output CSV path.
    - Creates a fresh virtual environment per Python version (named `.venv-perf-<ver>`).
    - Installs required tools in each venv (`pip`, `setuptools`, `wheel`, and runtime
      deps `littletable` and `rich`).
    - Copies `tests\perf_pyparsing.py` into a temp folder inside the venv so the run uses the
      installed pyparsing package, not the checkout.
    - Iterates through pyparsing tags `3.1.1` through `3.3.0a2`, installing each and
      appending results to the consolidated CSV.
    - Prints a cumulative elapsed timer (M:SS) after each Python version block, and a total
      elapsed time at the end.
  - How to run:

    ```powershell
    cd <repo-root>  # e.g., D:\dev\pyparsing\gh\pyparsing
    .\run_perf_all_tags.bat
    ```

- Ubuntu/Linux (bash): `run_perf_all_tags.sh`

  - Requirements: bash, one or more Python interpreters available as `python3.9`,
    `python3.10`, …; internet access.
  - What it does: mirrors the Windows script behavior (venv per Python, dependency installs,
    iterate pyparsing versions, append to CSV, cumulative/total elapsed timers).
  - How to run:

    ```bash
    cd <repo-root>
    chmod +x ./run_perf_all_tags.sh
    ./run_perf_all_tags.sh
    ```

## Notes

- The consolidated output file is `perf_pyparsing.csv` at the repo root. It contains
  columns for date, `python_version`, `pyparsing_version`, benchmark name, mean time,
  standard deviation, and number of runs.
- Re-running either script will recreate the venvs as needed and regenerate/append to the
  consolidated CSV. Some older pyparsing versions may not install on the newest Python
  versions; these entries will be skipped with a message.
