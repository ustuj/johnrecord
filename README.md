# USTUJ RECORDS

Демонстрационный интернет-магазин виниловых пластинок по требованиям КОД 09.02.07-2-2026.

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

## Модуль 1 — база данных
- `data/source/` — исходные файлы, предоставленные для задания.
- `data/import_ready/` — подготовленные XLSX-файлы для новой предметной области.
- `data/processed/` — нормализованные подготовленные данные для заполнения БД.
- `database/vinyl_store.sql` — итоговый SQL-скрипт со структурой и данными.
- `database/vinyl_store.sqlite3` — локальный файл БД создаётся скриптом `scripts/init_database.py` и не хранится в Git.
- `docs/er_diagram.drawio` — редактируемая ER-диаграмма для draw.io.
- `docs/er_diagram.pdf` — версия ER для сдачи.

## Модуль 2 — алгоритм и приложение
- `docs/module2_algorithm.drawio` — редактируемая блок-схема.
- `docs/module2_algorithm.pdf` — PDF для сдачи.
- `docs/module2_algorithm.docx` — DOCX-версия блок-схемы.
- `docs/module2_screenshots.docx` — документ со скриншотами отладки.
- `docs/ui_check/` — исходные скриншоты проверки.

## Модули 3–4
В приложении реализованы:
- последовательная навигация;
- обработка ошибок, предупреждения и информативные сообщения;
- каталог;
- поиск по текстовым данным;
- сортировка по остатку;
- фильтр по поставщику;
- совместная работа поиска, фильтра и сортировки в реальном времени;
- добавление, редактирование и удаление товаров для администратора;
- загрузка, замена и удаление изображений;
- запрет удаления товара, присутствующего в заказе;
- просмотр заказов менеджером и администратором;
- добавление, редактирование и удаление заказов администратором.

## Обложки
В `data/processed/products.csv` и `data/import_ready/Tovar_import.xlsx` указаны источники реальных обложек использованных релизов.

Для локальной демонстрации с Интернетом можно выполнить:

```powershell
python scripts/cache_covers.py
python scripts/init_database.py
```

Скрипт сохранит успешно загруженные обложки в `media/products/` и переведёт соответствующие записи БД на локальные пути. Если источник недоступен, приложение использует `static/resources/picture.png`.

## Стиль
Использованы требования руководства по стилю: Times New Roman, `#FFFFFF`, `#7FFF00`, `#00FA9A`; для скидки более 15% — `#2E8B57`.

## Git
В `.gitignore` исключены `.venv`, `.env`, Python-кэш, логи и локальная SQLite-БД.
