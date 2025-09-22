import os
import streamlit as st

from utils.supabase_integration import SupabaseClient

def show_instructors_page():
    tab1, tab2, tab3 = st.tabs(["Instructors", "Student-Instructors", "Future"])

    with tab1:
        st.title("Instructors")
        client = SupabaseClient(os.getenv("SUPABASE_URL"),os.getenv("SUPABASE_KEY"))
        rows = client.get_instructors()
        st.data_editor(rows,hide_index=True,width='stretch',num_rows="dynamic")

    with tab2:
        st.title("Student-Instructors")
        st.info("Student-Instructors content coming soon.")

    with tab3:
        st.title("Future")
        st.info("Future content coming soon.")
