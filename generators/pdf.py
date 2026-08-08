from __future__ import annotations

import re
import uuid
from io import BytesIO
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable

from config.settings import Settings


def build_pdf(content: str, doc_type: str, settings: Settings) -> Path:
    """Generate a PDF from plain/Markdown-like content."""
    settings.generated_dir.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9_]+", "_", doc_type.lower()).strip("_") or "document"
    filename = f"{slug}_{uuid.uuid4().hex[:8]}.pdf"
    output_path = settings.generated_dir / filename

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2.5 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Title"],
        fontSize=22,
        spaceAfter=12,
        textColor=colors.HexColor("#1f2328"),
    )
    heading2_style = ParagraphStyle(
        "Heading2Custom",
        parent=styles["Heading2"],
        fontSize=14,
        spaceBefore=12,
        spaceAfter=6,
        textColor=colors.HexColor("#1f2328"),
    )
    body_style = ParagraphStyle(
        "BodyCustom",
        parent=styles["BodyText"],
        fontSize=11,
        spaceAfter=6,
        leading=16,
    )
    bullet_style = ParagraphStyle(
        "BulletCustom",
        parent=styles["BodyText"],
        fontSize=11,
        spaceAfter=4,
        leftIndent=14,
        bulletIndent=0,
    )

    story = [Paragraph(doc_type, title_style), HRFlowable(width="100%", spaceAfter=10)]

    for line in content.splitlines():
        stripped = line.strip()
        if not stripped:
            story.append(Spacer(1, 8))
            continue
        if stripped.startswith("# "):
            story.append(Paragraph(stripped[2:], title_style))
        elif stripped.startswith("## "):
            story.append(Paragraph(stripped[3:], heading2_style))
        elif stripped.startswith("### "):
            story.append(Paragraph(f"<b>{stripped[4:]}</b>", body_style))
        elif stripped.startswith("- ") or stripped.startswith("* "):
            story.append(Paragraph(f"• {stripped[2:]}", bullet_style))
        else:
            story.append(Paragraph(stripped, body_style))

    doc.build(story)
    output_path.write_bytes(buffer.getvalue())
    return output_path
