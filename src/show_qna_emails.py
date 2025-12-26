import os
from typing import List

import streamlit as st

from utils.supabase_integration import SupabaseClient

DEFAULT_PROMPT_GROUP = "common"
ALLOWED_QNA_ROLES = {"financeadmin", "superadmin"}


def _build_client() -> SupabaseClient | None:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        return None
    return SupabaseClient(url=url, key=key)


def _user_role() -> str:
    return st.session_state.get("current_user_role", "guest")


def _can_manage_qna_emails() -> bool:
    return _user_role() in ALLOWED_QNA_ROLES


def _normalize_prompt_group(value: str) -> str:
    """Return a lowercase prompt group, defaulting to 'common'."""
    cleaned = (value or "").strip()
    return cleaned or DEFAULT_PROMPT_GROUP


def _normalize_email(value: str) -> str:
    return (value or "").strip().lower()


def _validate_email(value: str) -> str | None:
    """Return a normalized email when valid, otherwise None."""
    email = _normalize_email(value)
    if not email or "@" not in email:
        return None
    domain = email.split("@", maxsplit=1)[-1]
    if "." not in domain:
        return None
    return email


def _load_qna_rows(client: SupabaseClient) -> List[dict]:
    with st.spinner("Loading QnA email recipients..."):
        return client.list_qna_emails()


def _render_qna_table(rows: List[dict]):
    st.subheader("Current recipients")
    if not rows:
        st.info("No recipients have been added yet.")
        return
    st.caption(f"Showing {len(rows)} rows.")
    st.dataframe(rows)


def _render_new_recipient_form(client: SupabaseClient):
    st.subheader("Add a recipient")
    with st.form("create_qna_email"):
        prompt_group = st.text_input("Prompt group", value=DEFAULT_PROMPT_GROUP)
        email = st.text_input("Email address")
        submitted = st.form_submit_button("Add recipient")
    if not submitted:
        return
    normalized_group = _normalize_prompt_group(prompt_group)
    normalized_email = _validate_email(email)
    if not normalized_email:
        st.error("Enter a valid email address (example@example.com).")
        return
    with st.spinner("Saving recipient..."):
        inserted = client.insert_qna_email(
            prompt_group=normalized_group,
            email=normalized_email,
        )
    if inserted:
        st.success("Recipient added.")
        st.rerun()
    else:
        st.error("Unable to add recipient. Check logs for details.")


def _render_edit_recipient_form(client: SupabaseClient, rows: List[dict]):
    editable = [row for row in rows if row.get("id")]
    if not editable:
        return
    st.subheader("Edit an existing recipient")
    options = {
        f"{row.get('prompt_group', DEFAULT_PROMPT_GROUP)} · {row.get('email', '')} (#{row.get('id')})": row
        for row in editable
    }
    label = st.selectbox("Select a recipient", list(options.keys()))
    selected = options.get(label)
    if not selected:
        return
    record_id = selected.get("id")
    with st.form(f"edit_qna_email_{record_id}"):
        updated_group = st.text_input(
            "Prompt group",
            value=selected.get("prompt_group", DEFAULT_PROMPT_GROUP),
            key=f"edit_qna_group_{record_id}",
        )
        updated_email = st.text_input(
            "Email address",
            value=selected.get("email", ""),
            key=f"edit_qna_email_{record_id}",
        )
        submitted = st.form_submit_button("Save changes")
    if not submitted:
        return
    normalized_group = _normalize_prompt_group(updated_group)
    normalized_email = _validate_email(updated_email)
    if not normalized_email:
        st.error("Enter a valid email address.")
        return
    with st.spinner("Updating recipient..."):
        updated = client.update_qna_email(
            record_id=record_id,
            updates={
                "prompt_group": normalized_group,
                "email": normalized_email,
            },
        )
    if updated:
        st.success("Recipient updated.")
        st.rerun()
    else:
        st.error("Unable to update recipient. Check logs for details.")


def show_qna_emails_page():
    st.title("QnA Email Recipients")
    if not _can_manage_qna_emails():
        st.info("Only Finance Admins and Super Admins can edit QnA email recipients.")
        return
    client = _build_client()
    if not client:
        st.error("Supabase credentials are missing.")
        return
    rows = _load_qna_rows(client)
    _render_qna_table(rows)
    _render_edit_recipient_form(client, rows)
    _render_new_recipient_form(client)
