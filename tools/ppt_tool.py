from __future__ import annotations

from pathlib import Path
from typing import Any

from config.settings import Settings
from generators.ppt import build_presentation


def generate_presentation_tool(
    slides: list[dict[str, Any]],
    settings: Settings,
) -> dict[str, Any]:
    """Generate a PowerPoint presentation and return the file path."""
    try:
        output_path: Path = build_presentation(slides, settings)
        return {"success": True, "file_path": str(output_path), "filename": output_path.name}
    except Exception as exc:
        return {"success": False, "error": str(exc)}
