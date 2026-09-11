@echo off
python -m venv .venv
call .venv\Scripts\activate
python -m pip install -U pip
pip install -r requirements-dev.txt
pyinstaller --noconfirm --windowed --name "CAD Translator" run.py
if errorlevel 1 exit /b 1
echo Built app: dist\CAD Translator\CAD Translator.exe
