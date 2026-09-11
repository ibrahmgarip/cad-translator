#!/usr/bin/env bash
set -euo pipefail

ODA_APP="/Applications/ODAFileConverter.app"
if [[ ! -x "$ODA_APP/Contents/MacOS/ODAFileConverter" ]]; then
  echo "Missing ODA File Converter: $ODA_APP" >&2
  exit 1
fi

python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements-dev.txt
pyinstaller --noconfirm --clean --windowed --name "CAD Translator" \
  run.py

# ODA is a signed nested Qt application. Copy it after PyInstaller finishes so
# PyInstaller does not try to re-sign its embedded frameworks.
mkdir -p "dist/CAD Translator.app/Contents/Resources"
rm -rf "dist/CAD Translator.app/Contents/Resources/ODAFileConverter.app"
cp -R "$ODA_APP" "dist/CAD Translator.app/Contents/Resources/ODAFileConverter.app"

printf '\nBuilt app: dist/CAD Translator.app\n'
