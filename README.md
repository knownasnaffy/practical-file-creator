<img width="1920" height="1080" alt="Cover image" src="https://github.com/user-attachments/assets/916f3982-a997-4a04-98fb-a8c580ec68ae" />

# Practical File Generator

Practical File Generator is a local tool that creates formatted, paginated PDF reports for college practical files and lab assignments. It connects Markdown written with large language model assistants, image resolution, and document compilation into a structured workflow.

## The Problem

Students often need to assemble multi-task practical lab files throughout a semester. Writing individual assignments in word processors leads to inconsistent formatting, broken page numbers, and manual screenshot placement.

Generating reports with Markdown and LaTeX provides clean typography, but doing it by hand has friction:
1. Prompts for language models must follow strict formatting rules so they do not produce extra section breaks.
2. Screenshots and diagrams must be found, cropped, and saved to disk.
3. Page numbers must be continuous across multiple tasks, taking into account title pages and earlier assignments. If task 1 changes length, task 2 and all following tasks must have their starting page numbers updated.

This project automates that workflow entirely on your local machine.

## How It Works

The application operates in four stages:

1. Task Instruction Prompt: When you create a task, the application gives you a standardized prompt. You paste this into your preferred chat assistant (such as ChatGPT, Claude, or a local model). The prompt instructs the model to return clean Markdown with a YAML frontmatter title and specific image placeholders, without horizontal rules between sections.

2. Markdown Validation: You paste the model response into the application. The system checks that the frontmatter parses correctly and that there are exactly two delimiter lines. Any format error shows an exact line description.

3. Image Placeholder Resolution: The application lists each placeholder found in the text. For each placeholder, you can:
   - Click to search Google Images in a new tab.
   - Paste an image URL for the server to download.
   - Paste a copied screenshot directly into the input with Ctrl+V.
   - Upload an image file from your computer.

4. Containerized PDF Build: The application creates a temporary build copy, injects the correct starting page number into the document header, copies resolved assets into place, and runs Pandoc inside an isolated Podman container with the Eisvogel LaTeX template. Once built, the page count is recorded, and the generated PDF is saved to your disk.

If an earlier task changes its page count, later tasks are marked as needing regeneration so your running page numbers stay accurate.

<details>
<summary><h2>Screenshots</h2></summary>
<img width="1920" height="1080" alt="image" src="https://github.com/user-attachments/assets/ab1dc6af-423d-4961-9deb-c6832378f024" />
<hr/>
<img width="1920" height="1080" alt="image" src="https://github.com/user-attachments/assets/95cea38e-2bf5-45f9-89f0-2cd6154e52fa" />
<hr/>
<img width="1920" height="1080" alt="image" src="https://github.com/user-attachments/assets/6a013e1e-fafa-4773-8957-2143aed76296" />
<hr/>
<img width="1920" height="1080" alt="image" src="https://github.com/user-attachments/assets/afcf3f0c-7fda-48b0-a31d-fa0f4e243ddb" />
<hr/>
<img width="1920" height="1080" alt="image" src="https://github.com/user-attachments/assets/2cb10e76-f70b-4fcb-a997-a97e0f4aa60c" />
<hr/>
<img width="1920" height="1080" alt="image" src="https://github.com/user-attachments/assets/943ba906-a599-4c95-8f0c-583a2c7fdb1a" />

</details>

## File Organization on Disk

The application treats your file system as the true source of records. SQLite is used as a fast local index, but your Markdown files, assets, and PDFs live in standard folders:

```
<practical-file-directory>/
  assets/
    1-introduction-to-sql/
      image-01.png
      image-02.png
    uploads/
  tasks/
    1-introduction-to-sql.md
    1-introduction-to-sql.pdf
```

Because your files are regular Markdown and PNG files on disk, you can inspect or edit them with any text editor at any time.

## Prerequisites

Before running the application, make sure the following software is installed on your computer:

- Python (version 3.11 or higher): [Python Downloads](https://www.python.org/downloads/)
- Node.js (version 20 or higher) and npm: [Node.js Downloads](https://nodejs.org/)
- Podman: [Podman Installation Guide](https://podman.io/docs/installation)
  Podman runs the container image that contains Pandoc, XeLaTeX, and the Eisvogel template without requiring you to install a multi-gigabyte TeX Live distribution on your host system.

## Quick Start

### 1. Set Up the Backend

Open a terminal in the project directory:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Start the backend API server:

```bash
uvicorn app.main:app --reload --port 8000
```

The backend starts at `http://localhost:8000`. You can view the interactive OpenAPI documentation at `http://localhost:8000/docs`.

### 2. Set Up the Frontend

Open a second terminal in the project directory:

```bash
cd frontend
npm install
npm run dev
```

The frontend server starts at `http://localhost:5173`. Open this URL in your web browser.

## User Guide

1. Create a Practical File Workspace:
   Click "New Practical File". Enter the subject title (for example, "Database Management Systems"), choose a folder on your computer where files should be stored, and configure the number of cover pages (default is 2, representing cover page and table of contents).

2. Add a Task:
   Click "New Task" and type the topic of the practical (for example, "Introduction to SQL and installation of SQL Server / Oracle").

3. Generate the Content:
   Copy the generated prompt block from Step 1 and paste it into your assistant chat. Once the assistant responds, copy the raw Markdown.

4. Paste and Validate:
   Paste the returned Markdown into Step 2 and click "Validate & Extract Images". If the assistant added trailing commentary or extra horizontal lines, the validation error message points to the problem.

5. Resolve Images:
   In Step 3, view each extracted placeholder. Either paste an image URL, press Ctrl+V to paste a copied screenshot, or upload a local file.

6. Compile PDF:
   In Step 4, review the calculated starting page number. Click "Generate Task PDF". The backend compiles the document via Podman and displays the output page count and download link.

## Architecture

The project has two distinct services:

- Backend: A Python application built with FastAPI. It manages SQLite records, performs frontmatter parsing via python-frontmatter, handles image downloads, calculates page offsets, and manages subprocess execution of the Podman container.
- Frontend: A React single-page application built with Vite and Tailwind CSS. It communicates with the backend through an API proxy on port 5173.

### Key Implementation Decisions

- Disposable Index: The SQLite database indexes metadata (task title, order, page count, and status). If the database is deleted, documents and assets remain intact on disk.
- Isolated Compilation: During PDF compilation, the starting page command is placed only into a temporary build copy. It is never written into the source Markdown file. This keeps the file content hash stable and allows detecting external edits.
- Drift Detection: Whenever you view a practical file, the backend compares the stored content hash with the files on disk. If a Markdown file or image was edited outside the application, the task is flagged with "edited outside app".

## Development and Testing

### Running Tests

The backend includes unit and integration tests covering database constraints, prompt generation, Markdown parsing, image resolution, page cascade calculations, and container PDF builds.

Run the test suite from the backend directory:

```bash
cd backend
source .venv/bin/activate
PYTHONPATH=. pytest -v
```

### Verifying Frontend Builds

To test the frontend build and static asset generation:

```bash
cd frontend
npm run build
```

## Contributing

Contributions are welcome. Here are some guidelines to keep the codebase clean:

1. Keep modules focused: Business logic belongs in `backend/app/services/`, database operations in `backend/app/db.py`, and HTTP routes in `backend/app/routers/`.
2. Maintain container isolation: Ensure all relative file paths passed to container tools reference files inside the mounted data volume.
3. Write automated tests: Add test coverage in `backend/tests/` for any new endpoint, parser rule, or calculation change.
4. Keep interfaces simple: Avoid adding external API dependencies when standard local tools can accomplish the task.

## References

- Pandoc User Guide: https://pandoc.org/MANUAL.html
- Eisvogel LaTeX Template: https://github.com/Wandmalfarbe/pandoc-latex-template
- Podman Documentation: https://docs.podman.io/
- FastAPI Documentation: https://fastapi.tiangolo.com/
- React Documentation: https://react.dev/
- Vite Documentation: https://vite.dev/
- PyPDF Documentation: https://pypdf.readthedocs.io/
- Python Frontmatter: https://python-frontmatter.readthedocs.io/
