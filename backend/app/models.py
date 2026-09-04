from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field


# ---------------- Practical File Models ----------------

class PracticalFileCreate(BaseModel):
    subject_name: str = Field(min_length=1, max_length=200)
    directory_path: str = Field(min_length=1)
    cover_page_count: int = Field(default=2, ge=0)


class PracticalFilePatch(BaseModel):
    cover_page_count: int = Field(ge=0)


class PracticalFileResponse(BaseModel):
    id: int
    subject_name: str
    directory_path: str
    cover_page_count: int
    created_at: str


# ---------------- Task Models ----------------

class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)


class TaskResponse(BaseModel):
    id: int
    practical_file_id: int
    title: str
    order_index: int
    markdown_path: Optional[str] = None
    assets_dir: Optional[str] = None
    pdf_path: Optional[str] = None
    page_count: Optional[int] = None
    content_hash: Optional[str] = None
    status: Literal['drafting', 'pasted', 'resolving_images', 'generated']
    needs_regeneration: bool = False
    regeneration_reason: Optional[Literal['starting page changed', 'edited outside app']] = None


class TaskWithInstructionResponse(BaseModel):
    task: TaskResponse
    instruction_block: str


class TaskReorderRequest(BaseModel):
    task_ids: list[int] = Field(min_length=1)


# ---------------- Placeholder Models ----------------

class PlaceholderResponse(BaseModel):
    id: int
    task_id: int
    position: int
    search_query: str
    source_type: Literal['search', 'custom']
    source_value: Optional[str] = None
    resolved_path: Optional[str] = None
    error: Optional[str] = None


class PlaceholderPatch(BaseModel):
    source_value: str = Field(min_length=1)
    source_type: Literal['search', 'custom'] = 'search'


class PlaceholderUploadResponse(BaseModel):
    id: int
    task_id: int
    position: int
    source_type: Literal['custom']
    source_value: str
    resolved_path: Optional[str] = None


# ---------------- Markdown Models ----------------

class MarkdownPasteRequest(BaseModel):
    raw_markdown: str = Field(min_length=1)


class MarkdownValidationResponse(BaseModel):
    valid: bool
    title: Optional[str] = None
    placeholder_count: int
    placeholders: list[PlaceholderResponse]
    error: Optional[str] = None


# ---------------- Generation Models ----------------

class StartingPageResponse(BaseModel):
    task_id: int
    computed_starting_page: int
    cover_page_count: int
    accumulated_earlier_pages: int


class GenerateRequest(BaseModel):
    starting_page: Optional[int] = Field(default=None, ge=1)


class GenerateResponse(BaseModel):
    task_id: int
    pdf_path: str
    page_count: int
    starting_page: int
    content_hash: str
    status: str
    stderr: Optional[str] = None


class PracticalFileWithTasksResponse(BaseModel):
    practical_file: PracticalFileResponse
    tasks: list[TaskResponse]
