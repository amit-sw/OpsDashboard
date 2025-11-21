import streamlit as st
import pandas as pd

import os

#import io
#from google.oauth2 import service_account
#from googleapiclient.discovery import build
#from googleapiclient.http import MediaIoBaseDownload

from utils.supabase_integration import SupabaseClient

def create_topic_zoom_session_table(supabase_client: SupabaseClient, topic_list: [str]):
    try:
        response = supabase_client.supabase.table("zoom_sessions").select("topic,date,session_id").in_("topic", topic_list).order("date", desc=True).execute()
        return response.data or []
    except Exception as e:
        st.error(f"An error occurred while fetching zoom sessions: {e}")
        return None

def show_users_students():
    st.title("User's Students - Initial")
    df = st.session_state.get('student_list')
    df.drop(columns=["Status"], inplace=True)
    df["URL"]="/show_users_student_details?q="+df['Name']
    st.dataframe(df, column_config={"URL": st.column_config.LinkColumn("URL", display_text="Student details")}, hide_index=True)

    #st.dataframe(df)
    
def show_users_student_details():
    student_name = st.query_params.get("q")
    st.title(f"Student: {student_name}")
    supabase_client=SupabaseClient(os.getenv('SUPABASE_URL'),os.getenv('SUPABASE_KEY'))
    #st.divider()
    df2=st.session_state.get('topic_list')
    #st.dataframe(df2)
    topics = df2['Topic'].dropna().str.strip().tolist()
    session_table=create_topic_zoom_session_table(supabase_client,topics)
    df3 = pd.DataFrame(session_table)
    df3["URL"]="/show_zoom_detail_page?q="+df3['session_id']
    st.dataframe(df3, column_config={"URL": st.column_config.LinkColumn("URL", display_text="Session details")}, hide_index=True)
    
    
