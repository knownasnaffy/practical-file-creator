import os
import sqlite3
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.db import get_db
from app.models import (
    PracticalFileCreate,
    PracticalFilePatch,
    PracticalFileResponse,
    PracticalFileWithTasksResponse,
    TaskCreate,
    TaskReorderRequest,
    TaskResponse,
    TaskWithInstructionResponse,
)
from app.services.hash_service import check_and_update_task_integrity
from app.services.instruction_service import render_instruction_prompt
from app.services.markdown_service import slugify
from app.services.page_service import cascade_cover_page_drift, cascade_page_drift_on_task_update

router = APIRouter(prefix="/practical-files", tags=["practical-files"])
DbDep = Annotated[sqlite3.Connection, Depends(get_db)]


@router.post("", response_model=PracticalFileResponse, status_code=status.HTTP_201_CREATED)
def create_practical_file(payload: PracticalFileCreate, db: DbDep) -> PracticalFileResponse:
    cursor = db.cursor()
    # Normalize directory path
    dir_path = str(Path(payload.directory_path).resolve())
    try:
        cursor.execute("""
            INSERT INTO practical_files (subject_name, directory_path, cover_page_count)
            VALUES (?, ?, ?)
        """, (payload.subject_name.strip(), dir_path, payload.cover_page_count))
        file_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Practical file already exists at this directory path."
        )

    # Ensure disk directories exist
    target_dir = Path(dir_path)
    (target_dir / "tasks").mkdir(parents=True, exist_ok=True)
    (target_dir / "assets").mkdir(parents=True, exist_ok=True)

    cursor.execute("SELECT * FROM practical_files WHERE id = ?", (file_id,))
    row = cursor.fetchone()
    return PracticalFileResponse(
        id=row["id"],
        subject_name=row["subject_name"],
        directory_path=row["directory_path"],
        cover_page_count=row["cover_page_count"],
        created_at=row["created_at"],
    )


@router.get("", response_model=list[PracticalFileResponse])
def list_practical_files(db: DbDep) -> list[PracticalFileResponse]:
    cursor = db.cursor()
    cursor.execute("SELECT * FROM practical_files ORDER BY created_at DESC")
    rows = cursor.fetchall()
    return [
        PracticalFileResponse(
            id=r["id"],
            subject_name=r["subject_name"],
            directory_path=r["directory_path"],
            cover_page_count=r["cover_page_count"],
            created_at=r["created_at"],
        )
        for r in rows
    ]


@router.get("/{pf_id}", response_model=PracticalFileWithTasksResponse)
def get_practical_file(pf_id: int, db: DbDep) -> PracticalFileWithTasksResponse:
    cursor = db.cursor()
    cursor.execute("SELECT * FROM practical_files WHERE id = ?", (pf_id,))
    pf = cursor.fetchone()
    if not pf:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Practical file not found")

    # Run integrity check on tasks
    check_and_update_task_integrity(db, pf_id)

    cursor.execute("""
        SELECT * FROM tasks
        WHERE practical_file_id = ?
        ORDER BY order_index ASC
    """, (pf_id,))
    task_rows = cursor.fetchall()

    return PracticalFileWithTasksResponse(
        practical_file=PracticalFileResponse(
            id=pf["id"],
            subject_name=pf["subject_name"],
            directory_path=pf["directory_path"],
            cover_page_count=pf["cover_page_count"],
            created_at=pf["created_at"],
        ),
        tasks=[
            TaskResponse(
                id=t["id"],
                practical_file_id=t["practical_file_id"],
                title=t["title"],
                order_index=t["order_index"],
                markdown_path=t["markdown_path"],
                assets_dir=t["assets_dir"],
                pdf_path=t["pdf_path"],
                page_count=t["page_count"],
                content_hash=t["content_hash"],
                status=t["status"],
                needs_regeneration=bool(t["needs_regeneration"]),
                regeneration_reason=t["regeneration_reason"],
            )
            for t in task_rows
        ]
    )


@router.patch("/{pf_id}", response_model=PracticalFileResponse)
def update_cover_page_count(pf_id: int, payload: PracticalFilePatch, db: DbDep) -> PracticalFileResponse:
    cursor = db.cursor()
    cursor.execute("SELECT * FROM practical_files WHERE id = ?", (pf_id,))
    pf = cursor.fetchone()
    if not pf:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Practical file not found")

    if pf["cover_page_count"] != payload.cover_page_count:
        cursor.execute("""
            UPDATE practical_files
            SET cover_page_count = ?
            WHERE id = ?
        """, (payload.cover_page_count, pf_id))
        cascade_cover_page_drift(db, pf_id)

    cursor.execute("SELECT * FROM practical_files WHERE id = ?", (pf_id,))
    updated = cursor.fetchone()
    return PracticalFileResponse(
        id=updated["id"],
        subject_name=updated["subject_name"],
        directory_path=updated["directory_path"],
        cover_page_count=updated["cover_page_count"],
        created_at=updated["created_at"],
    )


@router.post("/{pf_id}/tasks", response_model=TaskWithInstructionResponse, status_code=status.HTTP_201_CREATED)
def create_task_for_practical_file(pf_id: int, payload: TaskCreate, db: DbDep) -> TaskWithInstructionResponse:
    cursor = db.cursor()
    cursor.execute("SELECT * FROM practical_files WHERE id = ?", (pf_id,))
    pf = cursor.fetchone()
    if not pf:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Practical file not found")

    # Determine max order_index
    cursor.execute("""
        SELECT COALESCE(MAX(order_index), 0) AS max_order
        FROM tasks
        WHERE practical_file_id = ?
    """, (pf_id,))
    max_order = cursor.fetchone()["max_order"]
    new_order = max_order + 1

    clean_title = payload.title.strip()
    slug = slugify(clean_title, prefix=new_order)
    pf_dir = Path(pf["directory_path"])
    markdown_path = pf_dir / "tasks" / f"{slug}.md"
    assets_dir = pf_dir / "assets" / slug

    cursor.execute("""
        INSERT INTO tasks (practical_file_id, title, order_index, markdown_path, assets_dir, status)
        VALUES (?, ?, ?, ?, ?, 'drafting')
    """, (pf_id, clean_title, new_order, str(markdown_path), str(assets_dir)))
    task_id = cursor.lastrowid

    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    task_row = cursor.fetchone()

    instruction_block = render_instruction_prompt(
        task_number=new_order,
        task_title=clean_title
    )

    return TaskWithInstructionResponse(
        task=TaskResponse(
            id=task_row["id"],
            practical_file_id=task_row["practical_file_id"],
            title=task_row["title"],
            order_index=task_row["order_index"],
            markdown_path=task_row["markdown_path"],
            assets_dir=task_row["assets_dir"],
            pdf_path=task_row["pdf_path"],
            page_count=task_row["page_count"],
            content_hash=task_row["content_hash"],
            status=task_row["status"],
            needs_regeneration=bool(task_row["needs_regeneration"]),
            regeneration_reason=task_row["regeneration_reason"],
        ),
        instruction_block=instruction_block,
    )


@router.get("/{pf_id}/tasks", response_model=list[TaskResponse])
def list_tasks_for_practical_file(pf_id: int, db: DbDep) -> list[TaskResponse]:
    cursor = db.cursor()
    cursor.execute("SELECT id FROM practical_files WHERE id = ?", (pf_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Practical file not found")

    # Re-hash & drift check on task list load (§4.5)
    check_and_update_task_integrity(db, pf_id)

    cursor.execute("""
        SELECT * FROM tasks
        WHERE practical_file_id = ?
        ORDER BY order_index ASC
    """, (pf_id,))
    rows = cursor.fetchall()
    return [
        TaskResponse(
            id=r["id"],
            practical_file_id=r["practical_file_id"],
            title=r["title"],
            order_index=r["order_index"],
            markdown_path=r["markdown_path"],
            assets_dir=r["assets_dir"],
            pdf_path=r["pdf_path"],
            page_count=r["page_count"],
            content_hash=r["content_hash"],
            status=r["status"],
            needs_regeneration=bool(r["needs_regeneration"]),
            regeneration_reason=r["regeneration_reason"],
        )
        for r in rows
    ]


@router.patch("/{pf_id}/tasks/reorder", response_model=list[TaskResponse])
def reorder_tasks(pf_id: int, payload: TaskReorderRequest, db: DbDep) -> list[TaskResponse]:
    cursor = db.cursor()
    cursor.execute("SELECT id FROM practical_files WHERE id = ?", (pf_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Practical file not found")

    cursor.execute("SELECT id FROM tasks WHERE practical_file_id = ?", (pf_id,))
    existing_ids = {r["id"] for r in cursor.fetchall()}

    if set(payload.task_ids) != existing_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provided task IDs must match exactly all tasks in this practical file."
        )

    # Shift order_indexes temporarily to negative values to avoid UNIQUE constraint collisions
    for i, t_id in enumerate(payload.task_ids, start=1):
        cursor.execute("UPDATE tasks SET order_index = ? WHERE id = ?", (-i, t_id))

    # Apply positive new order_index
    for i, t_id in enumerate(payload.task_ids, start=1):
        cursor.execute("UPDATE tasks SET order_index = ? WHERE id = ?", (i, t_id))

    # Reordering invalidates starting pages for generated tasks
    cursor.execute("""
        UPDATE tasks
        SET needs_regeneration = 1,
            regeneration_reason = 'starting page changed'
        WHERE practical_file_id = ? AND status = 'generated'
    """, (pf_id,))

    cursor.execute("""
        SELECT * FROM tasks
        WHERE practical_file_id = ?
        ORDER BY order_index ASC
    """, (pf_id,))
    rows = cursor.fetchall()
    return [
        TaskResponse(
            id=r["id"],
            practical_file_id=r["practical_file_id"],
            title=r["title"],
            order_index=r["order_index"],
            markdown_path=r["markdown_path"],
            assets_dir=r["assets_dir"],
            pdf_path=r["pdf_path"],
            page_count=r["page_count"],
            content_hash=r["content_hash"],
            status=r["status"],
            needs_regeneration=bool(r["needs_regeneration"]),
            regeneration_reason=r["regeneration_reason"],
        )
        for r in rows
    ]
