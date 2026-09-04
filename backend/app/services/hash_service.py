import hashlib
from pathlib import Path
import sqlite3
from typing import Optional


def compute_task_content_hash(markdown_path: Optional[str | Path], assets_dir: Optional[str | Path]) -> str:
    """
    Computes deterministic SHA-256 hash over:
    1. The markdown file bytes.
    2. Every file in the assets directory (sorted by filename), hashing both filename and contents.
    """
    hasher = hashlib.sha256()

    # Hash markdown file if exists
    if markdown_path:
        md_file = Path(markdown_path)
        if md_file.is_file():
            with open(md_file, "rb") as f:
                hasher.update(b"MD_CONTENT:")
                hasher.update(f.read())

    # Hash assets dir files in sorted order
    if assets_dir:
        a_dir = Path(assets_dir)
        if a_dir.is_dir():
            for item in sorted(a_dir.iterdir()):
                if item.is_file():
                    hasher.update(b"ASSET_NAME:")
                    hasher.update(item.name.encode("utf-8"))
                    hasher.update(b"ASSET_BYTES:")
                    with open(item, "rb") as f:
                        hasher.update(f.read())

    return hasher.hexdigest()


def check_and_update_task_integrity(conn: sqlite3.Connection, practical_file_id: int) -> None:
    """
    Scans tasks for a practical file on load:
    Recomputes SHA-256 hash for each generated task.
    If stored content_hash differs from live hash on disk:
      flags needs_regeneration = 1, regeneration_reason = 'edited outside app'
      (unless already flagged with 'starting page changed').
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, markdown_path, assets_dir, content_hash, needs_regeneration, regeneration_reason, status
        FROM tasks
        WHERE practical_file_id = ?
    """, (practical_file_id,))
    tasks = cursor.fetchall()

    for task in tasks:
        # Only check generated tasks that have a stored hash
        if task["status"] == "generated" and task["content_hash"]:
            live_hash = compute_task_content_hash(task["markdown_path"], task["assets_dir"])
            if live_hash != task["content_hash"]:
                # Only overwrite reason if not already 'starting page changed'
                current_reason = task["regeneration_reason"]
                if current_reason != "starting page changed":
                    cursor.execute("""
                        UPDATE tasks
                        SET needs_regeneration = 1,
                            regeneration_reason = 'edited outside app'
                        WHERE id = ?
                    """, (task["id"],))
