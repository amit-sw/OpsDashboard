import os
import streamlit as st

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.errors import HttpError
from googleapiclient.discovery import build

from utils.gmail_backfill_ids import backfill_index_last_six_months
from utils.gmail_get_contents import fetch_and_store_messages_for_day

from utils.supabase_integration import SupabaseClient
from utils.gmail_creds import GmailOAuthManager, TokenStore, OAuthSettings, SupabaseTokenStore

def gmail_service(creds: Credentials):
    return build("gmail", "v1", credentials=creds, cache_discovery=False)

def show_gmail_fetch_control():
    st.title("GMAIL Fetch control")
    supabase = SupabaseClient(os.getenv('SUPABASE_URL'),os.getenv('SUPABASE_KEY'))
    store = SupabaseTokenStore(supabase) 
    manager = GmailOAuthManager(OAuthSettings.from_secrets(), store)
    creds = manager.credentials()
    
    #if st.button("Run Backfill"):
    #    backfill_index_last_six_months(gmail_service(creds),1,False)
    st.divider()
    month=st.pills("Month", ["03","04","05","06","07","08","09"])
    if month:
        if st.button("Fetch emails"):
            for days in range(1,32):
                ymd="2025-"+month+f"-{days:02}"
                #st.write(f"Now running for date: {ymd}")
                with st.spinner(f"For {ymd}",show_time=True):
                    i=fetch_and_store_messages_for_day(supabase, gmail_service(creds),ymd,True)
                    st.sidebar.write(f"Fetched {i} records for {ymd}")
                
            


    