from __future__ import annotations

from pathlib import Path
from typing import Any

from config.settings import Settings
from generators.docx import build_docx
from generators.pdf import build_pdf


def generate_document_tool(
    content: str,
    doc_type: str,
    output_format: str,
    settings: Settings,
) -> dict[str, Any]:
    """Generate a document in the specified format and return the file path."""
    fmt = output_format.lower()
    try:
        if fmt == "pdf":
            output_path: Path = build_pdf(content, doc_type, settings)
        else:
            # Default to DOCX
            output_path = build_docx(content, doc_type, settings)
        return {"success": True, "file_path": str(output_path), "filename": output_path.name}
    except Exception as exc:
        return {"success": False, "error": str(exc)}
