"""Lightweight helpers for PostHog analytics."""
from __future__ import annotations

from typing import Any, Dict, Optional

import streamlit as st

try:
    from posthog import Posthog
except ImportError:  # pragma: no cover - optional dependency
    Posthog = None  # type: ignore  # noqa: N816

_CLIENT: Optional[Posthog] = None


def _load_config() -> Dict[str, Any]:
    section = st.secrets.get("posthog", {})
    return {
        "api_key": section.get("api_key", ""),
        "host": section.get("host", "https://app.posthog.com"),
    }


def get_client() -> Optional[Posthog]:
    """Return a cached PostHog client if credentials are available."""
    global _CLIENT
    if _CLIENT is not None:
        return _CLIENT
    if Posthog is None:
        return None
    config = _load_config()
    api_key = config.get("api_key")
    if not api_key:
        return None
    host = config.get("host")
    _CLIENT = Posthog(project_api_key=api_key, host=host)
    return _CLIENT


def track_event(event_name: str, distinct_id: str = "anonymous", properties: Optional[Dict[str, Any]] = None) -> None:
    client = get_client()
    if not client:
        return
    client.capture(distinct_id=distinct_id, event=event_name, properties=properties or {})
