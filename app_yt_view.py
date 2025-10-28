import streamlit as st
from utils.utils_credentials import setup_env_from_dict
import math

from src.show_yt_video_discuss import show_yt_ui, show_discuss_ui
from src.show_pdf_upload import show_upload_pdf_ui



env_secrets=st.secrets.get("env")  
#print(f"DEBUG: ENV Secrets: {env_secrets=}")  
if env_secrets:
    setup_env_from_dict(env_secrets)

def login_screen():
    st.button("Log in with Google", on_click=st.login)

if st.user and st.user.is_logged_in:
    tab1, tab2, tab3 = st.tabs(["Video", "Discuss","Upload PDF"])
    with tab1:
        show_yt_ui(st.user)
    with tab2:
        show_discuss_ui(st.user)
    with tab3:
        show_upload_pdf_ui(st.user)
else:
    login_screen()