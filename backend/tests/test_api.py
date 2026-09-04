from pathlib import Path
import pytest


def test_practical_file_and_task_lifecycle(client, tmp_path):
    pf_dir = tmp_path / "dbms_subject"
    
    # 1. Create practical file
    res = client.post("/practical-files", json={
        "subject_name": "Database Management Systems",
        "directory_path": str(pf_dir),
        "cover_page_count": 2
    })
    assert res.status_code == 201, res.text
    pf_data = res.json()
    pf_id = pf_data["id"]
    assert pf_data["subject_name"] == "Database Management Systems"
    assert pf_data["cover_page_count"] == 2

    # 2. Create Task 1
    res = client.post(f"/practical-files/{pf_id}/tasks", json={
        "title": "Introduction to SQL and installation of SQL Server / Oracle"
    })
    assert res.status_code == 201, res.text
    task1_data = res.json()
    t1 = task1_data["task"]
    t1_id = t1["id"]
    assert t1["order_index"] == 1
    assert t1["status"] == "drafting"
    assert "Generate my practical file task 1: Introduction to SQL" in task1_data["instruction_block"]

    # 3. Paste Markdown for Task 1
    valid_markdown = """---
title: "Practical 1: SQL Server Setup"
---

# Introduction
Overview of SQL and installation steps.

![SQL Server Installer](placeholder_1)

## Details
Additional steps.

![Management Studio](placeholder_2)
"""
    res = client.post(f"/tasks/{t1_id}/markdown", json={"raw_markdown": valid_markdown})
    assert res.status_code == 200, res.text
    md_res = res.json()
    assert md_res["valid"] is True
    assert md_res["placeholder_count"] == 2
    assert len(md_res["placeholders"]) == 2

    # 4. Check placeholders
    res = client.get(f"/tasks/{t1_id}/placeholders")
    assert res.status_code == 200
    placeholders = res.json()
    assert len(placeholders) == 2
    ph1_id = placeholders[0]["id"]
    ph2_id = placeholders[1]["id"]

    # 5. Patch placeholder 1 with search URL
    res = client.patch(f"/placeholders/{ph1_id}", json={
        "source_value": "https://example.com/sql_installer.png",
        "source_type": "search"
    })
    assert res.status_code == 200
    assert res.json()["source_value"] == "https://example.com/sql_installer.png"

    # 5b. Test upload on placeholder 2 (simulating raw image paste/upload)
    dummy_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc`\x00\x00\x00\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82"
    res = client.post(
        f"/placeholders/{ph2_id}/upload",
        files={"file": ("clipboard_paste.png", dummy_png, "image/png")}
    )
    assert res.status_code == 200
    assert res.json()["source_type"] == "custom"

    # Test image preview endpoint
    img_res = client.get(f"/placeholders/{ph2_id}/image")
    assert img_res.status_code == 200
    assert img_res.content == dummy_png

    # 6. Check Starting Page calculation
    res = client.get(f"/tasks/{t1_id}/starting-page")
    assert res.status_code == 200
    sp_data = res.json()
    assert sp_data["computed_starting_page"] == 3

    # 7. Test Markdown validation errors
    bad_markdown = """---
title: "Bad"
---
# Header
---
Extra separator
"""
    res = client.post(f"/tasks/{t1_id}/markdown", json={"raw_markdown": bad_markdown})
    assert res.status_code == 422
    assert "Found 3 '---' delimiters" in res.json()["detail"]

    # 8. Create Task 2 and reorder
    res = client.post(f"/practical-files/{pf_id}/tasks", json={
        "title": "DDL Commands"
    })
    assert res.status_code == 201
    t2_id = res.json()["task"]["id"]

    # Reorder tasks: [t2, t1]
    res = client.patch(f"/practical-files/{pf_id}/tasks/reorder", json={
        "task_ids": [t2_id, t1_id]
    })
    assert res.status_code == 200
    reordered = res.json()
    assert reordered[0]["id"] == t2_id
    assert reordered[0]["order_index"] == 1
    assert reordered[1]["id"] == t1_id
    assert reordered[1]["order_index"] == 2
