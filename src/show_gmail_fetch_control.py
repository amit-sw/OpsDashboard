from datetime import date, timedelta
import os
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

    service = gmail_service(creds)
    col1, col2, col3 = st.columns(3)

    with col1:
        run_index = st.button("Backfill Gmail index", use_container_width=True)
    with col2:
        run_fetch = st.button("Fetch indexed emails", use_container_width=True)
    with col3:
        run_both = st.button("Backfill and fetch", use_container_width=True, type="primary")

    if run_index or run_both:
        with st.spinner("Backfilling Gmail message index...", show_time=True):
            backfill_index_for_date_range(
                service,
                start_date,
                end_date,
                include_spam_trash=include_spam_trash,
            )
        st.success("Gmail message index updated.")

    if run_fetch or run_both:
        total_inserted = 0
        progress = st.progress(0.0)
        status = st.empty()
        for idx, ymd in enumerate(_iter_ymd_range(start_date, end_date), start=1):
            status.write(f"Fetching Gmail messages for {ymd} ({idx}/{total_days})")
            with st.spinner(f"For {ymd}", show_time=True):
                inserted = fetch_and_store_messages_for_day(supabase, service, ymd, fetch_bodies)
            total_inserted += inserted
            progress.progress(idx / total_days)
        status.write(f"Finished fetching indexed Gmail messages for {total_days} day(s).")
        st.success(f"Stored or refreshed {total_inserted} Gmail message rows across {total_days} day(s).")

    
