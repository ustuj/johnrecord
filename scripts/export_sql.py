from pathlib import Path
import re
import sqlite3

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "database" / "vinyl_store.sqlite3"
OUT = ROOT / "database" / "vinyl_store.sql"

TABLE_ORDER = {
    "categories": 1,
    "labels": 2,
    "manufacturers": 3,
    "record_formats": 4,
    "suppliers": 5,
    "users": 6,
    "pickup_points": 7,
    "products": 8,
    "orders": 9,
    "order_items": 10,
}


def table_name(statement: str) -> str:
    create_match = re.match(r"CREATE TABLE\s+(?:IF NOT EXISTS\s+)?([\w\"]+)", statement, re.I)
    if create_match:
        return create_match.group(1).strip('"')
    insert_match = re.match(r'INSERT INTO\s+"?([\w]+)"?', statement, re.I)
    if insert_match:
        return insert_match.group(1)
    index_match = re.match(r'CREATE (?:UNIQUE )?INDEX\s+(?:IF NOT EXISTS\s+)?\S+\s+ON\s+"?([\w]+)"?', statement, re.I)
    if index_match:
        return index_match.group(1)
    return ""


with sqlite3.connect(DB) as connection:
    dump = [
        statement
        for statement in connection.iterdump()
        if statement not in {"BEGIN TRANSACTION;", "COMMIT;"}
    ]

    create_statements = sorted(
        (statement for statement in dump if statement.upper().startswith("CREATE TABLE ")),
        key=lambda statement: TABLE_ORDER.get(table_name(statement), 99),
    )
    index_statements = [
        statement
        for statement in dump
        if statement.upper().startswith("CREATE INDEX ")
        or statement.upper().startswith("CREATE UNIQUE INDEX ")
    ]
    insert_statements = sorted(
        (statement for statement in dump if statement.upper().startswith("INSERT INTO ")),
        key=lambda statement: TABLE_ORDER.get(table_name(statement), 99),
    )

    lines = [
        "PRAGMA foreign_keys = ON;",
        "",
        "BEGIN TRANSACTION;",
        "",
        "-- Структура БД",
        *create_statements,
        "",
        "-- Индексы",
        *index_statements,
        "",
        "-- Данные",
        *insert_statements,
        "",
        "COMMIT;",
    ]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")

print(f"SQL exported to {OUT}")
