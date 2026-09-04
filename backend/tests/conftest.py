import os
import sqlite3
import tempfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.db import init_db, set_db_path, get_db
from app.main import app


@pytest.fixture
def temp_workspace(tmp_path: Path):
    """Provides a temporary workspace folder for practical file tests."""
    ws = tmp_path / "practical_file_root"
    ws.mkdir(parents=True, exist_ok=True)
    return ws


@pytest.fixture
def test_db(tmp_path: Path):
    """Initializes a temporary SQLite database for testing."""
    db_file = tmp_path / "test_index.db"
    set_db_path(db_file)
    init_db(db_file)
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    yield conn
    conn.close()


@pytest.fixture
def client(test_db, tmp_path: Path):
    """FastAPI TestClient with overridden database."""
    def override_get_db():
        conn = sqlite3.connect(str(tmp_path / "test_index.db"))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
