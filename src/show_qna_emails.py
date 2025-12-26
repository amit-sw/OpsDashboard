import math
import os
from typing import List

import pandas as pd
import streamlit as st

from utils.supabase_integration import SupabaseClient

DEFAULT_PROMPT_GROUP = "common"
ALLOWED_QNA_ROLES = {"financeadmin", "superadmin"}


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


def _render_qna_table(rows: List[dict]) -> tuple[List[dict], List[dict]]:
    st.subheader("Current recipients")
    table_df = pd.DataFrame(rows)
    required_columns = ["id", "prompt_group", "email"]
    for column in required_columns:
        if column not in table_df:
            table_df[column] = "" if column != "id" else None
    st.caption(f"Showing {len(rows)} rows.")
    if not rows:
        st.info("No recipients yet. Add rows below to create the first entry.")
    editor_value = st.data_editor(
        table_df,
        hide_index=True,
        use_container_width=True,
        key="qna_email_editor",
        disabled=False if _can_manage_qna_emails() else True,
        column_config={"id": st.column_config.NumberColumn("ID", disabled=True)},
        num_rows="dynamic" if _can_manage_qna_emails() else "fixed",
    )
    edited_rows = editor_value.to_dict("records")
    return rows, edited_rows


def _collect_qna_changes(
    original_rows: List[dict], edited_rows: List[dict]
) -> tuple[List[tuple[int, dict]], List[dict], List[int], List[int]]:
    original_map = {}
    for row in original_rows:
        row_id = _coerce_int(row.get("id"))
        if row_id is not None:
            original_map[row_id] = row
    updates: List[tuple[int, dict]] = []
    creations: List[dict] = []
    invalid_email_rows: List[int] = []
    missing_email_rows: List[int] = []
    for idx, row in enumerate(edited_rows):
        record_id = _coerce_int(row.get("id"))
        raw_group = str(row.get("prompt_group") or "")
        group_value = _normalize_prompt_group(raw_group)
        email_value_raw = row.get("email", "")
        normalized_email = _normalize_email(email_value_raw)
        if record_id and record_id in original_map:
            original = original_map[record_id]
            if (
                group_value != _normalize_prompt_group(original.get("prompt_group", DEFAULT_PROMPT_GROUP))
                or normalized_email != _normalize_email(original.get("email"))
            ):
                if not normalized_email:
                    missing_email_rows.append(idx + 1)
                    continue
                valid_email = _validate_email(normalized_email)
                if not valid_email:
                    invalid_email_rows.append(idx + 1)
                    continue
                updates.append(
                    (
                        record_id,
                        {
                            "prompt_group": group_value,
                            "email": valid_email,
                        },
                    )
                )
        else:
            if not raw_group.strip() and not normalized_email:
                continue
            if not normalized_email:
                missing_email_rows.append(idx + 1)
                continue
            validated_email = _validate_email(normalized_email)
            if not validated_email:
                invalid_email_rows.append(idx + 1)
                continue
            creations.append(
                {
                    "prompt_group": group_value or DEFAULT_PROMPT_GROUP,
                    "email": validated_email,
                }
            )
    return updates, creations, invalid_email_rows, missing_email_rows


def _render_edit_recipient_form(client: SupabaseClient, original_rows: List[dict], edited_rows: List[dict]):
    if not _can_manage_qna_emails():
        return
    updates, creations, invalid_rows, missing_rows = _collect_qna_changes(original_rows, edited_rows)
    if missing_rows:
        st.error(f"Rows {', '.join(map(str, missing_rows))} need an email address.")
        return
    if invalid_rows:
        st.error(f"Rows {', '.join(map(str, invalid_rows))} contain invalid email addresses.")
        return
    if not updates and not creations:
        st.caption("Edit rows or add new recipients inline, then click save.")
        return
    save_label = f"Save {len(updates) + len(creations)} change(s)"
    if st.button(save_label, key="save_qna_email_updates"):
        with st.spinner("Saving QnA recipients..."):
            for record_id, payload in updates:
                updated = client.update_qna_email(record_id=record_id, updates=payload)
                if not updated:
                    st.error(f"Unable to update recipient #{record_id}.")
                    return
            for payload in creations:
                inserted = client.insert_qna_email(
                    prompt_group=payload["prompt_group"],
                    email=payload["email"],
                )
                if not inserted:
                    st.error(f"Unable to add recipient '{payload['email']}'.")
                    return
        st.success("Recipients saved.")
        st.rerun()


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
    original_rows, edited_rows = _render_qna_table(rows)
    _render_edit_recipient_form(client, original_rows, edited_rows)
