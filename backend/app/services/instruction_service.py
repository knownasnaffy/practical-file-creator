from typing import Optional
from app.config import DEFAULT_PROMPT_TEMPLATE


def render_instruction_prompt(
    task_number: int,
    task_title: str,
    template: Optional[str] = None
) -> str:
    """Renders the copyable LLM prompt instruction block for a task."""
    tpl = template or DEFAULT_PROMPT_TEMPLATE
    return tpl.format(
        task_number=task_number,
        task_title=task_title.strip()
    )
