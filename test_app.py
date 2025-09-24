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
        
from pathlib import Path
from utils.gmail_creds import GmailOAuthManager, TokenStore, OAuthSettings, SupabaseTokenStore
TOKEN_FILE = (Path(__file__).parent / ".tokens" / "gmail.json")



def test_gmail_credentials() -> None:
    st.set_page_config(page_title="Gmail Search", layout="wide")
    supabase = SupabaseClient(url=os.environ.get("SUPABASE_URL", ""), key=os.environ.get('SUPABASE_KEY', ""))
    store = SupabaseTokenStore(supabase) if supabase else TokenStore(TOKEN_FILE)
    manager = GmailOAuthManager(OAuthSettings.from_secrets(), store)

    # Read query parameters in a way that works across Streamlit versions
    if hasattr(st, "query_params"):
        raw_params = dict(st.query_params)
    else:
        raw_params = st.experimental_get_query_params()

    # Normalize: convert list values (from experimental API) to single strings
    params = {k: (v if isinstance(v, str) else (v[0] if v else "")) for k, v in raw_params.items()}
    print(f"DEBUG: {params=}")
    print(f"DEBUG: token_path={TOKEN_FILE.resolve()}")

    if "code" in params and "state" in params:
        manager.exchange_code(params)
        try:
            if hasattr(st, "query_params"):
                st.query_params.clear()
            else:
                st.experimental_set_query_params()
        except Exception:
            pass
        st.rerun()
    creds = manager.credentials()
    if not creds:
        st.header("Authorize Gmail Read-Only Access")
        try:
            url = manager.authorization_url()
        except RuntimeError as exc:
            st.error(str(exc))
            return
        st.link_button("Authorize with Google", url=url)
        return
    with st.sidebar.expander("Reset authorization", expanded=False):
        if st.button("Reset now"):
            manager.reset()
            st.success("Authorization removed.")
            st.rerun()
    st.success("Authorization active. Refresh tokens will be managed automatically.")
    if isinstance(store, TokenStore):
        st.caption(f"Token file path: {TOKEN_FILE.resolve()}")
        st.caption(f"Token file exists: {TOKEN_FILE.exists()}")
    else:
        st.caption("Tokens stored in Supabase.")
        
def test_confluence_links():
    full_name=st.text_input("Student name")
    supabase = SupabaseClient(url=os.environ["SUPABASE_URL"], key=os.environ['SUPABASE_KEY'])
    responses = supabase.get_confluence_pages(full_name)
    for resp in responses:
        title=resp.get('title', 'No title')
        page_url=resp.get('page_url', 'https://aiclub.world')
        st.write(f"{resp=}")
        st.link_button(title,page_url)
    

if __name__ == "__main__":
    env_secrets=st.secrets.get("env")  
    if env_secrets:
        setup_env_from_dict(env_secrets)
    #test_st_secrets()
    #test_supabase_integration()
    #test_calendar_integration()
    #test_gmail_credentials()
    test_confluence_links()
