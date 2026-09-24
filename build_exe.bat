@echo off
setlocal
call .venv\Scripts\activate
python -m pip install pyinstaller
pyinstaller --onefile --name USTUJ_RECORDS --add-data "templates;templates" --add-data "static;static" --add-data "media;media" main.py
pause
