import streamlit as st
import os

import base64
import datetime
import pandas as pd

from utils.utils_aws import setup_env_from_dict
from utils.supabase_integration import SupabaseClient

from src.show_fetch_zoom_aws import process_one_day_fetch_selection, process_one_day_qna
        
def show_cron_processing():
    env_secrets=st.secrets.get("env")  
    if env_secrets:
        setup_env_from_dict(env_secrets)
    supabase = SupabaseClient(url=os.environ["SUPABASE_URL"], key=os.environ['SUPABASE_KEY'])
        
    cronId=st.query_params.get("cronId")
    duration=st.query_params.get("duration")
    
    end_date = datetime.date.today()+datetime.timedelta(days=1)
    start_date = end_date - datetime.timedelta(days=int(duration))
        
    current_date=start_date
    while current_date <= end_date:
        date_str=current_date.strftime("%Y-%m-%d")
        print(f"DEBUG: Selected date: {date_str}")
        if cronId=="Sessions":
            rows= process_one_day_fetch_selection(date_str)
        if cronId=="QnA":
            rows = process_one_day_qna(supabase, date_str)

        df = pd.DataFrame(rows)
        with st.expander(f"Data {cronId} for {date_str}"):
            st.dataframe(df)
        current_date += datetime.timedelta(days=1)