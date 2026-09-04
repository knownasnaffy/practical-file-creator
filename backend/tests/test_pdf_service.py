from pathlib import Path
import pytest
from app.services.pdf_service import (
    PdfBuildError,
    inject_starting_page_directive,
    rewrite_markdown_placeholders,
)


def test_inject_starting_page_directive():
    md = """---
title: "SQL Practical"
---

# Content Here
"""
    result = inject_starting_page_directive(md, starting_page=5)
    assert "\\setcounter{page}{5}" in result
    assert result.index("title: \"SQL Practical\"") < result.index("\\setcounter{page}{5}") < result.index("# Content Here")


def test_rewrite_markdown_placeholders(tmp_path):
    md = """# Intro
![Screenshot 1](placeholder_1)

Some text

![Screenshot 2](placeholder_2)
"""
    temp_build_dir = tmp_path / "build"
    temp_build_dir.mkdir()
    resolved_map = {
        1: str(temp_build_dir / "assets" / "image-01.png"),
        2: str(temp_build_dir / "assets" / "image-02.png"),
    }
    rewritten = rewrite_markdown_placeholders(md, resolved_map, temp_build_dir)
    assert "![Screenshot 1](assets/image-01.png)" in rewritten
    assert "![Screenshot 2](assets/image-02.png)" in rewritten
