import streamlit as st
from utils.supabase_integration import SupabaseClient
import os
from utils.utils_credentials import setup_env_from_dict
from datetime import datetime, timezone, timedelta

def get_zoom_session(session_id):
    env_secrets=st.secrets.get("env")  
    #print(f"DEBUG: ENV Secrets: {env_secrets=}")  
    if env_secrets:
        setup_env_from_dict(env_secrets)

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key=os.environ['SUPABASE_KEY']

    supabase=SupabaseClient(supabase_url, supabase_key)
    zoom_session=supabase.get_zoom_session(session_id) # created_at:2025-11-27 02:02:56.964265+00


    return zoom_session[0]

def use_st_state(): 
    print("AAA")   
    

user_record=get_zoom_session('xxx')
st.json(user_record)
st.session_state.user_record=user_record
#set_st_state()
current_time = datetime.now(timezone.utc) - timedelta(days=30)
trial_expiry_str = user_record.get('created_at', current_time)
trial_expiry = datetime.fromisoformat(trial_expiry_str.replace("Z", "+00:00"))
if trial_expiry.tzinfo is None:
    trial_expiry = trial_expiry.replace(tzinfo=timezone.utc)
print(f"CHECK: {trial_expiry=}, {current_time=}")
dt = trial_expiry
if dt > current_time:
    print("Greater")
else:
    print("Not greater")