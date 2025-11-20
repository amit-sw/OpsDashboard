import streamlit as st
import pandas as pd

import io
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from utils.process_gsheets import get_users_students

def show_users_students():
    st.title("User's Students - Initial")
    df = st.session_state.get('student_list')
    st.dataframe(df)
    
def show_users_students_old():
    st.title("User's students")
    email = st.user.get('email')
    service_account_info = st.secrets["gdrive_secrets"]
    sheets_list=service_account_info.get("sheets")
    df_students, df_persons, df_relations=get_users_students(email, service_account_info, sheets_list)
    with st.sidebar.expander("Persons"):
        st.dataframe(df_persons)
    with st.sidebar.expander("Relationships"):
        st.dataframe(df_relations)
    st.dataframe(df_students)
