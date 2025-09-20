import streamlit as st
import os

from utils.utils_credentials import setup_env_from_dict
from utils.calendar_integration import CalendarClient
from utils.supabase_integration import SupabaseClient

def test_st_secrets():
    secrets = st.secrets
    with st.expander("Secrets"):
        st.json(secrets)    

def test_supabase_integration():
    supabase = SupabaseClient(url=os.environ["SUPABASE_URL"], key=os.environ['SUPABASE_KEY'])
    if supabase:
        user_records = supabase.get_students_from_db()
        with st.expander("Students"):
            st.dataframe(user_records)  
    
def test_calendar_integration():
    calendar = CalendarClient(st.secrets.get('calendar'))
    events = calendar.get_calendar_events(True, 3)
    with st.expander("Events"):
        st.dataframe(events)

if __name__ == "__main__":
    env_secrets=st.secrets.get("env")  
    if env_secrets:
        setup_env_from_dict(env_secrets)
    test_st_secrets()
    test_supabase_integration()
    test_calendar_integration()
