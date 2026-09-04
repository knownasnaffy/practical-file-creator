from pathlib import Path

DEFAULT_PROMPT_TEMPLATE = """Generate my practical file task {task_number}: {task_title}.

It should be markdown with the title being in the frontmatter only as a title field. You can add image placeholders as for where images and be inserted, whether they be screenshots or other forms of images. Don't use --- separators between sections. The image placeholders should be in normal markdown image format. The image placeholders should have alt text that briefly describes the image (very short). The placeholders should also be accompanied by comments that makes it clear what kind of image should go in there, it can be a proper instruction like take a screenshot of this ui or something like search terms that can be used with Google image search if applicable."""

# Default container runner and image
PANDOC_CONTAINER_ENGINE = "podman"
PANDOC_IMAGE = "docker.io/pandoc/extra"
PANDOC_TEMPLATE = "eisvogel"

# Default SQLite database path
DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "index.db"
