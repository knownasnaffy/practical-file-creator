from app.services.page_service import (
    calculate_starting_page,
    cascade_cover_page_drift,
    cascade_page_drift_on_task_update,
)


def test_calculate_starting_page(test_db):
    cursor = test_db.cursor()
    cursor.execute("""
        INSERT INTO practical_files (subject_name, directory_path, cover_page_count)
        VALUES ('DBMS', '/tmp/dbms', 2)
    """)
    pf_id = cursor.lastrowid

    # Task 1 (order 1)
    cursor.execute("""
        INSERT INTO tasks (practical_file_id, title, order_index, page_count, status)
        VALUES (?, 'Task 1', 1, 4, 'generated')
    """, (pf_id,))
    t1_id = cursor.lastrowid

    # Task 2 (order 2)
    cursor.execute("""
        INSERT INTO tasks (practical_file_id, title, order_index, page_count, status)
        VALUES (?, 'Task 2', 2, 3, 'generated')
    """, (pf_id,))
    t2_id = cursor.lastrowid

    # Task 3 (order 3)
    cursor.execute("""
        INSERT INTO tasks (practical_file_id, title, order_index, status)
        VALUES (?, 'Task 3', 3, 'drafting')
    """, (pf_id,))
    t3_id = cursor.lastrowid

    test_db.commit()

    # Task 1 starting page = cover_page_count(2) + 0 + 1 = 3
    sp1 = calculate_starting_page(test_db, t1_id)
    assert sp1.computed_starting_page == 3

    # Task 2 starting page = cover_page_count(2) + task1_pages(4) + 1 = 7
    sp2 = calculate_starting_page(test_db, t2_id)
    assert sp2.computed_starting_page == 7

    # Task 3 starting page = cover_page_count(2) + task1_pages(4) + task2_pages(3) + 1 = 10
    sp3 = calculate_starting_page(test_db, t3_id)
    assert sp3.computed_starting_page == 10


def test_cascade_page_drift_on_task_update(test_db):
    cursor = test_db.cursor()
    cursor.execute("""
        INSERT INTO practical_files (subject_name, directory_path, cover_page_count)
        VALUES ('DBMS', '/tmp/dbms', 2)
    """)
    pf_id = cursor.lastrowid

    cursor.execute("INSERT INTO tasks (practical_file_id, title, order_index, status) VALUES (?, 'T1', 1, 'generated')", (pf_id,))
    t1_id = cursor.lastrowid
    cursor.execute("INSERT INTO tasks (practical_file_id, title, order_index, status) VALUES (?, 'T2', 2, 'generated')", (pf_id,))
    t2_id = cursor.lastrowid
    cursor.execute("INSERT INTO tasks (practical_file_id, title, order_index, status) VALUES (?, 'T3', 3, 'generated')", (pf_id,))
    t3_id = cursor.lastrowid
    test_db.commit()

    # Task 1 changes page count: should cascade to T2 and T3, but NOT T1
    affected = cascade_page_drift_on_task_update(test_db, pf_id, order_index=1)
    test_db.commit()
    assert affected == 2

    # T1 should not be flagged
    t1 = test_db.execute("SELECT needs_regeneration, regeneration_reason FROM tasks WHERE id = ?", (t1_id,)).fetchone()
    assert t1["needs_regeneration"] == 0

    # T2 and T3 should be flagged with 'starting page changed'
    t2 = test_db.execute("SELECT needs_regeneration, regeneration_reason FROM tasks WHERE id = ?", (t2_id,)).fetchone()
    assert t2["needs_regeneration"] == 1
    assert t2["regeneration_reason"] == "starting page changed"

    t3 = test_db.execute("SELECT needs_regeneration, regeneration_reason FROM tasks WHERE id = ?", (t3_id,)).fetchone()
    assert t3["needs_regeneration"] == 1
    assert t3["regeneration_reason"] == "starting page changed"


def test_cascade_cover_page_drift(test_db):
    cursor = test_db.cursor()
    cursor.execute("INSERT INTO practical_files (subject_name, directory_path) VALUES ('OS', '/tmp/os')")
    pf_id = cursor.lastrowid
    cursor.execute("INSERT INTO tasks (practical_file_id, title, order_index, status) VALUES (?, 'T1', 1, 'generated')", (pf_id,))
    cursor.execute("INSERT INTO tasks (practical_file_id, title, order_index, status) VALUES (?, 'T2', 2, 'generated')", (pf_id,))
    test_db.commit()

    affected = cascade_cover_page_drift(test_db, pf_id)
    assert affected == 2
