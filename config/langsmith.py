from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Iterator

from config.settings import Settings


def configure_langsmith(settings: Settings) -> None:
    """Configure optional LangSmith tracing via environment variables."""
    if not settings.langsmith_enabled:
        return

    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
    os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
    os.environ["LANGSMITH_ENDPOINT"] = settings.langsmith_endpoint


@contextmanager
def trace_block(
    settings: Settings,
    name: str,
    *,
    run_type: str = "chain",
    inputs: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> Iterator[Any]:
    """Create a LangSmith trace span when enabled, otherwise no-op."""
    if not settings.langsmith_enabled:
        yield None
        return

    from langsmith import trace  # local import to keep dependency optional at runtime

    with trace(
        name=name,
        run_type=run_type,
        inputs=inputs or {},
        metadata=metadata or {},
    ) as run_tree:
        yield run_tree


def set_trace_outputs(run_tree: Any, outputs: dict[str, Any]) -> None:
    """Safely attach outputs to a LangSmith run tree."""
    if run_tree is None:
        return
    try:
        run_tree.end(outputs=outputs)
    except Exception:
        return


def set_trace_error(run_tree: Any, error: Exception | str) -> None:
    """Safely attach error details to a LangSmith run tree."""
    if run_tree is None:
        return
    try:
        run_tree.end(
            error=str(error),
            outputs={
                "error": str(error),
            },
        )
    except Exception:
        return
