from pathlib import Path
from app.services.hash_service import (
    check_and_update_task_integrity,
    compute_task_content_hash,
)


def test_compute_task_content_hash_determinism(tmp_path):
    md_file = tmp_path / "task.md"
    md_file.write_text("# Hello World", encoding="utf-8")

    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    (assets_dir / "image-02.png").write_bytes(b"image2_bytes")
    (assets_dir / "image-01.png").write_bytes(b"image1_bytes")

    hash1 = compute_task_content_hash(md_file, assets_dir)
    hash2 = compute_task_content_hash(md_file, assets_dir)
    assert hash1 == hash2
    assert len(hash1) == 64


def test_hash_integrity_drift_check(test_db, tmp_path):
    md_file = tmp_path / "task1.md"
    md_file.write_text("# Initial Content", encoding="utf-8")
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()

    initial_hash = compute_task_content_hash(md_file, assets_dir)

    cursor = test_db.cursor()
    cursor.execute("INSERT INTO practical_files (subject_name, directory_path) VALUES ('Algo', ?)", (str(tmp_path),))
    pf_id = cursor.lastrowid

    cursor.execute("""
        INSERT INTO tasks (practical_file_id, title, order_index, markdown_path, assets_dir, content_hash, status)
        VALUES (?, 'Task 1', 1, ?, ?, ?, 'generated')
    """, (pf_id, str(md_file), str(assets_dir), initial_hash))
    task_id = cursor.lastrowid
    test_db.commit()

    # Initial check should find no drift
    check_and_update_task_integrity(test_db, pf_id)
    task = test_db.execute("SELECT needs_regeneration, regeneration_reason FROM tasks WHERE id = ?", (task_id,)).fetchone()
    assert task["needs_regeneration"] == 0

    # Modify markdown file outside the app (e.g. Neovim)
    md_file.write_text("# Modified Content Outside App", encoding="utf-8")

    # Integrity check should detect drift
    check_and_update_task_integrity(test_db, pf_id)
    test_db.commit()
    task = test_db.execute("SELECT needs_regeneration, regeneration_reason FROM tasks WHERE id = ?", (task_id,)).fetchone()
    assert task["needs_regeneration"] == 1
    assert task["regeneration_reason"] == "edited outside app"
