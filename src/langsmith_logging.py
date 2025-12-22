from __future__ import annotations

import os
from typing import Any, Dict, Optional

from langsmith import Client


def _langsmith_available() -> bool:
    """Return True when the environment is configured for LangSmith logging."""
    return bool(
        os.environ.get("LANGSMITH_API_KEY")
        or os.environ.get("LANGCHAIN_API_KEY")
        or os.environ.get("LANGCHAIN_TRACING_V2")
    )


def _truncate_text(value: Optional[str], limit: int = 800) -> str:
    """Return a bounded preview so traces stay compact."""
    if not value:
        return ""
    text = str(value)
    if len(text) <= limit:
        return text
    return f"{text[:limit]}... ({len(text) - limit} more chars)"


def _safe_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure payload is JSON-serializable by coercing complex types to strings."""
    safe: Dict[str, Any] = {}
    for key, value in payload.items():
        if isinstance(value, (str, int, float, type(None), bool)):
            safe[key] = value
        elif isinstance(value, dict):
            safe[key] = _safe_payload(value)
        elif isinstance(value, (list, tuple)):
            safe[key] = [
                item if isinstance(item, (str, int, float, type(None), bool)) else str(item)
                for item in value
            ]
        else:
            safe[key] = str(value)
    return safe


def log_langsmith_run(
    *,
    name: str,
    inputs: Dict[str, Any],
    outputs: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None,
    tags: Optional[list[str]] = None,
    run_type: str = "chain",
    project_name: Optional[str] = None,
) -> None:
    """Create a LangSmith run with safe payloads and graceful fallbacks."""
    if not _langsmith_available():
        return

    try:
        client = Client()
    except Exception as exc:  # pragma: no cover - defensive logging only
        print(f"LangSmith client initialization failed: {exc}")
        return

    payload = {
        "name": name,
        "inputs": _safe_payload(inputs),
        "run_type": run_type,
    }
    if project_name:
        payload["project_name"] = project_name
    if tags:
        payload["tags"] = tags
    extra = {"metadata": metadata} if metadata else None
    if extra:
        payload["extra"] = extra
    payload["outputs"] = _safe_payload(outputs)

    try:
        client.create_run(**payload)
    except Exception as exc:  # pragma: no cover - logging should not fail cron
        print(f"LangSmith logging failed: {exc}")


def log_qna_response(
    *,
    session_id: str,
    topic: str,
    question_topic: str,
    prompt: str,
    transcript: Optional[str],
    response: str,
    source: str,
    tags: Optional[list[str]] = None,
) -> None:
    """Log a CRON-generated QnA exchange to LangSmith."""
    transcript_text = transcript or ""
    inputs = {
        "session_id": session_id,
        "topic": topic,
        "question_topic": question_topic,
        "prompt": prompt,
        "prompt_length": len(prompt or ""),
        "transcript_preview": _truncate_text(transcript_text),
        "transcript_length": len(transcript_text),
    }
    outputs = {
        "response_preview": _truncate_text(response),
        "response_length": len(response or ""),
    }
    metadata = {
        "source": source,
        "session_id": session_id,
        "question_topic": question_topic,
        "topic": topic,
    }
    merged_tags = (tags or []) + ["qna", source]
    log_langsmith_run(
        name="session_qna_generation",
        inputs=inputs,
        outputs=outputs,
        metadata=metadata,
        tags=merged_tags,
    )
