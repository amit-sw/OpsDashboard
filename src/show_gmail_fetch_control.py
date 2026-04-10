from datetime import date, timedelta
import os
from collections import defaultdict
import time

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


def _gmail_messages_for_range(supabase: SupabaseClient, start_date: date, end_date: date):
    index_rows = supabase.list_gmail_index_rows_by_range(start_date.isoformat(), end_date.isoformat())
    if not index_rows:
        return pd.DataFrame()
    ymd_by_id = {
        row.get("id"): str(row.get("ymd") or "")
        for row in index_rows
        if row.get("id")
    }
    message_rows = supabase.list_gmail_messages_by_ids(list(ymd_by_id.keys()))
    display_rows = []
    for row in message_rows:
        headers = row.get("headers") or {}
        display_rows.append(
            {
                "date": ymd_by_id.get(row.get("id"), ""),
                "from": headers.get("From", ""),
                "to": headers.get("To", ""),
                "subject": headers.get("Subject", ""),
                "snippet": row.get("snippet", ""),
                "body_full": row.get("body_full", ""),
            }
        )
    if not display_rows:
        return pd.DataFrame()
    df = pd.DataFrame(display_rows)
    return df.sort_values(by=["date", "subject"], ascending=[True, True]).reset_index(drop=True)


def _format_eta(seconds_remaining: float):
    if seconds_remaining <= 0:
        return "less than 1 second"
    total_seconds = int(seconds_remaining)
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes}m {seconds}s"
    if minutes:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


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

    st.caption("Choose a date range, then either pull Gmail into Supabase or review what is already stored there.")
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
        st.caption("This shows what is already indexed and fetched in Supabase for the selected dates.")
        st.dataframe(coverage_df, use_container_width=True, hide_index=True)

    service = gmail_service(creds)
    st.markdown("**Actions**")
    action_col1, action_col2 = st.columns(2)

    with action_col1:
        st.caption("Fetch from Gmail and store in Supabase")
        st.caption("Discovers message IDs for the selected dates, then saves the matching email content into the database.")
        run_sync = st.button("Sync Gmail to database", use_container_width=True, type="primary")

    with action_col2:
        st.caption("Show what is already in Supabase")
        st.caption("Loads email rows already stored in the database for the selected date range without calling Gmail.")
        run_show_db = st.button("Show stored database messages", use_container_width=True)

    if run_sync:
        run_started = time.time()
        index_stats_placeholder = st.empty()
        live_metrics = st.empty()
        live_status = st.empty()
        live_table = st.empty()
        overall_progress = st.progress(0.0)
        live_rows = []
        cumulative = {
            "indexed_seen": 0,
            "processed_messages": 0,
            "new_rows": 0,
            "already_present": 0,
            "attempted_upserts": 0,
        }

        def render_live_progress(current_stage: str, current_day: str = ""):
            elapsed = time.time() - run_started
            processed = max(cumulative["processed_messages"], cumulative["indexed_seen"], 0)
            total_target = max(coverage_totals["missing_messages"], coverage_totals["indexed_ids"], 1)
            rate = processed / elapsed if elapsed > 0 else 0
            remaining = max(total_target - processed, 0)
            eta = _format_eta(remaining / rate) if rate > 0 else "estimating..."
            m1, m2, m3, m4 = live_metrics.columns(4)
            m1.metric("Processed so far", processed)
            m2.metric("New rows", cumulative["new_rows"])
            m3.metric("Already present", cumulative["already_present"])
            m4.metric("ETA", eta)
            prefix = f"{current_day}: " if current_day else ""
            live_status.info(
                f"{prefix}{current_stage}. "
                f"Processed {processed} items so far in {int(elapsed)}s. "
                f"Estimated time remaining: {eta}."
            )
            if live_rows:
                live_table.dataframe(pd.DataFrame(live_rows), use_container_width=True, hide_index=True)

        def on_index_progress(payload):
            cumulative["indexed_seen"] = payload.get("gmail_ids_found", cumulative["indexed_seen"])
            cumulative["new_rows"] = payload.get("inserted", cumulative["new_rows"])
            cumulative["already_present"] = payload.get("already_in_supabase", cumulative["already_present"])
            cumulative["attempted_upserts"] = payload.get("attempted_upserts", cumulative["attempted_upserts"])
            overall_progress.progress(min(cumulative["indexed_seen"] / max(coverage_totals["indexed_ids"], 1), 0.25))
            render_live_progress("Discovering message ids")

        with st.spinner("Discovering Gmail messages for the selected date range...", show_time=True):
            index_stats = backfill_index_for_date_range(
                service,
                start_date,
                end_date,
                include_spam_trash=include_spam_trash,
                progress_callback=on_index_progress,
            )
        index_stats_placeholder.info(
            "Discovery finished. "
            f"Found {index_stats['gmail_ids_found']} Gmail ids, "
            f"inserted {index_stats['inserted']} new index rows, "
            f"skipped {index_stats['already_in_supabase']} already in Supabase, "
            f"and ignored {index_stats['duplicates_in_scan']} duplicates within the scan."
        )

        total_attempted = 0
        total_inserted = 0
        total_existing = 0
        total_indexed = 0
        day_rows = []
        for idx, ymd in enumerate(_iter_ymd_range(start_date, end_date), start=1):
            current_row = {
                "date": ymd,
                "indexed_ids": 0,
                "processed_messages": 0,
                "attempted_upserts": 0,
                "new_rows": 0,
                "already_present": 0,
            }
            day_rows.append(current_row)

            def on_fetch_progress(payload, row=current_row):
                row["indexed_ids"] = payload.get("indexed_for_day", row["indexed_ids"])
                row["processed_messages"] = payload.get("processed_messages", row["processed_messages"])
                row["attempted_upserts"] = payload.get("attempted_upserts", row["attempted_upserts"])
                row["new_rows"] = payload.get("inserted", row["new_rows"])
                row["already_present"] = payload.get("already_in_supabase", row["already_present"])
                cumulative["processed_messages"] = total_indexed + row["processed_messages"]
                cumulative["new_rows"] = total_inserted + row["new_rows"]
                cumulative["already_present"] = total_existing + row["already_present"]
                cumulative["attempted_upserts"] = total_attempted + row["attempted_upserts"]
                progress_fraction = (idx - 1 + (row["processed_messages"] / max(row["indexed_ids"], 1))) / max(total_days, 1)
                overall_progress.progress(max(0.25, min(progress_fraction, 1.0)))
                render_live_progress("Fetching message content", current_day=ymd)

            with st.spinner(f"For {ymd}", show_time=True):
                fetch_stats = fetch_and_store_messages_for_day(
                    supabase,
                    service,
                    ymd,
                    fetch_bodies,
                    progress_callback=on_fetch_progress,
                )
            total_indexed += fetch_stats["indexed_for_day"]
            total_attempted += fetch_stats["attempted_upserts"]
            total_inserted += fetch_stats["inserted"]
            total_existing += fetch_stats["already_in_supabase"]
            current_row.update(
                {
                    "indexed_ids": fetch_stats["indexed_for_day"],
                    "processed_messages": fetch_stats["processed_messages"],
                    "attempted_upserts": fetch_stats["attempted_upserts"],
                    "new_rows": fetch_stats["inserted"],
                    "already_present": fetch_stats["already_in_supabase"],
                }
            )
            cumulative["processed_messages"] = total_indexed
            cumulative["new_rows"] = total_inserted
            cumulative["already_present"] = total_existing
            cumulative["attempted_upserts"] = total_attempted
            overall_progress.progress(idx / max(total_days, 1))
            render_live_progress("Finished day", current_day=ymd)
        live_status.success(f"Finished fetching indexed Gmail messages for {total_days} day(s).")
        st.success(
            f"Processed {total_indexed} indexed ids across {total_days} day(s): "
            f"{total_inserted} new rows written, {total_existing} already present, "
            f"{total_attempted} total upserts attempted."
        )
        with st.expander("Per-day fetch results", expanded=True):
            st.dataframe(pd.DataFrame(day_rows), use_container_width=True, hide_index=True)

    if run_show_db:
        stored_df = _gmail_messages_for_range(supabase, start_date, end_date)
        if stored_df.empty:
            st.info("No stored Gmail messages were found in Supabase for this date range yet.")
        else:
            st.success(f"Loaded {len(stored_df)} stored Gmail messages from Supabase.")
            st.dataframe(stored_df, use_container_width=True, hide_index=True)
