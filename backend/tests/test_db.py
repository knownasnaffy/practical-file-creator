import sqlite3
import pytest
from app.db import get_connection, init_db


def test_schema_creation_and_foreign_keys(tmp_path):
    db_file = tmp_path / "fk_test.db"
    init_db(db_file)
    conn = get_connection(db_file)

    # Verify PRAGMA foreign_keys is ON
    fk_status = conn.execute("PRAGMA foreign_keys;").fetchone()[0]
    assert fk_status == 1

    # Insert a practical file
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO practical_files (subject_name, directory_path, cover_page_count)
        VALUES ('DBMS', '/tmp/dbms', 2)
    """)
    pf_id = cursor.lastrowid

    # Insert task
    cursor.execute("""
        INSERT INTO tasks (practical_file_id, title, order_index, status)
        VALUES (?, 'Task 1', 1, 'drafting')
    """, (pf_id,))
    task_id = cursor.lastrowid

    # Insert image placeholder
    cursor.execute("""
        INSERT INTO image_placeholders (task_id, position, search_query, source_type)
        VALUES (?, 1, 'SQL Server Setup', 'search')
    """, (task_id,))

    # Test ON DELETE CASCADE from practical_file
    cursor.execute("DELETE FROM practical_files WHERE id = ?", (pf_id,))
    conn.commit()

    assert conn.execute("SELECT COUNT(*) FROM tasks WHERE id = ?", (task_id,)).fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM image_placeholders WHERE task_id = ?", (task_id,)).fetchone()[0] == 0
    conn.close()


def test_unique_constraints(tmp_path):
    db_file = tmp_path / "unique_test.db"
    init_db(db_file)
    conn = get_connection(db_file)
    cursor = conn.cursor()

    cursor.execute("INSERT INTO practical_files (subject_name, directory_path) VALUES ('OS', '/tmp/os')")
    pf_id = cursor.lastrowid

    # Duplicate directory path should raise IntegrityError
    with pytest.raises(sqlite3.IntegrityError):
        cursor.execute("INSERT INTO practical_files (subject_name, directory_path) VALUES ('OS 2', '/tmp/os')")

    # Duplicate order_index in same practical_file should raise IntegrityError
    cursor.execute("INSERT INTO tasks (practical_file_id, title, order_index) VALUES (?, 'T1', 1)", (pf_id,))
    with pytest.raises(sqlite3.IntegrityError):
        cursor.execute("INSERT INTO tasks (practical_file_id, title, order_index) VALUES (?, 'T2', 1)", (pf_id,))

    conn.close()
