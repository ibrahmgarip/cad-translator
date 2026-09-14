@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "APP_VERSION=%~1"
if not defined APP_VERSION set "APP_VERSION=0.2.0-beta.1"

where py >nul 2>nul
if %errorlevel% equ 0 (
  set "PYTHON_CMD=py -3.12"
) else (
  set "PYTHON_CMD=python"
)

echo [1/5] Creating a clean Python environment...
%PYTHON_CMD% -m venv --clear .venv
if errorlevel 1 goto :failed

set "VENV_PYTHON=%CD%\.venv\Scripts\python.exe"

echo [2/5] Installing dependencies...
"%VENV_PYTHON%" -m pip install --disable-pip-version-check -r requirements-dev.txt
if errorlevel 1 goto :failed

echo [3/5] Running tests...
"%VENV_PYTHON%" -m pytest -q
if errorlevel 1 goto :failed

echo [4/5] Building the Windows application...
"%VENV_PYTHON%" -m PyInstaller --noconfirm --clean --windowed --onedir --name "CAD Translator" run.py
if errorlevel 1 goto :failed

set "ZIP_PATH=dist\CAD-Translator-%APP_VERSION%-Windows-x64.zip"
echo [5/5] Creating %ZIP_PATH%...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -Path 'dist\CAD Translator' -DestinationPath '%ZIP_PATH%' -Force"
if errorlevel 1 goto :failed

echo.
echo Build complete:
echo   Application: dist\CAD Translator\CAD Translator.exe
echo   ZIP package: %ZIP_PATH%
echo.
echo ODA File Converter is not redistributed with this package.
echo Install it separately on each Windows computer that will open DWG files.
exit /b 0

:failed
set "BUILD_ERROR=%errorlevel%"
echo.
echo Windows build failed with exit code %BUILD_ERROR%.
exit /b %BUILD_ERROR%
