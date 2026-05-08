import streamlit as st
import os
from streamlit.runtime.scriptrunner_utils.exceptions import StopException

from langsmith import traceable

st.set_page_config(layout="wide")

from utils import configs
from utils.supabase_integration import SupabaseClient
import pandas as pd

from src.show_students_page import show_students_page
from src.show_student_email_calendar import show_student_email_calendar
from src.show_gmail_creds_page import show_gmail_creds_page
from src.show_search_page import show_search_page
from src.show_zoom_session_page import show_zoom_session_page, show_zoom_detail_page
from src.show_instructors_page import show_instructors_page
from src.show_gmail_fetch_control import show_gmail_fetch_control
from src.show_fetch_zoom_aws import show_fetch_zoom_aws
from src.show_users_students import show_users_students, show_users_student_details
from src.show_finance_info import show_braintree, show_finance_agent
from src.show_table_explorer import show_table_explorer
from src.show_sheet_explorer import show_sheet_explorer
from src.show_question_prompts import show_question_prompts_page
from src.show_qna_emails import show_qna_emails_page
from src.show_recent_sessions_page import show_recent_sessions_page

from utils.process_gsheets import get_users_students

    
def show_events_all():
    st.title("Events all page")
    
def set_student_list(user):
    #st.title("User's students")
    email = user.get('email')
    service_account_info = st.secrets.get("gdrive_secrets", {})
    sheets_list = service_account_info.get("sheets", [])
    try:
        df_students, df_topic_list, df_persons, df_relations, df_sessions = get_users_students(
            email,
            service_account_info,
            sheets_list,
        )
    except Exception as exc:
        st.warning(f"Student roster could not be loaded: {exc}")
        df_students = pd.DataFrame()
        df_topic_list = pd.DataFrame()
        df_persons = pd.DataFrame()
        df_relations = pd.DataFrame()
        df_sessions = pd.DataFrame()
    #with st.sidebar.expander("Persons"):
    #    st.dataframe(df_persons)
    #with st.sidebar.expander("Relationships"):
    #    st.dataframe(df_relations)
    st.session_state['student_list']=df_students
    st.session_state['topic_list']=df_topic_list
    st.session_state['person_list']=df_persons
    st.session_state['relation_list']=df_relations
    return df_students

def show_sidebar_ui(user):
    name = user.get("name", "Unknown User")
    email = user.get("email", "Unknown Email")
    picture = user.get("picture", "")
    email_verified = user.get("email_verified", False)
    with st.sidebar:
        st.text(f"Welcome {name}\n {email}")
        if email_verified:
            st.success("Email is verified.")
        else:
            st.warning("Email is not verified.")
        if picture:
            st.image(picture, width=100)
        
        if st.button("Log out"):
            try:
                st.logout()
            except StopException:
                return

    
        

def show_ui_core(user):
    show_sidebar_ui(user)
    set_student_list(user)
    
    pages = {
        "User": [
            st.Page(show_users_students,title="User's students"),
            st.Page(show_users_student_details,title="User's student details"),
        ],
        "Students": [
            st.Page(show_students_page, title="Students"),
        ],
        "Calendar": [
            st.Page(show_student_email_calendar, title="Calendar"),
        ],
        "Search": [
            st.Page(show_search_page, title="Email search"),
        ],
        "Past Sessions": [
            st.Page(show_zoom_session_page, title="Sessions"),
            st.Page(show_zoom_detail_page, title="Session Details"),
        ],
        "Data": [
            st.Page(show_table_explorer, title="Table Explorer"),
            st.Page(show_sheet_explorer, title="Sheet Explorer"),
            st.Page(show_question_prompts_page, title="Question Prompts"),
        ],

    }

    pg = st.navigation(pages, position="top")
    try:
        pg.run()
    except StopException:
        # Streamlit uses StopException internally to control reruns/navigation
        # Swallow it so it doesn't get surfaced to external tracers/loggers
        return
   
def show_ui_superadmin(user):
    show_sidebar_ui(user)
    set_student_list(user)
    #st.title("Admin Panel")
    #st.write("This is the admin panel. More features coming soon!")
    pages = {
        "SuperAdmin": [
            st.Page(show_gmail_creds_page, title="Gmail Creds"),
            st.Page(show_gmail_fetch_control, title="Gmail Fetch"),
        ],
        "Super-Calendar": [
            st.Page(show_student_email_calendar, title="Calendar"),
        ],
        "Super-Search": [
            st.Page(show_search_page, title="Email search"),
        ],
        "Super - Past Sessions": [
            st.Page(show_zoom_session_page, title="Sessions"),
            st.Page(show_zoom_detail_page, title="Session Details"),
        ],
        "Super-Recent Sessions": [
            st.Page(show_recent_sessions_page, title="New Sessions (24h)"),
        ],
        "Data": [
            st.Page(show_table_explorer, title="Table Explorer"),
            st.Page(show_sheet_explorer, title="Sheet Explorer"),
            st.Page(show_question_prompts_page, title="Question Prompts"),
            st.Page(show_qna_emails_page, title="QnA Emails"),
        ],
    }
    pg = st.navigation(pages, position="top")
    try:
        pg.run()
    except StopException:
        return
    
def show_ui_financeadmin(user):
    show_sidebar_ui(user)
    set_student_list(user)
    
    pages = {
        "Finance": [
            st.Page(show_finance_agent,title="Finance Agent"),
            st.Page(show_braintree,title="Briantree"),
        ],
        "Finance-User": [
            st.Page(show_users_students,title="User's students"),
            st.Page(show_users_student_details,title="User's student details"),
        ],
        "Finance-Second": [
            st.Page(show_search_page, title="Email Search"),
            st.Page(show_zoom_session_page, title="Sessions"),
            st.Page(show_zoom_detail_page, title="Session Details"),
        ],
        "Finance-Archive": [
            st.Page(show_students_page, title="Students"),
            st.Page(show_student_email_calendar, title="Calendar"),
            #st.Page(show_instructors_page, title="Instructors"),
            st.Page(show_gmail_fetch_control, title="Gmail Fetch"),
            
        ],
        "Finance-Data": [
            st.Page(show_table_explorer, title="Table Explorer"),
            st.Page(show_sheet_explorer, title="Sheet Explorer"),
            st.Page(show_fetch_zoom_aws, title="CRON explorer"),
            st.Page(show_question_prompts_page, title="Question Prompts"),
            st.Page(show_qna_emails_page, title="QnA Emails"),
        ],

    }

    pg = st.navigation(pages, position="top")
    try:
        pg.run()
    except StopException:
        return
   
def show_ui_admin(user):
    show_sidebar_ui(user)
    set_student_list(user)
    
    pages = {
        "Admin-User": [
            st.Page(show_users_students,title="User's students"),
            st.Page(show_users_student_details,title="User's student details"),
        ],
        "Admin-Students": [
            st.Page(show_students_page, title="Students"),
        ],
        "Admin-Calendar": [
            st.Page(show_student_email_calendar, title="Calendar"),
        ],
        "Admin-Search": [
            st.Page(show_search_page, title="Email search"),
            #st.Page(show_instructors_page, title="Instructors"),
            st.Page(show_gmail_fetch_control, title="Gmail Fetch"),
        ],
        "Past Sessions": [
            st.Page(show_zoom_session_page, title="Sessions"),
            st.Page(show_zoom_detail_page, title="Session Details"),
            
        ],
        "Data": [
            st.Page(show_table_explorer, title="Table Explorer"),
            st.Page(show_sheet_explorer, title="Sheet Explorer"),
            st.Page(show_fetch_zoom_aws, title="CRON explorer"),
            st.Page(show_question_prompts_page, title="Question Prompts"),
        ],

    }

    pg = st.navigation(pages, position="top")
    try:
        pg.run()
    except StopException:
        return

def show_ui_guest(user):
    st.title("Guest Access")
    st.write(
        "You do not have access. Please reach out to the System Administrator "
        f"with your information\n Email: {user.get('email', 'Unknown Email')}."
    )
    if st.button("Log out"):
        try:
            st.logout()
        except StopException:
            return
    #show_ui_core(user)

def show_ui_user(user):
    #st.title("User Access")
    #st.write("Welcome to the user panel. More features coming soon!")
    show_ui_core(user)

def show_ui(user):
    st.session_state["current_user_role"] = "guest"
    if user and user.get("email_verified", False):
        supabase = SupabaseClient(url=os.environ["SUPABASE_URL"], key=os.environ['SUPABASE_KEY'])
        if supabase:
            user_record = supabase.get_user_from_db(user['email'])
            if not user_record:
                role = "guest"
                st.session_state["current_user_role"] = role
                show_ui_guest(user)
                return
            role= user_record.get("role", "guest")
            st.session_state["current_user_role"] = role
            if role == "superadmin":
                show_ui_superadmin(user)
            elif role == "financeadmin":
                show_ui_financeadmin(user)
            elif role == "admin":
                show_ui_admin(user)
            elif role == "user":
                show_ui_user(user)
            elif role == "guest":
                show_ui_guest(user)
            else:
                st.error(f"Unknown role: {role}. Please contact the administrator.")
        else:
            st.error("Could not connect to Supabase.")
    else:
        st.warning("Please log in with a verified email to access the app.")
