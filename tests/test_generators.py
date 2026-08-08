from __future__ import annotations

import pytest
from pathlib import Path


def _make_settings(tmp_path: Path):
    from config.settings import Settings
    s = Settings(
        gemini_api_key="",
        chroma_persist_directory=tmp_path / "chroma",
        sqlite_database=tmp_path / "app.db",
        data_dir=tmp_path / "data",
        generated_dir=tmp_path / "generated",
        log_dir=tmp_path / "logs",
    )
    s.ensure_directories()
    return s


class TestPPTGenerator:
    def test_creates_pptx_file(self, tmp_path):
        from generators.ppt import build_presentation
        settings = _make_settings(tmp_path)
        slides = [
            {"slide_title": "About Me", "bullet_points": ["Software Engineer", "5 years experience"], "notes": None},
            {"slide_title": "Skills", "bullet_points": ["Python", "ML", "Cloud"], "notes": "Technical skills"},
        ]
        output_path = build_presentation(slides, settings)
        assert output_path.exists()
        assert output_path.suffix == ".pptx"
        assert output_path.stat().st_size > 0

    def test_creates_file_with_correct_name_prefix(self, tmp_path):
        from generators.ppt import build_presentation
        settings = _make_settings(tmp_path)
        slides = [{"slide_title": "About Me", "bullet_points": ["Hello"], "notes": None}]
        output_path = build_presentation(slides, settings)
        assert "about_me" in output_path.name or "presentation" in output_path.name

    def test_empty_slides_list(self, tmp_path):
        from generators.ppt import build_presentation
        settings = _make_settings(tmp_path)
        output_path = build_presentation([], settings)
        assert output_path.exists()


class TestDocxGenerator:
    def test_creates_docx_file(self, tmp_path):
        from generators.docx import build_docx
        settings = _make_settings(tmp_path)
        content = "# Professional Bio\n\nSoftware engineer with expertise in Python.\n\n## Skills\n- Python\n- Go"
        output_path = build_docx(content, "Professional Bio", settings)
        assert output_path.exists()
        assert output_path.suffix == ".docx"
        assert output_path.stat().st_size > 0

    def test_creates_resume_docx(self, tmp_path):
        from generators.resume import build_resume_docx
        settings = _make_settings(tmp_path)
        resume_data = {
            "name": "Jane Doe",
            "summary": "Experienced ML engineer.",
            "experience": [
                {"title": "ML Engineer", "company": "Acme Corp", "dates": "2020-2023",
                 "bullet_points": ["Built ML pipelines", "Deployed models"]}
            ],
            "education": [{"degree": "BSc Computer Science", "institution": "MIT", "dates": "2016-2020"}],
            "skills": ["Python", "TensorFlow", "PyTorch"],
            "projects": [{"name": "LLM App", "description": "Deployed LLM", "technologies": "Python, LangChain"}],
            "certifications": ["AWS Certified ML Specialty"],
        }
        output_path = build_resume_docx(resume_data, "ML Engineer", settings)
        assert output_path.exists()
        assert output_path.suffix == ".docx"
        assert "resume" in output_path.name


class TestPDFGenerator:
    def test_creates_pdf_file(self, tmp_path):
        from generators.pdf import build_pdf
        settings = _make_settings(tmp_path)
        content = "# Profile\n\nA professional software engineer.\n\n## Experience\n- 5 years in Python\n- ML background"
        output_path = build_pdf(content, "Professional Profile", settings)
        assert output_path.exists()
        assert output_path.suffix == ".pdf"
        assert output_path.stat().st_size > 0

    def test_pdf_name_prefix_matches_doc_type(self, tmp_path):
        from generators.pdf import build_pdf
        settings = _make_settings(tmp_path)
        output_path = build_pdf("Hello world", "My Document", settings)
        assert "my_document" in output_path.name or "document" in output_path.name
