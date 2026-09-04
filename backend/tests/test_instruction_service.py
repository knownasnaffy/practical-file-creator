from app.services.instruction_service import render_instruction_prompt


def test_render_instruction_prompt():
    prompt = render_instruction_prompt(
        task_number=1,
        task_title="Introduction to SQL and installation of SQL Server / Oracle"
    )
    assert "Generate my practical file task 1: Introduction to SQL and installation of SQL Server / Oracle." in prompt
    assert "It should be markdown with the title being in the frontmatter only as a title field." in prompt
    assert "Don't use --- separators between sections." in prompt
    assert "The image placeholders should be in normal markdown image format." in prompt
