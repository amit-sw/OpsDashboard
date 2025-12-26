import math
import os
from typing import List

import pandas as pd
import streamlit as st

from utils.supabase_integration import SupabaseClient

DEFAULT_STATUS = "active"
DEFAULT_PROMPT_GROUP = "common"
EDITOR_ROLES = {"financeadmin", "superadmin"}


def _coerce_int(value) -> int | None:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _build_client() -> SupabaseClient | None:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        return None
    return SupabaseClient(url=url, key=key)


def _load_prompts(client: SupabaseClient, status: str) -> List[dict]:
    with st.spinner("Loading prompts from Supabase..."):
        return client.list_question_prompts(status=status)


def _render_prompt_filters(prompts: List[dict]) -> tuple[str, str]:
    groups = sorted({row.get("prompt_group", DEFAULT_PROMPT_GROUP) for row in prompts} - {""})
    filter_label = "All groups"
    options = [filter_label] + (groups or [DEFAULT_PROMPT_GROUP])
    selected = st.selectbox("Filter by prompt group", options)
    return selected, filter_label


def _render_prompt_table(prompts: List[dict], selected_group: str, filter_label: str) -> tuple[List[dict], List[dict]]:
    filtered = [
        row for row in prompts if selected_group == filter_label or row.get("prompt_group") == selected_group
    ]
    st.caption(f"Showing {len(filtered)} prompts.")
    if not filtered:
        st.info("No prompts yet. Add rows in the table below to create the first entry.")
    filtered_df = pd.DataFrame(filtered)
    required_columns = ["id", "title", "prompt", "prompt_group"]
    for column in required_columns:
        if column not in filtered_df:
            filtered_df[column] = None if column == "id" else ""
    editor_key = f"prompt_table_{selected_group}"
    column_config = {
        "id": st.column_config.NumberColumn("ID", disabled=True),
    }
    editor_value = st.data_editor(
        filtered_df,
        use_container_width=True,
        hide_index=True,
        key=editor_key,
        disabled=False if _can_edit_prompts() else True,
        column_config=column_config,
        num_rows="dynamic" if _can_edit_prompts() else "fixed",
    )
    edited_rows = editor_value.to_dict("records")
    return filtered, edited_rows


def _user_role() -> str:
    return st.session_state.get("current_user_role", "guest")


def _can_edit_prompts() -> bool:
    return _user_role() in EDITOR_ROLES


def _collect_prompt_changes(
    original_rows: List[dict], edited_rows: List[dict]
) -> tuple[List[tuple[int, dict]], List[dict], List[int]]:
    original_map = {}
    for row in original_rows:
        row_id = _coerce_int(row.get("id"))
        if row_id is not None:
            original_map[row_id] = row
    updates: List[tuple[int, dict]] = []
    creations: List[dict] = []
    invalid_rows: List[int] = []
    for idx, row in enumerate(edited_rows):
        prompt_id = _coerce_int(row.get("id"))
        title_value = str(row.get("title") or "").strip()
        prompt_value = str(row.get("prompt") or "").strip()
        group_value = str(row.get("prompt_group") or DEFAULT_PROMPT_GROUP).strip() or DEFAULT_PROMPT_GROUP
        if prompt_id and prompt_id in original_map:
            original = original_map[prompt_id]
            if (
                title_value != str(original.get("title") or "").strip()
                or prompt_value != str(original.get("prompt") or "").strip()
                or group_value != str(original.get("prompt_group") or DEFAULT_PROMPT_GROUP).strip()
            ):
                updates.append(
                    (
                        prompt_id,
                        {
                            "title": title_value,
                            "prompt": prompt_value,
                            "prompt_group": group_value,
                        },
                    )
                )
        else:
            if not title_value and not prompt_value:
                continue
            if not title_value or not prompt_value:
                invalid_rows.append(idx + 1)
                continue
            creations.append(
                {
                    "title": title_value,
                    "prompt": prompt_value,
                    "prompt_group": group_value,
                }
            )
    return updates, creations, invalid_rows


def _render_prompt_editor(client: SupabaseClient, original_rows: List[dict], edited_rows: List[dict]):
    if not _can_edit_prompts():
        return
    updates, creations, invalid_rows = _collect_prompt_changes(original_rows, edited_rows)
    if invalid_rows:
        st.error(f"Rows {', '.join(map(str, invalid_rows))} need both a title and prompt.")
        return
    if not updates and not creations:
        st.caption("Update prompts inline or add new rows, then click save.")
        return
    save_label = f"Save {len(updates) + len(creations)} change(s)"
    if st.button(save_label, key="save_prompt_updates"):
        with st.spinner("Saving prompt changes..."):
            for prompt_id, payload in updates:
                updated = client.update_question_prompt(prompt_id=prompt_id, updates=payload)
                if not updated:
                    st.error(f"Unable to update prompt #{prompt_id}.")
                    return
            for payload in creations:
                inserted = client.insert_question_prompt(
                    title=payload["title"],
                    prompt=payload["prompt"],
                    prompt_group=payload["prompt_group"],
                    status=DEFAULT_STATUS,
                )
                if not inserted:
                    st.error(f"Unable to add prompt '{payload['title']}'.")
                    return
        st.success("Prompts saved.")
        st.rerun()


def show_question_prompts_page():
    st.title("Question Prompts")
    client = _build_client()
    if not client:
        st.error("Supabase credentials are missing.")
        return

    prompts = _load_prompts(client, DEFAULT_STATUS)
    selected_group, filter_label = _render_prompt_filters(prompts)
    visible_prompts, edited_prompts = _render_prompt_table(prompts, selected_group, filter_label)
    _render_prompt_editor(client, visible_prompts, edited_prompts)
