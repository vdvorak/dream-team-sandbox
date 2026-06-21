import glob
import os
import tempfile

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

# Tests run against SQLite (no Docker). DATABASE_URL must be set BEFORE importing the app.
_fd, _DB_PATH = tempfile.mkstemp(suffix=".db")
os.close(_fd)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_DB_PATH}"

from src.database import get_engine  # noqa: E402
from src.main import create_app  # noqa: E402

_MIGRATIONS_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "contracts", "db", "migrations"
)


@pytest.fixture(autouse=True)
async def _schema():
    # Drop all tables, then apply every V*.sql migration in order — adding a feature
    # (a new migration) needs no conftest change.
    engine = get_engine()
    files = sorted(glob.glob(os.path.join(_MIGRATIONS_DIR, "V*.sql")))
    async with engine.begin() as conn:
        rows = (
            await conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            )
        ).fetchall()
        for (name,) in rows:
            await conn.execute(text(f'DROP TABLE IF EXISTS "{name}"'))
        for f in files:
            sql = open(f, encoding="utf-8").read()
            for stmt in (s.strip() for s in sql.split(";")):
                if stmt:
                    await conn.execute(text(stmt))
    yield


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def client(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
