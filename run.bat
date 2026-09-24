@echo off
setlocal
py -m venv .venv
call .venv\Scripts\activate
python -m pip install -r requirements.txt
python scripts\init_database.py
python -m uvicorn main:app --reload
pause
