from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

base_dir = Path(__file__).resolve().parent
database_dir = base_dir / "database"
database_dir.mkdir(exist_ok=True)
database_url = f"sqlite:///{database_dir / 'vinyl_store.sqlite3'}"

engine = create_engine(database_url, connect_args={"check_same_thread": False})

@event.listens_for(engine, "connect")
def enable_foreign_keys(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase):
    pass
