import streamlit as st
import pandas as pd

import math
import os
from datetime import datetime, timezone

#import io
#from google.oauth2 import service_account
#from googleapiclient.discovery import build
#from googleapiclient.http import MediaIoBaseDownload

from utils.supabase_integration import SupabaseClient
from utils.calendar_integration import CalendarClient
from src.show_search_page import show_search_page

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
    if df is None or df.empty:
        st.info("No students are currently linked to your account.")
        return
    if "Name" not in df.columns:
        st.warning("Student roster is missing the Name column.")
        return
    df = df.copy()
    df.drop(columns=["Status"], inplace=True, errors="ignore")
    df["URL"]="/show_users_student_details?q="+df['Name']
    st.dataframe(df, column_config={"URL": st.column_config.LinkColumn("URL", display_text="Student details")}, hide_index=True)

    #st.dataframe(df)
    
def events_to_df(events):
    rows = []
    for event in events:          # events = list of event dicts from the API
        start_str = (
            event.get("start", {}).get("dateTime")
            or event.get("start", {}).get("date")
        )
        start_dt = pd.to_datetime(start_str)
        rows.append(
            {
                "Topic": event.get("summary", ""),
                "Meeting Date": start_dt.date(),
                "Start Time": start_dt.time(),
            }
        )

    df = pd.DataFrame(rows)

    if df.empty:
        st.info("No meetings found.")
        return df, None, None
    else:
        combined = pd.to_datetime(df["Meeting Date"].astype(str) + " " + df["Start Time"].astype(str))
        first_idx = combined.idxmin()
        first_topic = df.loc[first_idx, "Topic"]
        first_dt = combined.loc[first_idx].replace(tzinfo=timezone.utc)  # adjust tz if needed
        days_until = (first_dt - datetime.now(timezone.utc)).days
        return df,first_topic,days_until
    
def show_calendar_info(topics):
    calendar = CalendarClient(st.secrets.get('calendar'))
    events,all_events=calendar.get_events_for_topics(topics)
    #st.json(events)
    df,topic,days_until=events_to_df(events)
    if days_until:
        st.divider()
        st.title(f"In {days_until} days, meeting: {topic}")
        st.dataframe(df.head(10), hide_index=True)
    #with st.expander("All events"):
    #    st.dataframe(all_events)
    
def show_email_info(student_name,days):
    st.divider()
    #st.write("TO-DO Email information")
    # 1. Get student email address
    df1=st.session_state.get('student_list')
    df2=st.session_state.get('relation_list')
    df3=st.session_state.get('person_list')
    #st.dataframe(df1)
    #st.dataframe(df2)
    #st.dataframe(df3)
    df1 = df1[df1['Name'] == student_name]
    student_emails=df1['Email'].tolist()
    parent_rows = df2[(df2['Student'] == student_name) & (df2['Relationship'] == 'parent')]
    parent_names=parent_rows['Person'].tolist()
    #st.write(f"{student_emails=}, {parent_names=}")
    parent_email_rows=df3[df3['Name'].isin(parent_names)]
    parent_emails=parent_email_rows['Email'].tolist()
    #st.write(f"{parent_emails=}")
    combined_emails=student_emails+parent_emails
    query_str=" OR ".join(combined_emails)
    #st.write(f"{combined_emails=}, {query_str=}")
    show_search_page(combined_emails,days)
    
    # 2. Get email of their parents
    # Search by df_n["URL"]="/show_search_page?q="+df_n['student']+' OR '+df_n['all_emails']
    
    
    
def show_past_session_details(topics):
    supabase_client=SupabaseClient(os.getenv('SUPABASE_URL'),os.getenv('SUPABASE_KEY'))
    session_table=create_topic_zoom_session_table(supabase_client,topics)
    df = pd.DataFrame(session_table)
    if df.empty:
        st.warning("No past sessions seem")
    else:
        df["URL"]="/show_zoom_detail_page?q="+df['session_id']
        st.dataframe(df, column_config={"URL": st.column_config.LinkColumn("URL", display_text="Session details")}, hide_index=True)
        return df
        
def days_since_last_session(past_sessions):
    if past_sessions is None:
        return 90
    #st.write(f"Past sessions: {past_sessions.info()}")
    df=past_sessions
    df['date'] = pd.to_datetime(df['date'])

    #max_date = df['date'].max().normalize() 
    #today = pd.Timestamp.now().normalize()
    max_date = df['date'].max()
    today = pd.Timestamp.now()
    days_inclusive = math.ceil((today - max_date) / pd.Timedelta(days=1))
    return days_inclusive

def show_users_student_details():
    student_name = st.query_params.get("q")
    st.title(f"Person: {student_name}")
    df=st.session_state.get('topic_list')
    if df is None or df.empty:
        st.info("No session topics are currently linked to this student.")
        return
    if "Person" not in df.columns or "Topic" not in df.columns:
        st.warning("Session topic data is missing required columns.")
        return
    df = df[df['Person'] == student_name]
    topics = df['Topic'].dropna().str.strip().tolist()
    with st.expander("Recent sessions"):
        past_sessions=show_past_session_details(topics)
    with st.expander("Upcoming Zoom sessions"):
        show_calendar_info(topics)
    with st.expander("Recent emails"):
        days=days_since_last_session(past_sessions)
        show_email_info(student_name,days)
    with st.expander("All emails"):
        show_email_info(student_name,90)
