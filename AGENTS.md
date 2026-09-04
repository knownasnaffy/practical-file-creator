# Agent Development Guide for Practical File Creator (PFC-v2)

This document provides a concise, complete onboarding guide for AI agents and human contributors working on this repository. Read this file first when tasked with a bug fix, feature request, refactor, or test improvement.

---

## 1. Project Overview and Philosophy

Practical File Creator (PFC-v2) is a local-first web tool designed to generate clean, academic-grade lab record PDFs from Markdown files. It uses an external LLM workflow without requiring paid API keys or hosted models.

### Key Tenets
1. **Oneshot Prompt Workflow**: The app generates a structured prompt for the user to paste into their own external LLM (such as ChatGPT, Claude, or Gemini). The user pastes the generated Markdown back into the app.
2. **Filesystem as Source of Truth**: Markdown files, image assets, and compiled PDFs live directly in the directory path chosen by the user. The SQLite database (`backend/index.db`) serves as a disposable index and cache, not an opaque black box.
3. **Containerized Document Pipeline**: Pandoc runs inside an isolated container (`docker.io/pandoc/extra` with the `eisvogel` LaTeX template) using Podman or Docker. No local TeX Live installation is required on the host system.
4. **Deterministic Page Numbering (The Cascade Rule)**: Laboratory records require unbroken page numbering across multiple sequential tasks. The system tracks starting page offsets, detects page-drift when earlier tasks grow or shrink, and flags downstream tasks for regeneration.

---

## 2. Technology Stack

- **Backend**: Python 3.11+, FastAPI, Uvicorn, SQLite3 (standard library), Pydantic v2, `python-frontmatter`, `pypdf`, `httpx`, `python-multipart`.
- **Frontend**: React 19, Vite 8, Tailwind CSS v4 (`@tailwindcss/vite`), Lucide React.
- **Document Engine**: Podman or Docker running `docker.io/pandoc/extra` with `--template eisvogel`.
- **Test Runner**: Pytest (`backend/tests`), Oxlint (`frontend`).

---

## 3. Directory Map and Responsibilities

Use this map to locate the relevant code without scanning unnecessary files.

```
pfc-v2/
├── AGENTS.md                                # This onboarding guide
├── README.md                                # User-facing setup and usage guide
├── .gitignore                               # Git ignore rules for Python, Node, DB, and builds
├── docs/
│   ├── architecture.md                      # Detailed technical architecture spec
│   ├── design_spec.md                       # Initial domain model and requirements
│   └── sprint.md                            # Original MVP sprint plan
├── backend/
│   ├── pyproject.toml                       # Python dependencies and pytest configuration
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py                        # Configuration defaults (engine, image, DB path, prompt)
│   │   ├── db.py                            # SQLite connection factory, WAL mode, foreign keys, schema
│   │   ├── main.py                          # FastAPI app entry point, CORS, router mounting
│   │   ├── models.py                        # Pydantic request/response schemas
│   │   ├── routers/
│   │   │   ├── practical_files.py           # Practical file CRUD, multi-task compilation (/build-pdf)
│   │   │   ├── tasks.py                     # Task CRUD, prompt generation, markdown upload, reordering
│   │   │   └── placeholders.py              # Placeholder resolution (upload, URL patch, image serving)
│   │   └── services/
│   │       ├── hash_service.py              # SHA-256 integrity hashing (markdown + assets)
│   │       ├── image_service.py             # MIME type detection, extension normalization, file storage
│   │       ├── instruction_service.py       # LLM prompt block rendering
│   │       ├── markdown_service.py          # Frontmatter validation, placeholder extraction, slugify
│   │       ├── page_service.py              # PDF page count extraction via pypdf, cumulative start pages
│   │       └── pdf_service.py               # Container execution (Podman/Docker), asset staging, LaTeX offsets
│   └── tests/
│       ├── conftest.py                      # Temporary DB and test fixtures
│       ├── test_api.py                      # FastAPI endpoint integration tests
│       ├── test_db.py                       # SQLite schema and foreign key constraint tests
│       ├── test_e2e_pandoc.py               # End-to-end containerized PDF generation test
│       ├── test_hash_service.py             # Content hash and drift detection tests
│       ├── test_instruction_service.py      # Prompt generator formatting tests
│       ├── test_markdown_service.py         # Markdown parsing and placeholder extraction tests
│       ├── test_page_service.py             # Page counting and cascade shift tests
│       └── test_pdf_service.py              # Markdown rewriting and page directive injection tests
└── frontend/
    ├── index.html                           # Single page HTML entry
    ├── package.json                         # Node dependencies and scripts
    ├── vite.config.js                       # Vite configuration and backend API proxy (/api -> :8000)
    └── src/
        ├── App.jsx                          # Root view switcher (FileList <-> TaskList <-> TaskWorkflow)
        ├── main.jsx                         # React entry point
        ├── api/
        │   └── client.js                    # API client talking to backend endpoints
        ├── pages/
        │   ├── PracticalFileList.jsx        # Practical file directory list and creation modal
        │   ├── TaskList.jsx                 # Task list, page numbers, cascade drift alert, compile action
        │   └── TaskWorkflow.jsx             # 4-step task wizard (Prompt, Markdown, Images, Preview)
        └── components/
            ├── GeneratePanel.jsx            # Single-task PDF compile modal and log viewer
            ├── InstructionBlock.jsx         # Copyable prompt block component
            ├── MarkdownPasteForm.jsx        # Markdown input editor with validation feedback
            ├── PlaceholderList.jsx          # Placeholder list container
            ├── PlaceholderRow.jsx           # Image resolver row (File upload, URL paste, raw image paste)
            └── RegenerationBadge.jsx        # Status badge for page drift or external edits
```

---

## 4. Core System Invariants (Do Not Break)

When making any modification, you must preserve these architectural rules:

### 1. The Page Cascade Invariant
A practical file consists of ordered tasks (`order_index = 1, 2, ...`).
- Starting page formula:
  `starting_page = 1 + cover_page_count + sum(page_count of preceding tasks)`
- If a task's page count changes:
  All subsequent tasks (`order_index > current`) must have their starting page recomputed, and their `needs_regeneration` flag must be set to `1` with `regeneration_reason = 'starting page changed'`.
- Code reference: [backend/app/services/page_service.py](file:///home/barinr/code/vibe/pfc-v2/backend/app/services/page_service.py).

### 2. The Containerized Pandoc Sandbox Invariant
Pandoc runs inside a container (`docker.io/pandoc/extra`). The container can only access files mounted inside its `/data` volume.
- **Never put host-absolute file paths in the Markdown sent to Pandoc.**
- All resolved images must be placed in a directory mounted into the container, typically `assets/<task-slug>/image-NN.<ext>`.
- The Markdown passed to Pandoc must use container-relative image paths (`assets/<task-slug>/image-NN.<ext>`), and Pandoc must be invoked with `--resource-path=/data`.
- Code reference: [backend/app/services/pdf_service.py](file:///home/barinr/code/vibe/pfc-v2/backend/app/services/pdf_service.py).

### 3. Markdown Validation Rules
Markdown pasted by the user must satisfy:
- Valid YAML frontmatter at the very top of the file containing at least a `title` field.
- No additional `---` horizontal rules in the body text (to prevent YAML parser ambiguity).
- Image placeholders must use Markdown image syntax with optional guidance text or HTML comments:
  `![alt text](url "guidance")` or `![alt text](url) <!-- guidance -->`.
- Code reference: [backend/app/services/markdown_service.py](file:///home/barinr/code/vibe/pfc-v2/backend/app/services/markdown_service.py).

### 4. Database Integrity and Foreign Keys
SQLite connections must always enable foreign keys:
- Execute `PRAGMA foreign_keys = ON;` on every single connection.
- Deleting a practical file cascades to delete all associated tasks and image placeholders.
- Deleting a task cascades to delete its image placeholders.
- Code reference: [backend/app/db.py](file:///home/barinr/code/vibe/pfc-v2/backend/app/db.py).

### 5. Load-Time Drift Detection
When task lists are loaded via `GET /practical-files/{id}/tasks`:
- The backend checks whether the Markdown file or asset files on disk were modified outside the app by recomputing the SHA-256 hash and comparing it to `content_hash`.
- If a mismatch occurs, `needs_regeneration` is set to `1` with `regeneration_reason = 'edited outside app'`.
- Code reference: [backend/app/services/hash_service.py](file:///home/barinr/code/vibe/pfc-v2/backend/app/services/hash_service.py).

---

## 5. Development and Verification Runbook

### Prerequisites
- Python 3.11+ with virtualenv in `backend/.venv`
- Node.js 18+ with `npm` or `pnpm`
- Podman (default) or Docker installed and able to run `docker.io/pandoc/extra`

### Quick Start Commands

#### Run Backend
```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```
Backend API will be accessible at `http://localhost:8000`. Swagger docs at `http://localhost:8000/docs`.

#### Run Frontend
```bash
npm --prefix frontend run dev
```
Frontend will be accessible at `http://localhost:5173`. Requests to `/api/*` are proxied to `http://localhost:8000/*`.

#### Run Tests
Always execute backend tests before completing any task:
```bash
# Run all tests using virtualenv pytest
backend/.venv/bin/pytest backend/tests -v

# Run fast unit tests only (skipping container execution)
backend/.venv/bin/pytest backend/tests -k "not pandoc" -v

# Run containerized end-to-end PDF test
backend/.venv/bin/pytest backend/tests/test_e2e_pandoc.py -v
```

#### Run Frontend Linting and Build
```bash
npm --prefix frontend run lint
npm --prefix frontend run build
```

---

## 6. Common Change Recipes

### Recipe A: Adding a New Backend Endpoint
1. Define request and response schemas in [backend/app/models.py](file:///home/barinr/code/vibe/pfc-v2/backend/app/models.py).
2. Add business logic in the relevant service under [backend/app/services/](file:///home/barinr/code/vibe/pfc-v2/backend/app/services/).
3. Add the route in the corresponding router under [backend/app/routers/](file:///home/barinr/code/vibe/pfc-v2/backend/app/routers/).
4. Add integration tests in [backend/tests/test_api.py](file:///home/barinr/code/vibe/pfc-v2/backend/tests/test_api.py).
5. Update client methods in [frontend/src/api/client.js](file:///home/barinr/code/vibe/pfc-v2/frontend/src/api/client.js).

### Recipe B: Modifying PDF Styling or Pandoc Arguments
1. Inspect [backend/app/services/pdf_service.py](file:///home/barinr/code/vibe/pfc-v2/backend/app/services/pdf_service.py).
2. Eisvogel YAML metadata is constructed in `build_eisvogel_yaml_metadata()`.
3. Pandoc command arguments and container mount options are configured in `compile_markdown_to_pdf()`.
4. Page offset injection is handled in `inject_starting_page_directive()` (`\setcounter{page}{N}`).
5. Run `backend/.venv/bin/pytest backend/tests/test_pdf_service.py` and `backend/.venv/bin/pytest backend/tests/test_e2e_pandoc.py` to verify output.

### Recipe C: Modifying Image Placeholder Resolution
1. Backend handler is in [backend/app/routers/placeholders.py](file:///home/barinr/code/vibe/pfc-v2/backend/app/routers/placeholders.py).
2. Storing and decoding image buffers is handled by [backend/app/services/image_service.py](file:///home/barinr/code/vibe/pfc-v2/backend/app/services/image_service.py).
3. Frontend UI is in [frontend/src/components/PlaceholderRow.jsx](file:///home/barinr/code/vibe/pfc-v2/frontend/src/components/PlaceholderRow.jsx). It supports:
   - File upload (native `<input type="file">`)
   - Image URL download (server fetches URL at generation time)
   - Raw image clipboard paste or dropzone (converts binary to File and uploads to `/placeholders/{id}/upload`)
   - Thumbnail preview via `GET /placeholders/{id}/image`

### Recipe D: Modifying Frontend UI or Workflow Steps
1. Task workflow steps are managed in [frontend/src/pages/TaskWorkflow.jsx](file:///home/barinr/code/vibe/pfc-v2/frontend/src/pages/TaskWorkflow.jsx):
   - Step 1: Prompt generation ([InstructionBlock.jsx](file:///home/barinr/code/vibe/pfc-v2/frontend/src/components/InstructionBlock.jsx))
   - Step 2: Markdown paste and validate ([MarkdownPasteForm.jsx](file:///home/barinr/code/vibe/pfc-v2/frontend/src/components/MarkdownPasteForm.jsx))
   - Step 3: Resolve placeholders ([PlaceholderList.jsx](file:///home/barinr/code/vibe/pfc-v2/frontend/src/components/PlaceholderList.jsx))
   - Step 4: Preview and compile task PDF ([GeneratePanel.jsx](file:///home/barinr/code/vibe/pfc-v2/frontend/src/components/GeneratePanel.jsx))
2. Navigation between practical files and task lists is in [frontend/src/App.jsx](file:///home/barinr/code/vibe/pfc-v2/frontend/src/App.jsx).

---

## 7. Style and Development Constraints

1. **No Em Dashes or En Dashes**: Do not use em dashes or en dashes in any comments, code, user messages, or documentation. Use regular hyphens, colons, or parentheses instead.
2. **No Emojis**: Avoid emojis in user interfaces, console outputs, documentation, or commit messages.
3. **Keep SQL Queries Parameterized**: Never concatenate strings into SQL queries. Always use `?` parameter substitution.
4. **Preserve Database Foreign Keys**: Always ensure `PRAGMA foreign_keys = ON;` is present when creating SQLite connections.
5. **Preserve Container Safety**: Do not pass host paths directly into Pandoc inside the container; always use mapped container-relative paths.
