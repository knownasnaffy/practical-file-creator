import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
import sqlite3
from typing import NamedTuple, Optional
from pypdf import PdfReader

from app.config import PANDOC_CONTAINER_ENGINE, PANDOC_IMAGE, PANDOC_TEMPLATE
from app.services.hash_service import compute_task_content_hash
from app.services.image_service import download_image, save_uploaded_image
from app.services.page_service import calculate_starting_page, cascade_page_drift_on_task_update


class PdfBuildResult(NamedTuple):
    pdf_path: str
    page_count: int
    starting_page: int
    content_hash: str
    stderr: Optional[str] = None


class PdfBuildError(Exception):
    def __init__(self, message: str, stderr: Optional[str] = None):
        super().__init__(message)
        self.stderr = stderr


def inject_starting_page_directive(markdown_content: str, starting_page: int) -> str:
    r"""
    Injects `\setcounter{page}{N}` immediately after the frontmatter closing `---`.
    If no frontmatter is found, prepends it to the document.
    """
    lines = markdown_content.splitlines(keepends=True)
    separator_indices = [i for i, line in enumerate(lines) if line.strip() == '---']

    directive = f"\n\\setcounter{{page}}{{{starting_page}}}\n\n"

    if len(separator_indices) >= 2:
        close_idx = separator_indices[1]
        lines.insert(close_idx + 1, directive)
        return "".join(lines)
    else:
        return directive + markdown_content


def resolve_task_assets(conn: sqlite3.Connection, task_id: int, assets_dir: Path) -> dict[int, str]:
    """
    Downloads or copies all pending placeholder assets into assets_dir (image-01.ext, image-02.ext, etc.)
    and updates resolved_path in database.
    Returns mapping of placeholder position -> canonical asset path on disk.
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, position, search_query, source_type, source_value, resolved_path
        FROM image_placeholders
        WHERE task_id = ?
        ORDER BY position ASC
    """, (task_id,))
    placeholders = cursor.fetchall()

    resolved_map: dict[int, str] = {}
    assets_dir.mkdir(parents=True, exist_ok=True)

    for ph in placeholders:
        pos = ph["position"]
        pos_str = f"image-{pos:02d}"
        source_type = ph["source_type"]
        source_value = ph["source_value"]
        current_resolved = ph["resolved_path"]

        # 1. If resolved_path exists on disk, ensure it is copied into task's assets_dir
        if current_resolved and Path(current_resolved).is_file():
            resolved_file = Path(current_resolved)
            ext = resolved_file.suffix or ".png"
            dest_file = assets_dir / f"{pos_str}{ext}"
            if resolved_file.resolve() != dest_file.resolve():
                shutil.copy2(resolved_file, dest_file)
                cursor.execute("""
                    UPDATE image_placeholders
                    SET resolved_path = ?
                    WHERE id = ?
                """, (str(dest_file), ph["id"]))
            resolved_map[pos] = str(dest_file)
            continue

        if not source_value:
            # Placeholder has not been resolved by user
            continue

        if source_type == "search":
            # source_value is URL
            try:
                dest_template = assets_dir / f"{pos_str}.png"
                saved_file = download_image(source_value, dest_template)
                cursor.execute("""
                    UPDATE image_placeholders
                    SET resolved_path = ?
                    WHERE id = ?
                """, (str(saved_file), ph["id"]))
                resolved_map[pos] = str(saved_file)
            except Exception as exc:
                raise PdfBuildError(
                    f"Failed to download image for placeholder #{pos} ({ph['search_query']}): {exc}"
                )
        elif source_type == "custom":
            # source_value points to uploaded / pasted file
            uploaded_tmp = Path(source_value)
            if uploaded_tmp.is_file():
                ext = uploaded_tmp.suffix or ".png"
                dest_file = assets_dir / f"{pos_str}{ext}"
                shutil.copy2(uploaded_tmp, dest_file)
                cursor.execute("""
                    UPDATE image_placeholders
                    SET resolved_path = ?
                    WHERE id = ?
                """, (str(dest_file), ph["id"]))
                resolved_map[pos] = str(dest_file)
            elif Path(source_value).is_absolute() and Path(source_value).is_file():
                ext = Path(source_value).suffix or ".png"
                dest_file = assets_dir / f"{pos_str}{ext}"
                shutil.copy2(Path(source_value), dest_file)
                cursor.execute("""
                    UPDATE image_placeholders
                    SET resolved_path = ?
                    WHERE id = ?
                """, (str(dest_file), ph["id"]))
                resolved_map[pos] = str(dest_file)

    return resolved_map


def rewrite_markdown_placeholders(
    markdown_content: str,
    resolved_map: dict[int, str],
    temp_build_dir: Optional[Path] = None,
    slug: Optional[str] = None
) -> str:
    """
    Replaces each ![alt](url_or_placeholder) in document order with its resolved asset relative path inside temp build dir.
    Guarantees container-local relative path so Pandoc in container (/data) can always load it.
    """
    pattern = re.compile(r'!\[([^\]]*)\]\(([^)]*)\)')
    counter = 0

    def replacer(match: re.Match) -> str:
        nonlocal counter
        counter += 1
        alt = match.group(1)
        if counter in resolved_map:
            resolved_abs = Path(resolved_map[counter])
            filename = resolved_abs.name
            if slug:
                rel_path = f"assets/{slug}/{filename}"
            elif temp_build_dir:
                try:
                    rel = os.path.relpath(resolved_abs, temp_build_dir)
                    if not rel.startswith(".."):
                        rel_path = rel
                    else:
                        rel_path = f"assets/{filename}"
                except ValueError:
                    rel_path = f"assets/{filename}"
            else:
                rel_path = f"assets/{filename}"
            return f"![{alt}]({rel_path})"
        return match.group(0)

    return pattern.sub(replacer, markdown_content)


def run_pandoc_build(
    temp_dir: Path,
    input_md_name: str,
    output_pdf_name: str,
    template: str = PANDOC_TEMPLATE,
    resource_paths: Optional[list[str]] = None,
) -> str:
    """
    Runs pandoc via Podman container (with fallback to local pandoc if available).
    Returns stdout if successful, raises PdfBuildError with stderr on failure.
    """
    use_podman = shutil.which(PANDOC_CONTAINER_ENGINE) is not None
    use_local_pandoc = shutil.which("pandoc") is not None

    r_path = ":".join(resource_paths) if resource_paths else ".:assets"

    if use_podman:
        cmd = [
            PANDOC_CONTAINER_ENGINE,
            "run",
            "--rm",
            "--volume",
            f"{temp_dir}:/data:z",
            PANDOC_IMAGE,
            input_md_name,
            "-o",
            output_pdf_name,
            "--from",
            "markdown",
            "--template",
            template,
            "--resource-path",
            r_path,
        ]
    elif use_local_pandoc:
        cmd = [
            "pandoc",
            input_md_name,
            "-o",
            output_pdf_name,
            "--from",
            "markdown",
            "--template",
            template,
            "--resource-path",
            r_path,
        ]
    else:
        raise PdfBuildError("Neither podman nor pandoc is installed on the system.")

    try:
        proc = subprocess.run(
            cmd,
            cwd=str(temp_dir),
            capture_output=True,
            text=True,
            timeout=120
        )
    except subprocess.TimeoutExpired:
        raise PdfBuildError("PDF compilation timed out after 120 seconds.")
    except Exception as exc:
        raise PdfBuildError(f"Failed to execute PDF compilation process: {exc}")

    if proc.returncode != 0:
        err_msg = proc.stderr.strip() or proc.stdout.strip() or f"Process exited with code {proc.returncode}"
        raise PdfBuildError(f"Pandoc compilation failed:\n{err_msg}", stderr=err_msg)

    return proc.stdout


def generate_task_pdf(
    conn: sqlite3.Connection,
    task_id: int,
    starting_page_override: Optional[int] = None
) -> PdfBuildResult:
    r"""
    Full generation pipeline (Phase 4 & 5):
    1. Reads task and practical_file records.
    2. Resolves assets into <practical-file>/assets/<task-slug>/.
    3. Computes starting page number.
    4. Prepares temp build copy with \setcounter{page}{N} and rewritten asset paths.
    5. Compiles PDF via pandoc.
    6. On success: copies PDF, reads page count with pypdf, triggers cascade if page count changed,
       updates content_hash and status='generated'.
    7. On error: leaves prior state untouched, raises PdfBuildError with stderr.
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT t.*, pf.directory_path, pf.cover_page_count
        FROM tasks t
        JOIN practical_files pf ON t.practical_file_id = pf.id
        WHERE t.id = ?
    """, (task_id,))
    task = cursor.fetchone()
    if not task:
        raise ValueError(f"Task {task_id} not found")

    pf_dir = Path(task["directory_path"])
    markdown_path = Path(task["markdown_path"]) if task["markdown_path"] else None
    if not markdown_path or not markdown_path.is_file():
        raise ValueError(f"Task markdown file not found at {markdown_path}")

    with open(markdown_path, "r", encoding="utf-8") as f:
        source_markdown = f.read()

    # Determine assets directory
    slug = markdown_path.stem
    assets_dir = Path(task["assets_dir"]) if task["assets_dir"] else pf_dir / "assets" / slug

    # 1. Resolve placeholder assets
    resolved_map = resolve_task_assets(conn, task_id, assets_dir)

    # 2. Determine starting page
    if starting_page_override is not None and starting_page_override >= 1:
        starting_page = starting_page_override
    else:
        page_info = calculate_starting_page(conn, task_id)
        starting_page = page_info.computed_starting_page

    # 3. Create temp build directory (D4 - isolation)
    with tempfile.TemporaryDirectory(prefix=f"pfc_build_{slug}_") as temp_dir_str:
        temp_dir = Path(temp_dir_str)

        # Copy assets folder into temp_dir so relative links work inside container
        temp_assets_slug_dir = temp_dir / "assets" / slug
        temp_assets_slug_dir.mkdir(parents=True, exist_ok=True)
        temp_assets_dir = temp_dir / "assets"
        temp_assets_dir.mkdir(parents=True, exist_ok=True)

        for pos, abs_path_str in resolved_map.items():
            src_file = Path(abs_path_str)
            if src_file.is_file():
                # Copy to temp_dir/assets/<slug>/<filename>
                shutil.copy2(src_file, temp_assets_slug_dir / src_file.name)
                # Copy to temp_dir/assets/<filename>
                shutil.copy2(src_file, temp_assets_dir / src_file.name)
                # Copy to temp_dir/<filename>
                shutil.copy2(src_file, temp_dir / src_file.name)

        # Rewrite placeholder paths to container-local relative paths
        transformed_md = rewrite_markdown_placeholders(source_markdown, resolved_map, temp_dir, slug=slug)

        # Inject starting page directive
        final_temp_md = inject_starting_page_directive(transformed_md, starting_page)

        temp_md_path = temp_dir / f"{slug}.md"
        with open(temp_md_path, "w", encoding="utf-8") as f:
            f.write(final_temp_md)

        temp_pdf_name = f"{slug}.pdf"
        temp_pdf_path = temp_dir / temp_pdf_name

        # 4. Shell out to pandoc with resource paths
        run_pandoc_build(
            temp_dir,
            f"{slug}.md",
            temp_pdf_name,
            resource_paths=[".", "assets", f"assets/{slug}"]
        )

        if not temp_pdf_path.is_file():
            raise PdfBuildError("Pandoc finished but output PDF was not created.")

        # 5. Read back page count using pypdf
        try:
            reader = PdfReader(str(temp_pdf_path))
            new_page_count = len(reader.pages)
        except Exception as exc:
            raise PdfBuildError(f"Failed to read page count from generated PDF: {exc}")

        # 6. Copy final PDF to destination
        final_tasks_dir = pf_dir / "tasks"
        final_tasks_dir.mkdir(parents=True, exist_ok=True)
        final_pdf_path = final_tasks_dir / f"{slug}.pdf"
        shutil.copy2(temp_pdf_path, final_pdf_path)

        # 7. Compute deterministic content hash
        content_hash = compute_task_content_hash(markdown_path, assets_dir)

        # 8. Check for page-count change and trigger cascade
        old_page_count = task["page_count"]
        was_generated = task["status"] == "generated"

        if was_generated and old_page_count is not None and old_page_count != new_page_count:
            cascade_page_drift_on_task_update(conn, task["practical_file_id"], task["order_index"])

        # 9. Update task record in DB
        cursor.execute("""
            UPDATE tasks
            SET pdf_path = ?,
                page_count = ?,
                content_hash = ?,
                status = 'generated',
                needs_regeneration = 0,
                regeneration_reason = NULL,
                assets_dir = ?
            WHERE id = ?
        """, (str(final_pdf_path), new_page_count, content_hash, str(assets_dir), task_id))

        return PdfBuildResult(
            pdf_path=str(final_pdf_path),
            page_count=new_page_count,
            starting_page=starting_page,
            content_hash=content_hash,
            stderr=None
        )
