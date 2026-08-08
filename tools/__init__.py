from __future__ import annotations

"""
Tool wrappers that the agent nodes call directly.
Each module exposes a clean functional interface.
"""

from tools.rag_tool import search_knowledge_base
from tools.email_tool import EmailTool
from tools.ppt_tool import generate_presentation_tool
from tools.resume_tool import generate_resume_tool
from tools.document_tool import generate_document_tool
from tools.web_search_tool import web_search

__all__ = [
    "search_knowledge_base",
    "EmailTool",
    "generate_presentation_tool",
    "generate_resume_tool",
    "generate_document_tool",
    "web_search",
]
