@echo off
REM Run perf_pyparsing.py against multiple pyparsing versions and consolidate results into perf_pyparsing.csv
REM Requirements:
REM   - Windows
REM   - Python launcher `py` on PATH
REM   - Internet access to install specific pyparsing versions from PyPI
REM Notes:
REM   - This script does NOT checkout git tags. It installs each version into a temp venv
REM     and runs the current repo's tests\perf_pyparsing.py, which will use the installed version.
REM   - The perf script has been enhanced to support appending to a CSV via --append-csv.

setlocal enabledelayedexpansion

REM Location of this repo (directory of this .bat)
set REPO_DIR=%~dp0
pushd "%REPO_DIR%" >nul

REM Consolidated CSV output path
set CSV=%REPO_DIR%perf_pyparsing.csv

REM Remove any previous consolidated CSV (do this once for the full matrix run)
if exist "%CSV%" del /f /q "%CSV%"

REM List of pyparsing versions to test
set "VERSIONS=3.1.1 3.1.2 3.1.3 3.1.4 3.2.0 3.2.1 3.2.3 3.2.5 3.3.1 3.3.2"

REM Python versions to use
set "PY_VERSIONS=3.9 3.10 3.11 3.12 3.13 3.14"

REM ---- Summary of planned run ----
echo.
echo ==============================================
echo === pyparsing perf matrix: planned targets ===
echo ==============================================
echo Python versions:   %PY_VERSIONS%
echo pyparsing versions: %VERSIONS%
echo Output CSV:        %CSV%
echo ==============================================
echo.

REM Start cumulative timer (Unix epoch seconds)
for /f %%A in ('powershell -NoProfile -Command "[int]([DateTimeOffset]::UtcNow.ToUnixTimeSeconds())"') do set START_TS=%%A

for %%P in (%PY_VERSIONS%) do (
  echo.
  echo *******************************
  echo *** Python %%P matrix entry ***
  echo *******************************

  REM Check that the requested Python is available
  py -%%P -c "import sys; print(sys.version)" >nul 2>&1
  if errorlevel 1 (
    echo Python %%P not found by the 'py' launcher, skipping this interpreter.
  ) else (
    REM Create a fresh venv per Python version
    set "VENV_DIR=%REPO_DIR%.venv-perf-%%P"
    if exist "!VENV_DIR!" rmdir /S /Q "!VENV_DIR!"

    echo Creating virtual environment for Python %%P...
    py -%%P -m venv "!VENV_DIR!"
    if errorlevel 1 (
      echo Failed to create virtual environment for Python %%P, skipping...
    ) else (
      set "PYTHON=!VENV_DIR!\Scripts\python.exe"
      set "PIP=!VENV_DIR!\Scripts\pip.exe"
      set "VENV_TMP=!VENV_DIR!\_tmp"

      echo Upgrading pip and installing dependencies for Python %%P...
      "!PYTHON!" -m pip install --upgrade pip setuptools wheel >nul
      if errorlevel 1 (
        echo Failed to upgrade pip for Python %%P, skipping this interpreter.
      ) else (
        "!PIP!" install littletable >nul
        if errorlevel 1 (
          echo Failed to install littletable for Python %%P, skipping this interpreter.
        ) else (
          "!PIP!" install rich >nul
          if errorlevel 1 (
            echo Failed to install rich for Python %%P, skipping this interpreter.
          ) else (
            REM Prepare temp location for running the perf script outside the repo
            if exist "!VENV_TMP!" rmdir /S /Q "!VENV_TMP!"
            mkdir "!VENV_TMP!"
            copy /Y "%REPO_DIR%tests\perf_pyparsing.py" "!VENV_TMP!\perf_pyparsing.py" >nul

            for %%V in (%VERSIONS%) do (
              echo.
              echo === Running perf for Python %%P, pyparsing %%V ===
              "!PIP!" uninstall -y pyparsing >nul 2>&1
              "!PIP!" install "pyparsing==%%V"
              if errorlevel 1 (
                echo Failed to install pyparsing %%V on Python %%P, skipping...
              ) else (
                set PYTHONUTF8=1
                pushd "!VENV_TMP!" >nul
                "!PYTHON!" "!VENV_TMP!\perf_pyparsing.py" --append-csv "%CSV%"
                set EXITCODE=!ERRORLEVEL!
                popd >nul
                if not !EXITCODE! EQU 0 (
                  echo perf run failed for pyparsing %%V on Python %%P, continuing...
                )
              )
            )
          )
        )
      )
    )
  )
  REM ---- Cumulative elapsed time after this matrix entry ----
  for /f %%A in ('powershell -NoProfile -Command "[int]([DateTimeOffset]::UtcNow.ToUnixTimeSeconds())"') do set NOW_TS=%%A
  set /a ELAPSED=NOW_TS-START_TS
  set /a ELAPSED_MIN=ELAPSED/60
  set /a ELAPSED_SEC=ELAPSED%%60
  set "PADSEC=0!ELAPSED_SEC!"
  set "PADSEC=!PADSEC:~-2!"
  echo Cumulative elapsed: !ELAPSED_MIN!:!PADSEC!
)

echo.
echo Consolidated results written to:
echo   %CSV%

REM ---- Total elapsed time for full run ----
for /f %%A in ('powershell -NoProfile -Command "[int]([DateTimeOffset]::UtcNow.ToUnixTimeSeconds())"') do set END_TS=%%A
set /a TOTAL=END_TS-START_TS
set /a T_MIN=TOTAL/60
set /a T_SEC=TOTAL%%60
set "T_PADSEC=0!T_SEC!"
set "T_PADSEC=!T_PADSEC:~-2!"
echo Total elapsed: !T_MIN!:!T_PADSEC!

popd >nul
endlocal
exit /b 0
