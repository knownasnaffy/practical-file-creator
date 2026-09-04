import os
from pathlib import Path
from typing import Optional
import httpx


def get_image_extension(content_type: Optional[str], filename: Optional[str] = None) -> str:
    """Infer image extension from content-type or filename."""
    if content_type:
        ct = content_type.lower()
        if "image/jpeg" in ct or "image/jpg" in ct:
            return ".jpg"
        if "image/png" in ct:
            return ".png"
        if "image/webp" in ct:
            return ".webp"
        if "image/svg" in ct:
            return ".svg"
        if "image/gif" in ct:
            return ".gif"

    if filename:
        ext = Path(filename).suffix.lower()
        if ext in [".jpg", ".jpeg", ".png", ".webp", ".svg", ".gif"]:
            return ext

    return ".png"


def download_image(url: str, output_path: Path, timeout: float = 15.0) -> Path:
    """
    Downloads an image from URL to output_path.
    Raises Exception with clear message on network/HTTP failure.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    }
    with httpx.Client(follow_redirects=True, timeout=timeout, headers=headers) as client:
        response = client.get(url)
        response.raise_for_status()

        # Update extension if needed based on content-type
        content_type = response.headers.get("content-type", "")
        inferred_ext = get_image_extension(content_type, url)
        
        # If output_path has generic extension or mismatched, normalize
        final_path = output_path.with_suffix(inferred_ext)
        with open(final_path, "wb") as f:
            f.write(response.content)

        return final_path


def save_uploaded_image(file_bytes: bytes, filename: str, output_path: Path) -> Path:
    """Saves uploaded file bytes to output_path."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ext = get_image_extension(None, filename)
    final_path = output_path.with_suffix(ext)
    with open(final_path, "wb") as f:
        f.write(file_bytes)
    return final_path
