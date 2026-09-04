---
title: "Practical File Generator — MVP Design Spec"
date: "2026-08-17"
status: "Reviewed"
---

# Practical File Generator — MVP Design Spec

## Goal

Automate the existing manual pipeline for producing college practical-file PDFs:
LLM-drafted markdown → image placeholder resolution → pandoc+LaTeX build → correct
running page numbers across a subject's ordered tasks.

## Constraints

- No paid APIs or services (no image-search APIs, no hosted LLM calls from the app)
- MVP is **local-only** — no deployment, no accounts, no multi-user data sharing.
  Each classmate runs their own local copy. Hosting/sharing strategy is deferred
  until the app itself proves useful.
- Tech stack kept deliberately minimal: React frontend, FastAPI (Python) backend,
  SQLite as a lightweight index — not a database-first design.

## Tech Stack

- **Frontend**: React (Vite)
- **Backend**: FastAPI (Python), run locally via `uvicorn`, called from the
  frontend at `localhost`
- **Storage**: SQLite index only — actual content (markdown, images, PDFs) lives
  as real files on disk in the same folder layout already in use today, so the
  project stays hand-editable outside the app
- **PDF generation**: existing pandoc + LaTeX template, invoked as a subprocess
- **Packaging/deployment**: none for MVP. No Electron/Tauri wrapper yet — just
  run the two dev servers. Revisit packaging/hosting once the workflow itself is
  validated.

## Data Model (SQLite)

**`practical_files`**
- `id`
- `subject_name`
- `directory_path`
- `cover_page_count` (default `2`, editable — not hardcoded, so a subject with a
  different front-matter length still works)

**`tasks`**
- `id`
- `practical_file_id`
- `title`
- `order_index`
- `markdown_path`
- `assets_dir`
- `pdf_path`
- `page_count` (null until generated)
- `content_hash` (SHA-256 over the markdown file content + every file in
  `assets_dir`, sorted by filename for determinism; written when generation
  succeeds)
- `status`: `drafting` → `pasted` → `resolving_images` → `generated`
- `needs_regeneration` (bool) + `regeneration_reason` (`"starting page changed"` /
  `"edited outside app"`)

**`image_placeholders`**
- `id`
- `task_id`
- `position` (order within the document)
- `search_query` (the placeholder's alt text)
- `source_type`: `search` / `custom`
- `resolved_path`

## File Layout on Disk

Unchanged from the current manual workflow — SQLite just indexes it:

```
<practical-file>/
  assets/
    1-win-installation/
      image-01.png
      ...
  tasks/
    1-win-installation.md
    1-win-installation.pdf
```

## App Flow (per task)

1. **New task** — form for topic + instructions. Renders the user's input plus
   the fixed instruction block (plain technical English, no em dashes/AI-tells,
   frontmatter format, image-placeholder-with-search-query-as-alt-text
   convention) as copyable text. No LLM call happens in-app — the user pastes
   this into their own LLM chat of choice.
2. **Paste back & validate** — textarea for the returned markdown.
   `python-frontmatter` confirms the YAML block parses; a separator count check
   flags anything other than exactly two `---` lines (catches trailing LLM
   commentary the instructions tried to prevent). Errors surface inline with
   what's wrong, not a generic failure.
3. **Resolve images** — placeholders listed in document order, each showing its
   search-query alt text, with **Search online** (opens a Google Images tab for
   that query; paste the chosen image URL back — the backend downloads it
   server-side at generation time, avoiding browser CORS issues) or **Upload
   custom** (file picker, for cases like an Excel screenshot that must be a real
   image).
4. **Generate** — shows the computed starting page
   (`cover_page_count + sum of previous tasks' page_count` in this practical
   file; overridable). On confirm, the backend resolves images into
   `assets/<task-slug>/`, rewrites placeholder paths, inserts
   `\setcounter{page}{N}` after the frontmatter, shells out to pandoc, and reads
   the resulting PDF's page count back into `tasks.page_count`.

## Page Number Calculation & Drift Handling

Starting page for a task = `cover_page_count + sum(page_count for all earlier
tasks in the same practical_file, by order_index)`.

Editing an earlier task can change its page count, which invalidates every
later task's starting page. When a task is regenerated with a different
`page_count` than before, every later task in the same practical file is
flagged `needs_regeneration = true` (`"starting page changed"`) rather than
silently left stale.

## Content Integrity Check

On every task-list load, the backend re-hashes each task's markdown file plus
its assets directory and compares against the stored `content_hash`. A
mismatch sets `needs_regeneration = true` with reason `"edited outside app"` —
same flag/UI treatment as page-number drift, just a different displayed reason.
This catches hand-edits to the `.md` file or manually swapped/renamed images
done outside the app.

## Error Handling

- **Pandoc/LaTeX failure**: surface pandoc's actual stderr in the UI, not a
  generic "generation failed"
- **Dead/broken image URL**: per-placeholder retry; doesn't block resolving the
  others
- **Stale page numbers** (earlier task changed) and **stale content** (hash
  mismatch): both surface via the same `needs_regeneration` flag with a
  human-readable reason

## Explicitly Out of Scope for MVP

- Hosting, deployment, accounts, multi-user data sharing, cross-device sync
- Cover (title page) and index/TOC generation — handled by a separate existing
  tool (Next.js + Tectonic); this app only needs `cover_page_count` as a number
  for the page-number formula
- Merging per-task PDFs into one final practical-file PDF
- Any image-search API integration — manual Google Images link + paste-URL
  workflow only

## Future Todos (explicitly deferred, not designed yet)

- Task multi-select + "export merged PDF" using a CLI merge tool (e.g.
  `pdfmerge`/`pdftk`/`pdfunite`) across selected tasks
- Packaging as a Tauri/Electron app, if a shareable build turns out to be worth it
- Cross-device sync or export/import, if working from more than one machine
  becomes a real annoyance
