from __future__ import annotations

import os
from typing import Dict, List

from utils.supabase_integration import SupabaseClient

PROMPT_TABLE_NAME = "question_prompts"
DEFAULT_PROMPT_GROUP = "common"
DEFAULT_STATUS = "active"

system_prompt = """
You are a helpful AI assistant. Provide the information as best as you can based only on the transcript provided.
Many session includes a recap at the start. Most responses should use the new content discussed in this session, and not what was covered in the recap.
"""

DEFAULT_QUESTION_PROMPTS: List[Dict[str, str]] = [
    {
        "title": "Topics Discussed",
        "prompt": "Summarize the main topics covered during the session in a 3-5 bullet list - one line each",
        "status": DEFAULT_STATUS,
        "prompt_group": DEFAULT_PROMPT_GROUP,
    },
    {
        "title": "Action Items",
        "prompt": "List any action items or tasks that were assigned during the session in a 3-5 bullet list - one line each",
        "status": DEFAULT_STATUS,
        "prompt_group": DEFAULT_PROMPT_GROUP,
    },
    {
        "title": "Suggested Next Steps",
        "prompt": "Provide recommendations for follow-up actions or next steps based on the discussion",
        "status": DEFAULT_STATUS,
        "prompt_group": DEFAULT_PROMPT_GROUP,
    },
    {
        "title": "Unclear items",
        "prompt": "Highlight any points that were unclear for the participants in a bullet list - one line each",
        "status": DEFAULT_STATUS,
        "prompt_group": DEFAULT_PROMPT_GROUP,
    },
    {
        "title": "Questions",
        "prompt": "Prepare a bullet list of five to ten questions that can be asked to the participants to check their understanding of the session",
        "status": DEFAULT_STATUS,
        "prompt_group": DEFAULT_PROMPT_GROUP,
    },
]


def _build_supabase_client() -> SupabaseClient | None:
    """Return a SupabaseClient when SUPABASE_URL/KEY are configured."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        return None
    return SupabaseClient(url=url, key=key)


def _normalize_rows(rows: List[Dict]) -> List[Dict[str, str]]:
    normalized: List[Dict[str, str]] = []
    for row in rows:
        title = row.get("title")
        prompt = row.get("prompt")
        if not title or not prompt:
            continue
        normalized.append(
            {
                "title": title,
                "prompt": prompt,
                "status": row.get("status", DEFAULT_STATUS),
                "prompt_group": row.get("prompt_group", DEFAULT_PROMPT_GROUP),
            }
        )
    return normalized


def load_question_prompts(prompt_group: str = DEFAULT_PROMPT_GROUP) -> List[Dict[str, str]]:
    """Fetch prompts from Supabase or fall back to the baked-in defaults."""
    client = _build_supabase_client()
    supabase = getattr(client, "supabase", None)
    if not supabase:
        return DEFAULT_QUESTION_PROMPTS

    try:
        query = (
            supabase.table(PROMPT_TABLE_NAME)
            .select("title,prompt,status,prompt_group")
            .eq("status", "active")
        )
        if prompt_group:
            query = query.eq("prompt_group", prompt_group)
        response = query.order("title").execute()
        rows = _normalize_rows(response.data or [])
        if rows:
            return rows
    except Exception as exc:  # pragma: no cover - defensive log path
        print(f"Error loading Supabase prompts: {exc}")
    return DEFAULT_QUESTION_PROMPTS


question_prompts = load_question_prompts()
