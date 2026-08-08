from __future__ import annotations

from pathlib import Path
from typing import Any

from config.settings import Settings
from generators.resume import build_resume_docx


def generate_resume_tool(
    resume_data: dict[str, Any],
    role: str,
    settings: Settings,
) -> dict[str, Any]:
    """Generate a resume DOCX and return the file path."""
    try:
        output_path: Path = build_resume_docx(resume_data, role, settings)
        return {"success": True, "file_path": str(output_path), "filename": output_path.name}
    except Exception as exc:
        return {"success": False, "error": str(exc)}
