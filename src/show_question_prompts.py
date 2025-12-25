import os
from typing import List

import streamlit as st

from utils.supabase_integration import SupabaseClient

DEFAULT_STATUS = "active"
DEFAULT_PROMPT_GROUP = "common"
EDITOR_ROLES = {"financeadmin", "superadmin"}


def _build_client() -> SupabaseClient | None:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        return None
    return SupabaseClient(url=url, key=key)


def _load_prompts(client: SupabaseClient, status: str) -> List[dict]:
    with st.spinner("Loading prompts from Supabase..."):
        return client.list_question_prompts(status=status)


def _render_prompt_filters(prompts: List[dict]) -> tuple[str, str, str]:
    groups = sorted({row.get("prompt_group", DEFAULT_PROMPT_GROUP) for row in prompts} - {""})
    filter_label = "All groups"
    options = [filter_label] + (groups or [DEFAULT_PROMPT_GROUP])
    selected = st.selectbox("Filter by prompt group", options)
    current_group = selected if selected != filter_label else DEFAULT_PROMPT_GROUP
    return selected, current_group, filter_label


def _render_prompt_table(prompts: List[dict], selected_group: str, filter_label: str) -> List[dict]:
    filtered = [
        row for row in prompts if selected_group == filter_label or row.get("prompt_group") == selected_group
    ]
    st.caption(f"Showing {len(filtered)} prompts.")
    st.dataframe(filtered)
    return filtered


def _user_role() -> str:
    return st.session_state.get("current_user_role", "guest")


def _can_edit_prompts() -> bool:
    return _user_role() in EDITOR_ROLES


def _render_prompt_form(client: SupabaseClient, default_group: str):
    st.subheader("Add a new question prompt")
    with st.form("new_question_prompt"):
        title = st.text_input("New prompt title").strip()
        prompt_body = st.text_area("New prompt body", height=150).strip()
        prompt_group = st.text_input("New prompt group", value=default_group).strip() or DEFAULT_PROMPT_GROUP
        submitted = st.form_submit_button("Save prompt")

    if not submitted:
        return
    if not title or not prompt_body:
        st.error("Title and prompt are required.")
        return
    with st.spinner("Saving prompt..."):
        inserted = client.insert_question_prompt(
            title=title,
            prompt=prompt_body,
            prompt_group=prompt_group,
            status=DEFAULT_STATUS,
        )
    if inserted:
        st.success("Prompt saved.")
        st.rerun()
    else:
        st.error("Unable to save prompt. Check logs for details.")


def _render_prompt_editor(client: SupabaseClient, prompts: List[dict]):
    if not _can_edit_prompts():
        return
    editable = [row for row in prompts if row.get("id")]
    st.subheader("Edit an existing prompt")
    if not editable:
        st.info("No prompts are available to edit yet.")
        return
    option_map = {
        f"{row.get('title', '(untitled)')} · {row.get('prompt_group', DEFAULT_PROMPT_GROUP)} (#{row.get('id')})": row
        for row in editable
    }
    option_labels = list(option_map.keys())
    selected_label = st.selectbox("Select a prompt to edit", option_labels, key="prompt_edit_selector")
    selected = option_map.get(selected_label)
    if not selected:
        return
    prompt_id = selected.get("id")
    with st.form(f"edit_question_prompt_{prompt_id}"):
        new_title = st.text_input(
            "Updated title",
            value=selected.get("title", ""),
            key=f"edit_prompt_title_{prompt_id}",
        )
        new_prompt = st.text_area(
            "Updated prompt",
            value=selected.get("prompt", ""),
            height=150,
            key=f"edit_prompt_body_{prompt_id}",
        )
        new_group = st.text_input(
            "Updated prompt group",
            value=selected.get("prompt_group", DEFAULT_PROMPT_GROUP),
            key=f"edit_prompt_group_{prompt_id}",
        )
        submitted = st.form_submit_button("Update prompt")
    if not submitted:
        return
    title_value = new_title.strip()
    prompt_value = new_prompt.strip()
    group_value = new_group.strip() or DEFAULT_PROMPT_GROUP
    if not title_value or not prompt_value:
        st.error("Title and prompt are required.")
        return
    with st.spinner("Updating prompt..."):
        updated = client.update_question_prompt(
            prompt_id=prompt_id,
            updates={
                "title": title_value,
                "prompt": prompt_value,
                "prompt_group": group_value,
            },
        )
    if updated:
        st.success("Prompt updated.")
        st.rerun()
    else:
        st.error("Unable to update prompt. Check logs for details.")


def show_question_prompts_page():
    st.title("Question Prompts")
    client = _build_client()
    if not client:
        st.error("Supabase credentials are missing.")
        return

    prompts = _load_prompts(client, DEFAULT_STATUS)
    selected_group, current_group, filter_label = _render_prompt_filters(prompts)
    visible_prompts = _render_prompt_table(prompts, selected_group, filter_label)
    _render_prompt_editor(client, visible_prompts)
    _render_prompt_form(client, current_group)
