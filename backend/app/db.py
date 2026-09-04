import sqlite3
from collections.abc import Generator
from pathlib import Path
from typing import Optional

from app.config import DEFAULT_DB_PATH

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS practical_files (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_name      TEXT NOT NULL,
    directory_path    TEXT NOT NULL UNIQUE,
    cover_page_count  INTEGER NOT NULL DEFAULT 2,
    created_at        TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS tasks (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    practical_file_id     INTEGER NOT NULL REFERENCES practical_files(id) ON DELETE CASCADE,
    title                 TEXT NOT NULL,
    order_index           INTEGER NOT NULL,
    markdown_path         TEXT,
    assets_dir            TEXT,
    pdf_path              TEXT,
    page_count            INTEGER,
    content_hash          TEXT,
    status                TEXT NOT NULL DEFAULT 'drafting'
                          CHECK (status IN ('drafting','pasted','resolving_images','generated')),
    needs_regeneration    INTEGER NOT NULL DEFAULT 0,
    regeneration_reason   TEXT
                          CHECK (regeneration_reason IN ('starting page changed','edited outside app')
                                 OR regeneration_reason IS NULL),
    UNIQUE (practical_file_id, order_index)
);

CREATE TABLE IF NOT EXISTS image_placeholders (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id        INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    position       INTEGER NOT NULL,
    search_query   TEXT NOT NULL,
    source_type    TEXT NOT NULL DEFAULT 'search' CHECK (source_type IN ('search','custom')),
    source_value   TEXT,
    resolved_path  TEXT,
    UNIQUE (task_id, position)
);

CREATE INDEX IF NOT EXISTS idx_tasks_practical_file ON tasks(practical_file_id, order_index);
CREATE INDEX IF NOT EXISTS idx_placeholders_task ON image_placeholders(task_id, position);
"""

_current_db_path: Path = DEFAULT_DB_PATH


def set_db_path(path: Path | str) -> None:
    global _current_db_path
    _current_db_path = Path(path)


def get_db_path() -> Path:
    return _current_db_path


def get_connection(db_path: Optional[Path | str] = None) -> sqlite3.Connection:
    target_path = Path(db_path) if db_path else _current_db_path
    if str(target_path) != ":memory:":
        target_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path: Optional[Path | str] = None) -> None:
    conn = get_connection(db_path)
    try:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
    finally:
        conn.close()


def get_db() -> Generator[sqlite3.Connection, None, None]:
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
