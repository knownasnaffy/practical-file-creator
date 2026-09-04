from pathlib import Path
import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from app.db import get_db
from app.models import (
    GenerateRequest,
    GenerateResponse,
    MarkdownPasteRequest,
    MarkdownValidationResponse,
    PlaceholderResponse,
    StartingPageResponse,
    TaskResponse,
)
from app.services.markdown_service import validate_and_parse_markdown
from app.services.page_service import calculate_starting_page
from app.services.pdf_service import PdfBuildError, generate_task_pdf

router = APIRouter(prefix="/tasks", tags=["tasks"])
DbDep = Annotated[sqlite3.Connection, Depends(get_db)]


@router.get("/{task_id}", response_model=TaskResponse)
def get_task_detail(task_id: int, db: DbDep) -> TaskResponse:
    cursor = db.cursor()
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    return TaskResponse(
        id=row["id"],
        practical_file_id=row["practical_file_id"],
        title=row["title"],
        order_index=row["order_index"],
        markdown_path=row["markdown_path"],
        assets_dir=row["assets_dir"],
        pdf_path=row["pdf_path"],
        page_count=row["page_count"],
        content_hash=row["content_hash"],
        status=row["status"],
        needs_regeneration=bool(row["needs_regeneration"]),
        regeneration_reason=row["regeneration_reason"],
    )


@router.post("/{task_id}/markdown", response_model=MarkdownValidationResponse)
def paste_and_validate_markdown(
    task_id: int,
    payload: MarkdownPasteRequest,
    db: DbDep
) -> MarkdownValidationResponse:
    cursor = db.cursor()
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    task = cursor.fetchone()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    validation = validate_and_parse_markdown(payload.raw_markdown)
    if not validation.is_valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=validation.error_message or "Markdown validation failed."
        )

    # Write source markdown to disk
    markdown_path = Path(task["markdown_path"])
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    with open(markdown_path, "w", encoding="utf-8") as f:
        f.write(payload.raw_markdown)

    # Clear prior placeholders for this task
    cursor.execute("DELETE FROM image_placeholders WHERE task_id = ?", (task_id,))

    # Insert placeholders
    created_placeholders: list[PlaceholderResponse] = []
    for ph in validation.placeholders:
        cursor.execute("""
            INSERT INTO image_placeholders (task_id, position, search_query, source_type)
            VALUES (?, ?, ?, 'search')
        """, (task_id, ph.position, ph.search_query))
        ph_id = cursor.lastrowid
        created_placeholders.append(
            PlaceholderResponse(
                id=ph_id,
                task_id=task_id,
                position=ph.position,
                search_query=ph.search_query,
                source_type="search",
                source_value=None,
                resolved_path=None,
                error=None,
            )
        )

    new_status = "resolving_images" if created_placeholders else "pasted"
    cursor.execute("""
        UPDATE tasks
        SET status = ?,
            title = ?
        WHERE id = ?
    """, (new_status, validation.title or task["title"], task_id))

    return MarkdownValidationResponse(
        valid=True,
        title=validation.title,
        placeholder_count=len(created_placeholders),
        placeholders=created_placeholders,
        error=None,
    )


@router.get("/{task_id}/starting-page", response_model=StartingPageResponse)
def get_starting_page_preview(task_id: int, db: DbDep) -> StartingPageResponse:
    try:
        page_info = calculate_starting_page(db, task_id)
        return StartingPageResponse(
            task_id=task_id,
            computed_starting_page=page_info.computed_starting_page,
            cover_page_count=page_info.cover_page_count,
            accumulated_earlier_pages=page_info.accumulated_earlier_pages,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post("/{task_id}/generate", response_model=GenerateResponse)
def generate_pdf(
    task_id: int,
    payload: GenerateRequest,
    db: DbDep
) -> GenerateResponse:
    try:
        result = generate_task_pdf(
            conn=db,
            task_id=task_id,
            starting_page_override=payload.starting_page
        )
        return GenerateResponse(
            task_id=task_id,
            pdf_path=result.pdf_path,
            page_count=result.page_count,
            starting_page=result.starting_page,
            content_hash=result.content_hash,
            status="generated",
            stderr=result.stderr
        )
    except PdfBuildError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=exc.stderr or str(exc)
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        )


@router.get("/{task_id}/pdf")
def get_task_pdf(task_id: int, db: DbDep):
    cursor = db.cursor()
    cursor.execute("SELECT pdf_path, title FROM tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    if not row or not row["pdf_path"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PDF has not been generated for this task.")

    pdf_file = Path(row["pdf_path"])
    if not pdf_file.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PDF file not found on disk.")

    return FileResponse(
        path=str(pdf_file),
        media_type="application/pdf",
        filename=pdf_file.name
    )
