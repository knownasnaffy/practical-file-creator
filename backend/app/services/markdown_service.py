import re
import unicodedata
from typing import NamedTuple
import frontmatter


class ExtractedPlaceholder(NamedTuple):
    position: int
    search_query: str
    raw_match: str


class MarkdownValidationResult(NamedTuple):
    is_valid: bool
    title: str | None
    error_message: str | None
    placeholders: list[ExtractedPlaceholder]
    parsed_post: frontmatter.Post | None


# Regex to match markdown images: ![alt](url)
IMAGE_PATTERN = re.compile(r'!\[([^\]]*)\]\(([^)]*)\)')


def slugify(value: str, prefix: int | None = None) -> str:
    """Generate a clean filesystem slug from a title."""
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value.lower())
    slug = re.sub(r'[-\s]+', '-', value).strip('-')
    if not slug:
        slug = "task"
    if prefix is not None:
        return f"{prefix}-{slug}"
    return slug


def validate_and_parse_markdown(raw_markdown: str) -> MarkdownValidationResult:
    """
    Validates pasted markdown:
    1. Must parse with YAML frontmatter.
    2. Must contain 'title' in frontmatter.
    3. Must contain exactly two '---' separator lines (opening and closing frontmatter).
    4. Extracts all image placeholders in document order.
    """
    if not raw_markdown or not raw_markdown.strip():
        return MarkdownValidationResult(
            is_valid=False,
            title=None,
            error_message="Markdown content is empty.",
            placeholders=[],
            parsed_post=None,
        )

    # Check separator count: count lines that are exactly '---' or '---' with whitespace
    lines = [line.strip() for line in raw_markdown.splitlines()]
    separator_lines = [i for i, line in enumerate(lines) if line == '---']

    if len(separator_lines) < 2:
        return MarkdownValidationResult(
            is_valid=False,
            title=None,
            error_message="Missing YAML frontmatter delimiters. Markdown must start with '---' and close frontmatter with '---'.",
            placeholders=[],
            parsed_post=None,
        )

    if separator_lines[0] != 0:
        return MarkdownValidationResult(
            is_valid=False,
            title=None,
            error_message=f"YAML frontmatter must begin on the first line. Found leading content before '---' on line {separator_lines[0] + 1}.",
            placeholders=[],
            parsed_post=None,
        )

    if len(separator_lines) > 2:
        return MarkdownValidationResult(
            is_valid=False,
            title=None,
            error_message=(
                f"Found {len(separator_lines)} '---' delimiters (expected exactly 2). "
                "Do not use '---' horizontal rules between sections or trailing commentary."
            ),
            placeholders=[],
            parsed_post=None,
        )

    # Parse with python-frontmatter
    try:
        post = frontmatter.loads(raw_markdown)
    except Exception as exc:
        return MarkdownValidationResult(
            is_valid=False,
            title=None,
            error_message=f"YAML frontmatter parsing failed: {exc}",
            placeholders=[],
            parsed_post=None,
        )

    if not post.metadata or "title" not in post.metadata or not str(post.metadata["title"]).strip():
        return MarkdownValidationResult(
            is_valid=False,
            title=None,
            error_message="YAML frontmatter must include a non-empty 'title' field.",
            placeholders=[],
            parsed_post=None,
        )

    title = str(post.metadata["title"]).strip()

    # Extract placeholders from markdown body
    placeholders: list[ExtractedPlaceholder] = []
    matches = IMAGE_PATTERN.finditer(post.content)
    for idx, match in enumerate(matches, start=1):
        alt_text = match.group(1).strip()
        search_query = alt_text if alt_text else f"Image {idx}"
        placeholders.append(
            ExtractedPlaceholder(
                position=idx,
                search_query=search_query,
                raw_match=match.group(0),
            )
        )

    return MarkdownValidationResult(
        is_valid=True,
        title=title,
        error_message=None,
        placeholders=placeholders,
        parsed_post=post,
    )
