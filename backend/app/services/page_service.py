import sqlite3
from typing import NamedTuple


class StartingPageInfo(NamedTuple):
    task_id: int
    computed_starting_page: int
    cover_page_count: int
    accumulated_earlier_pages: int


def calculate_starting_page(conn: sqlite3.Connection, task_id: int) -> StartingPageInfo:
    r"""
    Computes starting page for a task:
    cover_page_count + 1 + sum(page_count for all tasks with order_index < current.order_index)
    Note: Page numbering in document begins at cover_page_count + 1.
    Formula: cover_page_count + sum(earlier_pages) + 1.
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT t.id, t.practical_file_id, t.order_index, pf.cover_page_count
        FROM tasks t
        JOIN practical_files pf ON t.practical_file_id = pf.id
        WHERE t.id = ?
    """, (task_id,))
    row = cursor.fetchone()
    if not row:
        raise ValueError(f"Task {task_id} not found")

    pf_id = row["practical_file_id"]
    order_index = row["order_index"]
    cover_page_count = row["cover_page_count"]

    cursor.execute("""
        SELECT COALESCE(SUM(page_count), 0) as total_earlier_pages
        FROM tasks
        WHERE practical_file_id = ? AND order_index < ? AND page_count IS NOT NULL
    """, (pf_id, order_index))
    sum_row = cursor.fetchone()
    total_earlier = sum_row["total_earlier_pages"] if sum_row else 0

    computed_starting_page = cover_page_count + total_earlier + 1

    return StartingPageInfo(
        task_id=task_id,
        computed_starting_page=computed_starting_page,
        cover_page_count=cover_page_count,
        accumulated_earlier_pages=total_earlier,
    )


def cascade_page_drift_on_task_update(
    conn: sqlite3.Connection,
    practical_file_id: int,
    order_index: int
) -> int:
    """
    Flags all subsequent tasks (order_index > current) as needing regeneration
    due to 'starting page changed'.
    """
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE tasks
        SET needs_regeneration = 1,
            regeneration_reason = 'starting page changed'
        WHERE practical_file_id = ? AND order_index > ? AND status = 'generated'
    """, (practical_file_id, order_index))
    return cursor.rowcount


def cascade_cover_page_drift(
    conn: sqlite3.Connection,
    practical_file_id: int
) -> int:
    """
    Flags all generated tasks in a practical file as needing regeneration
    due to cover_page_count change.
    """
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE tasks
        SET needs_regeneration = 1,
            regeneration_reason = 'starting page changed'
        WHERE practical_file_id = ? AND status = 'generated'
    """, (practical_file_id,))
    return cursor.rowcount
