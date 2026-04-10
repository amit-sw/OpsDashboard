from datetime import date, timedelta
import os
from collections import defaultdict

import pandas as pd
import streamlit as st

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from utils.gmail_backfill_ids import backfill_index_for_date_range
from utils.gmail_get_contents import fetch_and_store_messages_for_day

from utils.supabase_integration import SupabaseClient
from utils.gmail_creds import GmailOAuthManager, OAuthSettings, SupabaseTokenStore

def gmail_service(creds: Credentials):
    return build("gmail", "v1", credentials=creds, cache_discovery=False)

def _iter_ymd_range(start_date: date, end_date: date):
    current = start_date
    while current <= end_date:
        yield current.isoformat()
        current += timedelta(days=1)


def _gmail_range_coverage(supabase: SupabaseClient, start_date: date, end_date: date):
    rows = supabase.list_gmail_index_rows_by_range(start_date.isoformat(), end_date.isoformat())
    ids_by_day = defaultdict(list)
    all_ids = []
    for row in rows:
        ymd = str(row.get("ymd") or "")
        msg_id = row.get("id")
        if not ymd or not msg_id:
            continue
        ids_by_day[ymd].append(msg_id)
        all_ids.append(msg_id)

    existing_messages = supabase.get_existing_gmail_message_ids(all_ids)
    summary_rows = []
    for ymd in _iter_ymd_range(start_date, end_date):
        indexed_ids = ids_by_day.get(ymd, [])
        indexed_count = len(indexed_ids)
        fetched_count = sum(1 for msg_id in indexed_ids if msg_id in existing_messages)
        summary_rows.append(
            {
                "date": ymd,
                "indexed_ids": indexed_count,
                "fetched_messages": fetched_count,
                "missing_messages": max(indexed_count - fetched_count, 0),
                "status": (
                    "No index yet"
                    if indexed_count == 0
                    else "Fully fetched"
                    if fetched_count == indexed_count
                    else "Needs fetch"
                ),
            }
        )
    df = pd.DataFrame(summary_rows)
    totals = {
        "indexed_ids": int(df["indexed_ids"].sum()) if not df.empty else 0,
        "fetched_messages": int(df["fetched_messages"].sum()) if not df.empty else 0,
        "missing_messages": int(df["missing_messages"].sum()) if not df.empty else 0,
        "days_without_index": int((df["indexed_ids"] == 0).sum()) if not df.empty else 0,
    }
    return df, totals


def show_gmail_fetch_control():
    st.title("GMAIL Fetch control")
    supabase = SupabaseClient(os.getenv('SUPABASE_URL'),os.getenv('SUPABASE_KEY'))
    if not supabase or not getattr(supabase, "supabase", None):
        st.error("Supabase credentials are missing.")
        return

    store = SupabaseTokenStore(supabase) 
    manager = GmailOAuthManager(OAuthSettings.from_secrets(), store)
    creds = manager.credentials()

    if not creds or not creds.valid:
        st.error("Authorize Gmail access first on the GMail Creds page.")
        return

    default_end = date.today()
    default_start = default_end - timedelta(days=6)

    st.caption("Backfill Gmail message IDs and fetch full message content into Supabase for any date range.")
    start_date = st.date_input("Start date", value=default_start)
    end_date = st.date_input("End date", value=default_end)
    include_spam_trash = st.checkbox("Include Spam and Trash", value=False)
    fetch_bodies = st.checkbox("Fetch full message bodies", value=True)

    if start_date > end_date:
        st.error("Start date must be on or before end date.")
        return

    total_days = (end_date - start_date).days + 1
    st.caption(f"Selected range: {total_days} day(s)")

    coverage_df, coverage_totals = _gmail_range_coverage(supabase, start_date, end_date)
    metric1, metric2, metric3, metric4 = st.columns(4)
    metric1.metric("Indexed IDs", coverage_totals["indexed_ids"])
    metric2.metric("Fetched Messages", coverage_totals["fetched_messages"])
    metric3.metric("Missing Messages", coverage_totals["missing_messages"])
    metric4.metric("Days Without Index", coverage_totals["days_without_index"])

    with st.expander("Coverage for selected date range", expanded=True):
        st.caption("Use this to decide whether you need to backfill the Gmail index, fetch message bodies, or both.")
        st.dataframe(coverage_df, use_container_width=True, hide_index=True)

    service = gmail_service(creds)
    col1, col2, col3 = st.columns(3)

    with col1:
        run_index = st.button("Backfill Gmail index", use_container_width=True)
    with col2:
        run_fetch = st.button("Fetch indexed emails", use_container_width=True)
    with col3:
        run_both = st.button("Backfill and fetch", use_container_width=True, type="primary")

    if run_index or run_both:
        index_stats_placeholder = st.empty()
        with st.spinner("Backfilling Gmail message index...", show_time=True):
            index_stats = backfill_index_for_date_range(
                service,
                start_date,
                end_date,
                include_spam_trash=include_spam_trash,
            )
        index_stats_placeholder.info(
            "Index backfill finished. "
            f"Found {index_stats['gmail_ids_found']} Gmail ids, "
            f"inserted {index_stats['inserted']} new index rows, "
            f"skipped {index_stats['already_in_supabase']} already in Supabase, "
            f"and ignored {index_stats['duplicates_in_scan']} duplicates within the scan."
        )
        st.success("Gmail message index updated.")

    if run_fetch or run_both:
        total_attempted = 0
        total_inserted = 0
        total_existing = 0
        total_indexed = 0
        progress = st.progress(0.0)
        status = st.empty()
        day_rows = []
        for idx, ymd in enumerate(_iter_ymd_range(start_date, end_date), start=1):
            status.write(f"Fetching Gmail messages for {ymd} ({idx}/{total_days})")
            with st.spinner(f"For {ymd}", show_time=True):
                fetch_stats = fetch_and_store_messages_for_day(supabase, service, ymd, fetch_bodies)
            total_indexed += fetch_stats["indexed_for_day"]
            total_attempted += fetch_stats["attempted_upserts"]
            total_inserted += fetch_stats["inserted"]
            total_existing += fetch_stats["already_in_supabase"]
            day_rows.append(
                {
                    "date": ymd,
                    "indexed_ids": fetch_stats["indexed_for_day"],
                    "attempted_upserts": fetch_stats["attempted_upserts"],
                    "new_rows": fetch_stats["inserted"],
                    "already_present": fetch_stats["already_in_supabase"],
                }
            )
            status.write(
                f"{ymd}: indexed {fetch_stats['indexed_for_day']}, "
                f"new {fetch_stats['inserted']}, already present {fetch_stats['already_in_supabase']}"
            )
            progress.progress(idx / total_days)
        status.write(f"Finished fetching indexed Gmail messages for {total_days} day(s).")
        st.success(
            f"Processed {total_indexed} indexed ids across {total_days} day(s): "
            f"{total_inserted} new rows written, {total_existing} already present, "
            f"{total_attempted} total upserts attempted."
        )
        with st.expander("Per-day fetch results", expanded=True):
            st.dataframe(pd.DataFrame(day_rows), use_container_width=True, hide_index=True)

    
