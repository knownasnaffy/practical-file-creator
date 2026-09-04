import os
from pathlib import Path
import sqlite3
import tempfile
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.db import get_db
from app.models import (
    PlaceholderPatch,
    PlaceholderResponse,
    PlaceholderUploadResponse,
)
from app.services.image_service import get_image_extension, save_uploaded_image

router = APIRouter(tags=["placeholders"])
DbDep = Annotated[sqlite3.Connection, Depends(get_db)]


@router.get("/tasks/{task_id}/placeholders", response_model=list[PlaceholderResponse])
def list_task_placeholders(task_id: int, db: DbDep) -> list[PlaceholderResponse]:
    cursor = db.cursor()
    cursor.execute("SELECT id FROM tasks WHERE id = ?", (task_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    cursor.execute("""
        SELECT * FROM image_placeholders
        WHERE task_id = ?
        ORDER BY position ASC
    """, (task_id,))
    rows = cursor.fetchall()
    return [
        PlaceholderResponse(
            id=r["id"],
            task_id=r["task_id"],
            position=r["position"],
            search_query=r["search_query"],
            source_type=r["source_type"],
            source_value=r["source_value"],
            resolved_path=r["resolved_path"],
            error=None,
        )
        for r in rows
    ]


@router.patch("/placeholders/{placeholder_id}", response_model=PlaceholderResponse)
def update_placeholder_source(
    placeholder_id: int,
    payload: PlaceholderPatch,
    db: DbDep
) -> PlaceholderResponse:
    cursor = db.cursor()
    cursor.execute("SELECT * FROM image_placeholders WHERE id = ?", (placeholder_id,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Placeholder not found")

    cursor.execute("""
        UPDATE image_placeholders
        SET source_value = ?,
            source_type = ?,
            resolved_path = NULL
        WHERE id = ?
    """, (payload.source_value.strip(), payload.source_type, placeholder_id))

    cursor.execute("SELECT * FROM image_placeholders WHERE id = ?", (placeholder_id,))
    updated = cursor.fetchone()
    return PlaceholderResponse(
        id=updated["id"],
        task_id=updated["task_id"],
        position=updated["position"],
        search_query=updated["search_query"],
        source_type=updated["source_type"],
        source_value=updated["source_value"],
        resolved_path=updated["resolved_path"],
        error=None,
    )


@router.post("/placeholders/{placeholder_id}/upload", response_model=PlaceholderUploadResponse)
def upload_placeholder_image(
    placeholder_id: int,
    file: UploadFile,
    db: DbDep
) -> PlaceholderUploadResponse:
    cursor = db.cursor()
    cursor.execute("""
        SELECT ip.*, t.practical_file_id, pf.directory_path
        FROM image_placeholders ip
        JOIN tasks t ON ip.task_id = t.id
        JOIN practical_files pf ON t.practical_file_id = pf.id
        WHERE ip.id = ?
    """, (placeholder_id,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Placeholder not found")

    file_bytes = file.file.read()
    if not file_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")

    # Save to a staging directory in practical file assets
    staging_dir = Path(row["directory_path"]) / "assets" / "uploads"
    staging_dir.mkdir(parents=True, exist_ok=True)
    ext = get_image_extension(file.content_type, file.filename)
    staging_file = staging_dir / f"ph_{placeholder_id}_{row['position']}{ext}"

    with open(staging_file, "wb") as f:
        f.write(file_bytes)

    cursor.execute("""
        UPDATE image_placeholders
        SET source_type = 'custom',
            source_value = ?,
            resolved_path = ?
        WHERE id = ?
    """, (str(staging_file), str(staging_file), placeholder_id))

    return PlaceholderUploadResponse(
        id=row["id"],
        task_id=row["task_id"],
        position=row["position"],
        source_type="custom",
        source_value=str(staging_file),
        resolved_path=str(staging_file),
    )


@router.post("/placeholders/{placeholder_id}/retry", response_model=PlaceholderResponse)
def retry_placeholder_download(placeholder_id: int, db: DbDep) -> PlaceholderResponse:
    cursor = db.cursor()
    cursor.execute("SELECT * FROM image_placeholders WHERE id = ?", (placeholder_id,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Placeholder not found")

    # Reset resolved_path to allow fresh download during next generation
    cursor.execute("""
        UPDATE image_placeholders
        SET resolved_path = NULL
        WHERE id = ?
    """, (placeholder_id,))

    cursor.execute("SELECT * FROM image_placeholders WHERE id = ?", (placeholder_id,))
    updated = cursor.fetchone()
    return PlaceholderResponse(
        id=updated["id"],
        task_id=updated["task_id"],
        position=updated["position"],
        search_query=updated["search_query"],
        source_type=updated["source_type"],
        source_value=updated["source_value"],
        resolved_path=updated["resolved_path"],
        error=None,
    )


@router.get("/placeholders/{placeholder_id}/image")
def get_placeholder_image(placeholder_id: int, db: DbDep):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM image_placeholders WHERE id = ?", (placeholder_id,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Placeholder not found")

    file_path = row["resolved_path"] or row["source_value"]
    if row["source_type"] == "custom" and file_path:
        p = Path(file_path)
        if p.is_file():
            from fastapi.responses import FileResponse
            return FileResponse(path=str(p))
    elif row["source_type"] == "search" and row["source_value"]:
        if row["resolved_path"] and Path(row["resolved_path"]).is_file():
            from fastapi.responses import FileResponse
            return FileResponse(path=row["resolved_path"])
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=row["source_value"])

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No image file available")
