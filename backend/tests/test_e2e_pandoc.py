import os
import shutil
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.db import init_db, set_db_path, get_db
from app.main import app


def test_full_e2e_sprint_pipeline(tmp_path):
    db_file = tmp_path / "e2e_index.db"
    set_db_path(db_file)
    init_db(db_file)

    def override_get_db():
        from app.db import get_connection
        conn = get_connection(db_file)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    # Practical file workspace
    pf_workspace = tmp_path / "dbms_practicals"

    # 1. Create practical file
    res = client.post("/practical-files", json={
        "subject_name": "Database Management Systems",
        "directory_path": str(pf_workspace),
        "cover_page_count": 2
    })
    assert res.status_code == 201
    pf_id = res.json()["id"]

    # 2. Create Task 1
    res = client.post(f"/practical-files/{pf_id}/tasks", json={
        "title": "Introduction to SQL and installation of SQL Server / Oracle"
    })
    assert res.status_code == 201
    t1 = res.json()["task"]
    t1_id = t1["id"]
    assert "Generate my practical file task 1:" in res.json()["instruction_block"]

    # 3. Paste Task 1 markdown with 2 placeholders
    t1_markdown = """---
title: "Practical 1: SQL Server Installation"
---

# Introduction
Structured Query Language (SQL) is a standardized programming language that is used to manage relational databases.

<!-- Screenshot of SQL installation wizard -->
![SQL Server Installation Wizard](placeholder_1)

## Verification
Verify the installation by running standard queries.

<!-- Screenshot of SQL Management Studio interface -->
![SQL Server Management Studio](placeholder_2)

## Summary
The installation was completed successfully.
"""
    res = client.post(f"/tasks/{t1_id}/markdown", json={"raw_markdown": t1_markdown})
    assert res.status_code == 200
    assert res.json()["placeholder_count"] == 2

    # 4. Resolve placeholders for Task 1 using small test image files
    phs = client.get(f"/tasks/{t1_id}/placeholders").json()
    assert len(phs) == 2

    # 1x1 valid PNG bytes
    import base64
    dummy_png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")

    res = client.post(
        f"/placeholders/{phs[0]['id']}/upload",
        files={"file": ("wizard.png", dummy_png, "image/png")}
    )
    assert res.status_code == 200

    res = client.post(
        f"/placeholders/{phs[1]['id']}/upload",
        files={"file": ("ssms.png", dummy_png, "image/png")}
    )
    assert res.status_code == 200

    # 5. Check Starting Page calculation for Task 1 (Cover=2 -> starting page = 3)
    sp_res = client.get(f"/tasks/{t1_id}/starting-page").json()
    assert sp_res["computed_starting_page"] == 3

    # 6. Generate Task 1 PDF
    gen_res = client.post(f"/tasks/{t1_id}/generate", json={})
    assert gen_res.status_code == 200, gen_res.text
    t1_gen = gen_res.json()
    assert t1_gen["status"] == "generated"
    assert t1_gen["starting_page"] == 3
    assert t1_gen["page_count"] >= 1
    assert os.path.isfile(t1_gen["pdf_path"])
    t1_page_count = t1_gen["page_count"]
    t1_original_hash = t1_gen["content_hash"]

    # 7. Create Task 2
    res = client.post(f"/practical-files/{pf_id}/tasks", json={
        "title": "DDL and DML Commands"
    })
    assert res.status_code == 201
    t2_id = res.json()["task"]["id"]

    # 8. Check Starting Page calculation for Task 2 (Cover=2 + Task1 pages)
    sp2_res = client.get(f"/tasks/{t2_id}/starting-page").json()
    assert sp2_res["computed_starting_page"] == 2 + t1_page_count + 1

    # 9. Paste Task 2 markdown (no placeholders)
    t2_markdown = """---
title: "Practical 2: DDL and DML Commands"
---

# Objective
Learn CREATE, ALTER, DROP, INSERT, and SELECT queries.

## Examples
```sql
CREATE TABLE Students (
    id INT PRIMARY KEY,
    name VARCHAR(50)
);
```
"""
    res = client.post(f"/tasks/{t2_id}/markdown", json={"raw_markdown": t2_markdown})
    assert res.status_code == 200

    # 10. Generate Task 2 PDF
    gen2_res = client.post(f"/tasks/{t2_id}/generate", json={})
    assert gen2_res.status_code == 200
    t2_gen = gen2_res.json()
    assert t2_gen["starting_page"] == 2 + t1_page_count + 1
    assert os.path.isfile(t2_gen["pdf_path"])

    # 11. Test Drift Detection: External Edit on Task 1 markdown file
    t1_md_path = Path(client.get(f"/tasks/{t1_id}").json()["markdown_path"])
    with open(t1_md_path, "a") as f:
        f.write("\n\n<!-- Hand edit outside app via Neovim -->\n")

    # Load tasks list: should detect hash mismatch and set 'edited outside app'
    tasks_res = client.get(f"/practical-files/{pf_id}/tasks").json()
    task1_updated = next(t for t in tasks_res if t["id"] == t1_id)
    assert task1_updated["needs_regeneration"] is True
    assert task1_updated["regeneration_reason"] == "edited outside app"

    # 13. Test Compilation Failure: Broken LaTeX syntax surfaces stderr without corrupting state
    res = client.post(f"/practical-files/{pf_id}/tasks", json={
        "title": "Broken Task Syntax"
    })
    t3_id = res.json()["task"]["id"]

    broken_md = """---
title: "Practical 3: Broken Syntax"
---

# Test
\\someNonExistentLaTeXCommandThatThrowsError{}
"""
    client.post(f"/tasks/{t3_id}/markdown", json={"raw_markdown": broken_md})
    fail_gen = client.post(f"/tasks/{t3_id}/generate", json={})
    assert fail_gen.status_code == 500
    assert len(fail_gen.json()["detail"]) > 0

    # Verify task 3 status was not corrupted to 'generated'
    t3_state = client.get(f"/tasks/{t3_id}").json()
    assert t3_state["status"] != "generated"
    assert t3_state["pdf_path"] is None

    # 14. Test D4: content_hash is stable across a page-only regeneration
    # Regenerate Task 2 with an explicit starting page override (e.g. 50)
    gen2_again = client.post(f"/tasks/{t2_id}/generate", json={"starting_page": 50})
    assert gen2_again.status_code == 200
    assert gen2_again.json()["starting_page"] == 50
    assert gen2_again.json()["content_hash"] == t2_gen["content_hash"]

    # Clean up
    app.dependency_overrides.clear()
