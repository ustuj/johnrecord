# USTUJ RECORDS

## Стек
- Python
- FastAPI
- SQLAlchemy
- SQLite
- HTML / CSS / JavaScript

## Запуск
Windows:

```text
run.bat
```

или вручную:

```powershell
py -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python scripts/init_database.py
python -m uvicorn main:app --reload
```

Открыть: `http://127.0.0.1:8000/`

## Учётные записи
- Администратор: `admin` / `admin123`
- Менеджер: `manager` / `manager123`
- Клиент: `client` / `client123`
