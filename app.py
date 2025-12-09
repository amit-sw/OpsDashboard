import streamlit as st

from utils import configs

from src.verified_ui import show_ui
from utils.utils_credentials import setup_env_from_dict

from src.show_cron_processing import show_cron_processing

configs.load(st.secrets)
env_secrets=st.secrets.get("env")  
#print(f"DEBUG: ENV Secrets: {env_secrets=}")  
#print(f"DEBUG CONFIGS: {configs.braintree=}")
if env_secrets:
    setup_env_from_dict(env_secrets)

def login_screen():
    st.button("Log in with Google", on_click=st.login)
    
if st.query_params.get("cronId"):
    st.error("Not supported here.")
    show_cron_processing()
elif st.user and st.user.is_logged_in:
    show_ui(st.user)
else:
    login_screen()
    
    