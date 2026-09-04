from app.services.markdown_service import (
    slugify,
    validate_and_parse_markdown,
)


def test_slugify():
    slug = slugify("Introduction to SQL and installation of SQL Server / Oracle", prefix=1)
    assert slug == "1-introduction-to-sql-and-installation-of-sql-server-oracle"


def test_valid_markdown_parsing():
    sample_md = """---
title: "Practical 1: SQL Server Installation"
---

# Introduction
SQL is a domain-specific language.

<!-- Screenshot of installation wizard -->
![SQL Server Installation Wizard](placeholder_1)

## Verification
Run SELECT 1; to verify.

![SQL Server Management Studio Query Output](placeholder_2)
"""
    result = validate_and_parse_markdown(sample_md)
    assert result.is_valid is True
    assert result.title == "Practical 1: SQL Server Installation"
    assert len(result.placeholders) == 2
    assert result.placeholders[0].position == 1
    assert result.placeholders[0].search_query == "SQL Server Installation Wizard"
    assert result.placeholders[1].position == 2
    assert result.placeholders[1].search_query == "SQL Server Management Studio Query Output"


def test_invalid_markdown_extra_separators():
    sample_md = """---
title: "Practical 1"
---

# Introduction
Some content here.

---

## Next Section
More content here.
"""
    result = validate_and_parse_markdown(sample_md)
    assert result.is_valid is False
    assert "Found 3 '---' delimiters" in result.error_message


def test_invalid_markdown_missing_frontmatter():
    sample_md = """# Introduction
No frontmatter at all.
"""
    result = validate_and_parse_markdown(sample_md)
    assert result.is_valid is False
    assert "Missing YAML frontmatter" in result.error_message


def test_invalid_markdown_missing_title():
    sample_md = """---
author: "Student"
---

# Content
"""
    result = validate_and_parse_markdown(sample_md)
    assert result.is_valid is False
    assert "must include a non-empty 'title' field" in result.error_message
