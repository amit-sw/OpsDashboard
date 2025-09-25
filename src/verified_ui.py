import streamlit as st
import os

st.set_page_config(layout="wide")

from utils.supabase_integration import SupabaseClient
import pandas as pd

from src.show_students_page import show_students_page
from src.show_student_email_calendar import show_student_email_calendar
from src.show_gmail_creds_page import show_gmail_creds_page
from src.show_search_page import show_search_page
from src.show_instructors_page import show_instructors_page
from src.show_gmail_fetch_control import show_gmail_fetch_control
    
def show_events_all():
    st.title("Events all page")

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
            st.logout() 

def show_ui_core(user):
    show_sidebar_ui(user)
    
    pages = {
        "Students": [
            st.Page(show_students_page, title="Students"),
        ],
        "Calendar": [
            st.Page(show_student_email_calendar, title="Calendar"),
        ],
        "Search": [
            st.Page(show_search_page, title="Email search"),
        ],

    }

    pg = st.navigation(pages, position="top")
    pg.run()
    
def show_ui_superadmin(user):
    show_sidebar_ui(user)
    #st.title("Admin Panel")
    #st.write("This is the admin panel. More features coming soon!")
    pages = {
        "SuperAdmin": [
            st.Page(show_gmail_creds_page, title="GMail Creds"),
        ],
        "Super-Calendar": [
            st.Page(show_student_email_calendar, title="Calendar"),
        ],
        "Super-Search": [
            st.Page(show_search_page, title="Email search"),
        ],
    }
    pg = st.navigation(pages, position="top")
    pg.run()
    
def show_ui_admin(user):
    show_sidebar_ui(user)
    
    pages = {
        "Admin-Students": [
            st.Page(show_students_page, title="Students"),
        ],
        "Admin-Calendar": [
            st.Page(show_student_email_calendar, title="Calendar"),
        ],
        "Admin-Search": [
            st.Page(show_search_page, title="Email search"),
            #st.Page(show_instructors_page, title="Instructors"),
            st.Page(show_gmail_fetch_control, title="GMail Fetch"),
        ],

    }

    pg = st.navigation(pages, position="top")
    pg.run()

def show_ui_guest(user):
    st.title("Guest Access")
    st.write(f"You do not have access. Please reach out to System Administrator with your information\n Email: {user.get("email", "Unknown Email")}.")
    if st.button("Log out"):
        st.logout()
    #show_ui_core(user)

def show_ui_user(user):
    #st.title("User Access")
    #st.write("Welcome to the user panel. More features coming soon!")
    show_ui_core(user)

def show_ui(user):
    if user and user.get("email_verified", False):
        supabase = SupabaseClient(url=os.environ["SUPABASE_URL"], key=os.environ['SUPABASE_KEY'])
        if supabase:
            user_record = supabase.get_user_from_db(user['email'])
            if not user_record:
                role = "guest"
                show_ui_guest(user)
                return
            role= user_record.get("role", "guest")
            if role == "superadmin":
                show_ui_superadmin(user)
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
