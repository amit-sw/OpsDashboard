from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os

import pandas as pd
import streamlit as st

from utils.supabase_integration import SupabaseClient


def _can_view_recent_sessions() -> bool:
    return st.session_state.get("current_user_role") == "superadmin"


def _get_cutoff_utc(now: datetime | None = None) -> datetime:
    current = now or datetime.now(timezone.utc)
    return current - timedelta(hours=24)


def _format_cutoff(cutoff: datetime) -> str:
    return cutoff.isoformat()


def _fetch_recent_sessions(supabase_client: SupabaseClient, cutoff: datetime):
    try:
        response = (
            supabase_client.supabase
            .table("zoom_sessions")
            .select("topic,date,session_id")
            .gte("date", _format_cutoff(cutoff))
            .order("date", desc=True)
            .execute()
        )
        return response.data or []
    except Exception as exc:
        st.error(f"An error occurred while fetching recent sessions: {exc}")
        return []


def show_recent_sessions_page():
    st.title("New Sessions (Last 24 Hours)")
    if not _can_view_recent_sessions():
        st.error("This page is restricted to Super Admins.")
        return

    supabase_client = SupabaseClient(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_KEY"),
    )
    cutoff = _get_cutoff_utc()
    st.caption(f"Showing sessions since {cutoff:%Y-%m-%d %H:%M UTC}")

    with st.spinner("Fetching results from Supabase…", show_time=True):
        sessions = _fetch_recent_sessions(supabase_client, cutoff)

    if not sessions:
        st.info("No sessions found in the last 24 hours.")
        return

    df = pd.DataFrame(sessions)
    df["URL"] = "/show_zoom_detail_page?q=" + df["session_id"]
    st.dataframe(
        df,
        column_config={"URL": st.column_config.LinkColumn("URL", display_text="Session details")},
        hide_index=True,
    )
