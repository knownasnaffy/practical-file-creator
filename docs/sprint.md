---
title: "Practical File Generator — MVP Build Sprint"
date: "2026-08-20"
based_on: "./architecture.md, ./design_spec.md"
---

# Sprint Plan: Practical File Generator — MVP Build

**Window:** Aug 20 – Aug 27, 2026 (1 sprint, single build effort)
**Team:** Barinderpreet (driver) + Claude Code, using the main thread for
sequential/foundational work and delegated sub-agents for parallelizable
workstreams once the schema and API contract are frozen.

**Sprint Goal:** Ship a working local MVP — create a practical file, draft a
task via the copy-paste LLM instruction flow, validate and resolve images, and
generate a correctly paginated PDF via pandoc — matching Phases 0–6 in
`architecture.md`, end to end, on one real subject with 2+ tasks.

> Assumption flagged: since this is a one-person project, I've replaced
> human-capacity planning (PTO, story points, standup) with an agent-workstream
> model — what can run as parallel Claude Code sub-agents vs. what's blocked on
> shared state. Say the word if you'd rather size this in hours/days instead.

---

## Agent Allocation

The dependency-forcing resource here isn't developer-hours, it's **shared
state**: the SQLite schema (§6) and the API table (§5) in `architecture.md`.
Nothing can safely parallelize until both are frozen in Phase 0.

| Workstream | Agent role | Parallelizable? | Blocked on |
|---|---|---|---|
| Schema + scaffolding | Main agent (sequential) | No — everyone else depends on this | — |
| Backend CRUD + instruction template | `backend-core` sub-agent | Yes, once schema lands | Phase 0 |
| Frontend shell + routing | `frontend-shell` sub-agent | Yes, in parallel with backend-core | Phase 0 (needs the frozen §5 API table as a mock contract) |
| Markdown validation service | `backend-services` sub-agent | No — mutates `tasks.status`, sequence after Phase 1 | Phase 1 |
| Image resolution endpoints | `backend-services` sub-agent | Partial — can start once placeholder rows exist | Phase 2 |
| PDF generation pipeline | `backend-services` sub-agent, solo (highest-risk, keep sequential) | No — touches pandoc/LaTeX subprocess, D4 temp-copy logic, hashing | Phases 2 & 3 |
| Page cascade + drift detection | `backend-services` sub-agent | No — depends on real `page_count`/`content_hash` values existing | Phase 4 |
| Frontend workflow screens | `frontend-workflow` sub-agent | Yes, parallel with backend Phases 2–5 once endpoints match §5 | Phase 0 contract freeze |
| Error-message + polish pass | `qa-polish` sub-agent | No — needs everything else in place to review against | All above |

**Working with Claude Code:** freeze `architecture.md` §5 (API table) and §6
(schema) as the shared contract before spawning any parallel sub-agents — have
each sub-agent read it first rather than re-deriving endpoint shapes. Use the
Task tool to spin up `backend-core` and `frontend-shell` together right after
Phase 0; keep `pdf_service` (the pandoc/LaTeX/D4 logic) in a single sub-agent
rather than splitting it, since it's the one place where a subtle interleaving
bug (e.g., page-directive leaking into the source `.md`) is expensive to catch
later. A lightweight `TodoWrite`-tracked checklist mirroring the table below
keeps phase status visible across sub-agent handoffs.

---

## Sprint Backlog

| Priority | Item | Size | Owner | Depends on |
|---|---|---|---|---|
| P0 | Phase 0: FastAPI + Vite skeletons, SQLite migration, `PRAGMA foreign_keys=ON`, CORS | M | Main agent | — |
| P0 | Phase 1: `practical_files`/`tasks` CRUD endpoints | M | `backend-core` | Phase 0 |
| P0 | Phase 1: instruction-block template rendering (copyable text) | S | `backend-core` | Phase 0 |
| P0 | Frontend shell: `PracticalFileList`, `TaskList`, `TaskWorkflow` routing | M | `frontend-shell` | Phase 0 (§5 contract) |
| P0 | Phase 2: `markdown_service` — frontmatter parse + `---` separator check | M | `backend-services` | Phase 1 |
| P0 | Phase 2: placeholder extraction into `image_placeholders` rows | S | `backend-services` | Phase 2 (above) |
| P0 | Phase 3: `PATCH /placeholders/{id}` (pasted URL) + `POST .../upload` | M | `backend-services` | Phase 2 |
| P0 | Phase 4: `pdf_service` — D4 temp-copy build, `\setcounter{page}{N}` injection, pandoc invocation | L | `backend-services` (solo) | Phases 2 & 3 |
| P0 | Phase 4: page-count read-back via `pypdf`, failure path (stderr surfaced, prior state untouched) | M | `backend-services` (solo) | above |
| P0 | First end-to-end smoke run: one subject, one task, real pandoc build | S | Barinderpreet | all P0 above |
| P1 | Phase 3: retry endpoint for failed downloads | S | `backend-services` | Phase 3 |
| P1 | Phase 5: `page_service` — starting-page calc + cascade `needs_regeneration` on page-count change | M | `backend-services` | Phase 4 |
| P1 | Phase 5: `hash_service` — SHA-256 over markdown + sorted assets, load-time check | M | `backend-services` | Phase 4 |
| P1 | `cover_page_count` PATCH cascades `needs_regeneration` (Open Q4, resolved: true) | S | `backend-services` | Phase 5 |
| P1 | Frontend: `GeneratePanel`, `PlaceholderList`/`PlaceholderRow`, `RegenerationBadge` | M | `frontend-workflow` | §5 contract + Phase 3/4 shapes |
| P2 | Phase 6: inline specific error messages across all validation paths (no generic failures) | M | `qa-polish` | all above |
| P2 | `RegenerationBadge` dual-reason text ("starting page changed" vs "edited outside app") | S | `qa-polish` | Phase 5 |
| P2 | Task reorder endpoint + right-click move up/down (Open Q2, resolved) | S | `frontend-workflow` | P0/P1 backlog clear |

---

## Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Sub-agents drift from the frozen §5 API contract while working in parallel | Backend/frontend shapes mismatch, integration rework | Treat `architecture.md` §5/§6 as read-only source of truth; each sub-agent re-reads it before touching endpoints rather than inferring from partial context |
| `pandoc`/LaTeX/`pypdf` not present or misconfigured locally | Phase 4 blocked at the highest-risk, highest-value step | Add an environment check to Phase 0 (verify pandoc + template + `pypdf` import) before any sub-agent starts backend work |
| D4's temp-build-copy logic gets simplified away under time pressure (page directive written into source `.md`) | Silently breaks the two independent staleness signals (page drift vs. content edit) | Keep `pdf_service` as a single, un-split sub-agent task; smoke-test by regenerating a task twice with only a starting-page change and confirming `content_hash` doesn't move |
| Parallel sub-agents touch overlapping files (e.g., `db.py` schema vs. a service importing it) | Merge conflicts, wasted rework | Phase 0 strictly gates parallel work; module boundaries in §7/§8 assign each service/component to exactly one sub-agent |
| Context loss across long multi-turn agent sessions | Re-deriving decisions already settled in §9 (D1–D5), regressions | Keep `architecture.md` and `design_spec.md` as persistent references each sub-agent loads at task start |

---

## Definition of Done

- [ ] Every Phase 0–6 checklist item in `architecture.md` §11 is checked off
- [ ] Full manual smoke test passes: create subject → new task → paste
      instruction block into an external LLM chat → paste markdown back →
      resolve one search-URL image + one uploaded image → generate → PDF
      opens with correct starting page
- [ ] Regenerating an earlier task with a changed page count flags every later
      task `needs_regeneration = "starting page changed"`
- [ ] Hand-editing a task's `.md` outside the app (Neovim) flags
      `needs_regeneration = "edited outside app"` on next task-list load
- [ ] A deliberately broken pandoc build surfaces real stderr in the UI and
      leaves the prior PDF/state untouched
- [ ] `content_hash` is stable across a page-only regeneration (D4 check)

## Milestones

| Checkpoint | What it proves |
|---|---|
| Phase 0–1 complete | Schema frozen, CRUD + instruction block working, frontend shell talks to backend |
| Phase 2–3 complete | A real pasted-back markdown file validates and its images resolve to local paths |
| Phase 4 complete (mid-sprint check-in) | First real PDF generated end-to-end with correct injected starting page — the highest-risk step, worth a deliberate pause here |
| Phase 5–6 complete (sprint end) | Drift detection, cascades, and error messaging all match the spec; DoD checklist fully green |
