---
title: "Practical File Generator — Architecture & Implementation Plan"
date: "2026-08-17"
status: "Reviewed"
based_on: "./design_spec.md"
---

# Practical File Generator — Architecture & Implementation Plan

## 1. Context

The design spec already fixes the goal, tech stack, and data model: automate the
manual markdown-to-PDF pipeline for college practical files, running locally,
single user, no paid services. This document turns those decisions into a
concrete component architecture, request/data flow, API contract, and a phased
build plan. It also flags a handful of implementation details the spec leaves
implicit — these are called out as **Open Questions** at the end rather than
silently assumed.

## 2. Requirements

### Functional
- CRUD for practical files (subject) and their ordered tasks
- Generate a copy-paste instruction block per task (topic + fixed formatting
  rules) for use in an external LLM chat
- Validate pasted-back markdown (frontmatter parses, exactly two `---` lines)
- Resolve image placeholders via manual search-and-paste-URL or file upload
- Compute correct starting page per task and inject it into the LaTeX build
- Detect two kinds of staleness: page-number drift (earlier task's page count
  changed) and out-of-band edits (hash mismatch), and flag affected tasks
- Shell out to pandoc+LaTeX and surface real build errors

### Non-Functional
- Local-only: both servers run on `localhost`, no auth, no multi-user concerns
- No paid APIs or hosted LLM calls from the app itself
- Low operational overhead — SQLite is an index, not a system of record; files
  on disk stay hand-editable outside the app at any time
- Interactive-speed for a single user working through a handful of tasks per
  subject — no need to design for concurrency or scale

### Constraints (carried over from the spec)
- React (Vite) frontend, FastAPI (Python) backend via `uvicorn`
- SQLite index only, real content lives as files
- Existing pandoc + LaTeX template, invoked as a subprocess
- No packaging/deployment for MVP — two dev servers only

## 3. High-Level Architecture

```
┌──────────────────┐      HTTP (localhost)       ┌───────────────────────┐
│  React Frontend  │ ───────────────────────────▶ │   FastAPI Backend     │
│  (Vite, :5173)   │ ◀─────────────────────────── │   (uvicorn, :8000)    │
└──────────────────┘                              └───────────┬───────────┘
                                                                │
                      ┌─────────────────────────────────────────┼──────────────────────┐
                      ▼                                         ▼                      ▼
            ┌───────────────────┐                    ┌────────────────────┐  ┌──────────────────┐
            │  SQLite index.db  │                    │   Filesystem       │  │  pandoc + LaTeX   │
            │  practical_files  │                    │  <practical-file>/ │  │  subprocess       │
            │  tasks            │                    │    tasks/*.md      │  │  (per-task build) │
            │  image_placeholders│                   │    tasks/*.pdf     │  └──────────────────┘
            └───────────────────┘                    │    assets/*/*.png  │
                                                        └────────────────────┘

Manual, outside the app (not integrated):
  · User's own LLM chat        — paste instruction block in, paste markdown back
  · Browser tab → Google Images — pick an image, paste the URL back
```

SQLite and the filesystem are deliberately separate: the database is a
disposable index that can be rebuilt by re-scanning the folder layout; the
markdown, assets, and PDFs are the actual source of truth and stay editable
with any text editor or file browser.

## 4. Data Flow by Workflow Step

### 4.1 New task
`FE → POST /practical-files/{id}/tasks {title}`
Backend inserts a `tasks` row (`status = drafting`, `order_index = max + 1`)
and returns the rendered instruction block (topic + fixed formatting rules) as
plain text for the user to copy into their own LLM chat. No LLM call happens
in the app.

### 4.2 Paste back & validate
`FE → POST /tasks/{id}/markdown {raw_markdown}`
Backend runs `python-frontmatter` to parse the YAML block, checks for exactly
two `---` separators, and on success writes `tasks/<slug>.md`, scans the body
for image placeholders, and inserts one `image_placeholders` row per
placeholder (in document order). Status moves to `pasted`, then
`resolving_images` if any placeholders exist. Validation errors return the
specific problem (missing frontmatter field, wrong separator count, etc.), not
a generic failure.

### 4.3 Resolve images
`FE → GET /tasks/{id}/placeholders` — list in document order.
Per placeholder, two paths:
- **Search online**: the frontend opens a new tab to a Google Images search
  built from `search_query` — this is client-side only, no backend call. The
  user pastes the chosen image URL back via
  `PATCH /placeholders/{id} {source_value: url}` (`source_type = search`).
  Nothing is downloaded yet.
- **Upload custom**: `POST /placeholders/{id}/upload` (multipart file) stores
  the file in a temp location and sets `source_type = custom`.

Actual download of `search` URLs happens later, server-side, at generation
time — this is the spec's explicit choice to avoid browser CORS issues.

### 4.4 Generate
`FE → GET /tasks/{id}/starting-page` returns the computed
`cover_page_count + Σ(page_count of earlier tasks)`, overridable by the user.
`FE → POST /tasks/{id}/generate {starting_page?}` then:
1. For each placeholder: download the `search` URL or move the uploaded file
   into `assets/<task-slug>/image-NN.<ext>`; set `resolved_path`.
2. Rewrite the markdown's placeholder references to the resolved local paths,
   writing the result to a **temp build copy** — the original `tasks/<slug>.md`
   is not mutated with the page-number directive (see §9, decision D4).
3. Insert `\setcounter{page}{N}` after the frontmatter in the temp copy.
4. Shell out to pandoc on the temp copy.
5. On success: copy the resulting PDF to `tasks/<slug>.pdf`, read its page
   count back, update `tasks.page_count`, `status = generated`, and recompute
   `content_hash` over the markdown + assets dir.
6. If the new `page_count` differs from the previous value, set
   `needs_regeneration = true, regeneration_reason = "starting page changed"`
   on every later task (`order_index >` this one) in the same practical file.
7. On pandoc failure: return stderr verbatim, leave the task's prior state
   (PDF, page_count, status) untouched — no partial/broken PDF is ever written
   over a good one.

### 4.5 Load-time integrity check
`FE → GET /practical-files/{id}/tasks`
Backend re-hashes each task's markdown file plus its assets directory
(sorted filenames, SHA-256) and compares to the stored `content_hash`. A
mismatch sets `needs_regeneration = true, regeneration_reason = "edited outside app"`
unless the task is already flagged for the page-drift reason. Both reasons
render through the same UI badge, just with different text.

## 5. API Design

| Method | Path | Purpose |
|---|---|---|
| POST | `/practical-files` | Create a practical file (`subject_name`, `directory_path`, `cover_page_count?`) |
| GET | `/practical-files` | List practical files |
| GET | `/practical-files/{id}` | Get one, with its tasks |
| PATCH | `/practical-files/{id}` | Update `cover_page_count` (cascades like a page-count change, §4.4 step 6) |
| POST | `/practical-files/{id}/tasks` | Create a task; returns the task + rendered instruction block |
| GET | `/practical-files/{id}/tasks` | List tasks in order; runs the integrity check (§4.5) and returns live `needs_regeneration` flags |
| PATCH | `/practical-files/{id}/tasks/reorder` | Reorder tasks (see Open Questions — not detailed in the spec) |
| GET | `/tasks/{id}` | Task detail |
| POST | `/tasks/{id}/markdown` | Validate + store pasted-back markdown (§4.2) |
| GET | `/tasks/{id}/placeholders` | List image placeholders in document order |
| PATCH | `/placeholders/{id}` | Set `source_value` for a `search`-type placeholder |
| POST | `/placeholders/{id}/upload` | Multipart upload for a `custom`-type placeholder |
| POST | `/placeholders/{id}/retry` | Re-attempt a failed download without blocking the rest |
| GET | `/tasks/{id}/starting-page` | Computed starting page preview |
| POST | `/tasks/{id}/generate` | Run the full generation pipeline (§4.4) |

All routes are unauthenticated — this is a local, single-user tool.

## 6. Data Model (SQLite Schema)

The spec's data model is carried over directly, with two additions marked
`-- added`: a `source_value` column to hold the pasted URL or uploaded
filename before it becomes a `resolved_path`, and standard indices/constraints
for integrity.

```sql
CREATE TABLE practical_files (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_name      TEXT NOT NULL,
    directory_path    TEXT NOT NULL UNIQUE,
    cover_page_count  INTEGER NOT NULL DEFAULT 2,
    created_at        TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE tasks (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    practical_file_id     INTEGER NOT NULL REFERENCES practical_files(id) ON DELETE CASCADE,
    title                 TEXT NOT NULL,
    order_index           INTEGER NOT NULL,
    markdown_path         TEXT,
    assets_dir            TEXT,
    pdf_path              TEXT,
    page_count            INTEGER,
    content_hash          TEXT,
    status                TEXT NOT NULL DEFAULT 'drafting'
                          CHECK (status IN ('drafting','pasted','resolving_images','generated')),
    needs_regeneration    INTEGER NOT NULL DEFAULT 0,  -- SQLite has no bool; 0/1
    regeneration_reason   TEXT
                          CHECK (regeneration_reason IN ('starting page changed','edited outside app')
                                 OR regeneration_reason IS NULL),
    UNIQUE (practical_file_id, order_index)
);

CREATE TABLE image_placeholders (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id        INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    position       INTEGER NOT NULL,
    search_query   TEXT NOT NULL,
    source_type    TEXT NOT NULL DEFAULT 'search' CHECK (source_type IN ('search','custom')),
    source_value   TEXT,     -- added: pasted URL, or original uploaded filename
    resolved_path  TEXT,     -- final local asset path, set at generation time
    UNIQUE (task_id, position)
);

CREATE INDEX idx_tasks_practical_file   ON tasks(practical_file_id, order_index);
CREATE INDEX idx_placeholders_task      ON image_placeholders(task_id, position);
```

`ON DELETE CASCADE` requires `PRAGMA foreign_keys = ON` per SQLite connection —
easy to forget, worth a startup-time assertion in the backend.

## 7. Backend Component Breakdown (FastAPI)

```
app/
  main.py                    # app factory, CORS for localhost:5173, router mounts
  db.py                      # sqlite3 connection, PRAGMA foreign_keys=ON, migrations
  models.py                  # Pydantic request/response schemas
  routers/
    practical_files.py
    tasks.py
    placeholders.py
  services/
    markdown_service.py      # frontmatter parse/validate, placeholder extraction
    image_service.py         # URL download, upload handling, asset path assignment
    pdf_service.py            # temp-file page-number injection, pandoc invocation,
                              #   page-count read-back (pypdf)
    hash_service.py          # SHA-256 over markdown + sorted assets dir
    page_service.py          # starting-page calc, cascade invalidation on change
```

Each service is a plain module of functions, not a class hierarchy — there's
no state to manage beyond the SQLite connection and the filesystem, so
dependency injection beyond FastAPI's `Depends(get_db)` isn't needed.

## 8. Frontend Component Breakdown (React + Vite)

```
src/
  api/
    client.js                # fetch wrapper against localhost:8000
  pages/
    PracticalFileList.jsx
    TaskList.jsx              # shows RegenerationBadge per task
    TaskWorkflow.jsx          # the 4-step flow: draft → paste → resolve → generate
  components/
    InstructionBlock.jsx      # copyable instruction text
    MarkdownPasteForm.jsx     # textarea + inline validation errors
    PlaceholderList.jsx
    PlaceholderRow.jsx        # "Search online" / "Upload custom" / retry
    GeneratePanel.jsx         # starting-page preview + override + generate button
    RegenerationBadge.jsx     # renders needs_regeneration + reason
```

Given the app's size (single user, a handful of screens), plain
`fetch` + `useState`/`useEffect` is enough — a data-fetching library like React
Query is optional polish, not a requirement, since there's no cache-sharing
across many components that would justify it.

## 9. Key Design Decisions

**D1 — SQLite is an index, not the source of truth.**
Content stays as real files on disk, matching the existing manual workflow.
*Trade-off*: the backend must re-derive/re-hash rather than trust the DB
blindly (see §4.5), but the project stays hand-editable and the DB can be
deleted and rebuilt by re-scanning the folder layout.

**D2 — Drift detection is hash-on-load, not a filesystem watcher.**
Simpler to implement and reason about for a single-user local tool; avoids the
platform-specific quirks of file-watching libraries. *Trade-off*: a task
edited outside the app won't show as stale until its task list is next loaded
— acceptable here since generation is always a manual, explicit action.

**D3 — Staleness is a flag, not an automatic rebuild.**
`needs_regeneration` is surfaced, never acted on automatically. *Trade-off*:
one extra click per stale task, but it keeps PDF generation (which can fail
and takes real time) fully under user control.

**D4 — The starting-page directive is injected into a temp build copy, never
persisted into the source `.md`.**
This is an addition beyond what the spec states explicitly, needed to keep
`content_hash` stable: if `\setcounter{page}{N}` were written into
`tasks/<slug>.md` itself, every regeneration triggered purely by an earlier
task's page-count change would also look like a content edit, muddying the two
`needs_regeneration` reasons together.

**D5 — No image-search API; manual browser tab + paste-URL.**
Matches the "no paid APIs" constraint directly. *Trade-off*: an extra manual
step per image, acceptable at the scale of a few images per task.

## 10. Error Handling Matrix

| Scenario | Detection | User-facing behavior | HTTP status |
|---|---|---|---|
| Frontmatter fails to parse | `python-frontmatter` raises | Inline error naming the parse problem | 422 |
| Wrong `---` separator count | Count check post-parse | Inline error, likely cause named (trailing LLM commentary) | 422 |
| Dead/broken image URL | Download fails at generate time | That placeholder marked failed; retry available; others unaffected | 200 (partial), placeholder-level error field |
| Pandoc/LaTeX build failure | Non-zero subprocess exit | Raw stderr shown in UI, prior PDF/state untouched | 500 with stderr in body |
| Directory path collision | UNIQUE constraint on `directory_path` | "Practical file already exists at this path" | 409 |
| Task reorder produces duplicate `order_index` | UNIQUE constraint on `(practical_file_id, order_index)` | Reject, no partial write | 409 |

## 11. Implementation Plan

**Phase 0 — Scaffolding**
- [ ] FastAPI + uvicorn skeleton, Vite + React skeleton
- [ ] SQLite schema migration script (§6), `PRAGMA foreign_keys=ON` verified
- [ ] CORS configured for `localhost:5173` → `localhost:8000`

**Phase 1 — Practical files & tasks (CRUD + instruction block)**
- [ ] `practical_files` and `tasks` endpoints
- [ ] Instruction-block template rendering (topic + fixed rules, copyable)

**Phase 2 — Paste-back & validation**
- [ ] `markdown_service`: frontmatter parse, separator count check
- [ ] Placeholder extraction from markdown body, `image_placeholders` rows

**Phase 3 — Image resolution**
- [ ] `PATCH /placeholders/{id}` for pasted URLs
- [ ] `POST /placeholders/{id}/upload` for custom files
- [ ] Retry endpoint for failed downloads

**Phase 4 — PDF generation pipeline**
- [ ] `image_service`: server-side download + asset placement at generate time
- [ ] `pdf_service`: temp-copy page-number injection (D4), pandoc invocation,
      page-count read-back
- [ ] Failure path: stderr surfaced, no state mutated on error

**Phase 5 — Page-number cascade & drift detection**
- [ ] `page_service`: starting-page calc + cascade `needs_regeneration` on
      page-count change
- [ ] `hash_service`: SHA-256 over markdown + sorted assets, load-time check

**Phase 6 — Polish**
- [ ] Inline, specific validation/error messages throughout (no generic
      failures — this is a spec requirement, not a nice-to-have)
- [ ] `RegenerationBadge` reason text wired to both drift causes

## 12. Consequences

**Easier:** hand-editing files outside the app stays fully safe (D1, D2);
adding a new task type or tweaking the instruction template doesn't touch the
DB schema; the DB can be wiped and rebuilt without data loss.

**Harder:** anything that wants "live" staleness detection (e.g., a watcher
that flags an edit the moment it happens) needs a different design than D2;
reordering tasks needs care to keep `order_index` and the page-number cascade
consistent (see Open Questions).

**Revisit when:** the spec's own "Future Todos" become relevant — merged-PDF
export, Tauri/Electron packaging, or cross-device sync would each push against
the "SQLite as disposable index" and "no packaging" decisions made here.

## Open Questions / Assumptions

These aren't resolved by the spec and are assumed for this plan — flag any
that should go the other way:

1. **Image placeholder syntax** — assumed to be standard markdown image syntax
   with the search query as alt text, e.g. `![install wizard screenshot](placeholder)`.
2. **Task reordering** — the spec's data model has `order_index` but the app
   flow doesn't describe a reorder UI. Included here as a stub endpoint
   (§5); confirm whether MVP actually needs it or tasks are just created in
   final order.
3. **PDF page-count read-back** — assumed `pypdf` (pure Python, no system
   dependency beyond what LaTeX already needs) rather than shelling out to
   `pdfinfo`.
4. **Cover-page-count edits** — assumed a `PATCH` on `cover_page_count`
   cascades `needs_regeneration` the same way a page-count change does, since
   it feeds the same formula. Not explicit in the spec.

## Review

Closing open questions:

1. Image placeholders should use standard markdown image syntax `![]()`
2. Addition order as default and a simple right click context menu with move up and down options.
3. pypdf it is.
4. true, cover_page_count changes should trigger needs_regeneration.
