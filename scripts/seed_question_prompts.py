#!/usr/bin/env python
"""Seed the question_prompts table with the default prompt set."""
from __future__ import annotations

import os
from typing import Dict, Iterable

from supabase import Client, create_client  # type: ignore

from utils.prompts import (
    DEFAULT_PROMPT_GROUP,
    DEFAULT_QUESTION_PROMPTS,
    DEFAULT_STATUS,
    PROMPT_TABLE_NAME,
)


def _build_client() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise SystemExit(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_KEY) must be set."
        )
    return create_client(url, key)


def _fetch_existing_titles(client: Client) -> set[tuple[str, str]]:
    response = (
        client.table(PROMPT_TABLE_NAME)
        .select("title,prompt_group")
        .execute()
    )
    rows = response.data or []
    return {
        (row.get("title"), row.get("prompt_group", DEFAULT_PROMPT_GROUP))
        for row in rows
        if row.get("title")
    }


def _build_rows(prompts: Iterable[Dict[str, str]]) -> list[dict]:
    rows = []
    for prompt in prompts:
        row = {
            "title": prompt["title"],
            "prompt": prompt["prompt"],
            "prompt_group": prompt.get("prompt_group", DEFAULT_PROMPT_GROUP),
            "status": prompt.get("status", DEFAULT_STATUS),
        }
        rows.append(row)
    return rows


def main() -> None:
    client = _build_client()
    existing = _fetch_existing_titles(client)
    rows = [
        row
        for row in _build_rows(DEFAULT_QUESTION_PROMPTS)
        if (row["title"], row["prompt_group"]) not in existing
    ]
    if not rows:
        print("question_prompts already contains the default rows.")
        return

    client.table(PROMPT_TABLE_NAME).insert(rows).execute()
    print(f"Inserted {len(rows)} question_prompts rows.")


if __name__ == "__main__":
    main()
