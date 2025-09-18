import streamlit as st
import os

st.set_page_config(layout="wide")

from utils.supabase_integration import SupabaseClient
import pandas as pd

def show_students_page():
    st.title("Students page")
    
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
            st.Page(show_events_all, title="Calendar"),
        ],
    }

    pg = st.navigation(pages, position="top")
    pg.run()
    
def show_ui_admin(user):
    #st.title("Admin Panel")
    #st.write("This is the admin panel. More features coming soon!")
    show_ui_core(user)

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
            if role == "admin":
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