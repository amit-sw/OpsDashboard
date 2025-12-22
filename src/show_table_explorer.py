import os
from typing import Dict, List

import pandas as pd
import streamlit as st

from utils.supabase_integration import SupabaseClient


TABLE_CACHE_KEY = "table_viewer_cache"


def _build_client() -> SupabaseClient | None:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        return None
    return SupabaseClient(url=url, key=key)


def _load_rows(client: SupabaseClient, table_name: str, limit: int) -> List[Dict]:
    cache: Dict[str, List[Dict]] = st.session_state.setdefault(TABLE_CACHE_KEY, {})
    cache_key = f"{table_name}:{limit}"
    should_refresh = st.button("Refresh data", key=f"refresh_{table_name}")
    if should_refresh or cache_key not in cache:
        with st.spinner("Loading rows from Supabase..."):
            cache[cache_key] = client.fetch_table_rows(table_name, limit)
    return cache.get(cache_key, [])


def show_table_explorer():
    st.title("Supabase Table Explorer")
    client = _build_client()
    if not client:
        st.error("Supabase credentials are missing; set SUPABASE_URL and SUPABASE_KEY.")
        return

    tables = client.list_known_tables()
    if not tables:
        st.info("No Supabase tables were registered yet.")
        return

    with st.sidebar:
        st.subheader("Table Explorer Filters")
        selected = st.selectbox("Select a table", tables)
        row_limit = st.slider("Rows to display", 25, 1000, value=200, step=25)
    rows = _load_rows(client, selected, row_limit)
    df = pd.DataFrame(rows)

    st.caption(f"Showing {len(df)} rows from {selected} (limit {row_limit}).")
    if df.empty:
        st.info("No data returned for this table.")
    st.dataframe(df)
