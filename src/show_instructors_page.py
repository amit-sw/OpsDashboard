import os
import streamlit as st
import pandas as pd

from utils.supabase_integration import SupabaseClient

def add_instructor(name,email_address):

def show_update_instructors():
    st.title("Instructors")
    client = SupabaseClient(os.getenv("SUPABASE_URL"),os.getenv("SUPABASE_KEY"))
    ins_list = client.get_instructors()
    df = pd.DataFrame(ins_list)
    df = df.drop(columns=["id", "created_at", "updated_at"])
    edited_df=st.data_editor(df, hide_index=True, width='stretch', key="data_editor_key")
    if edited_df is not None:
        if changes := st.session_state["data_editor_key"]["edited_rows"]:
            for row_index, updated_columns in changes.items():
                for column_name, new_value in updated_columns.items():
                    ins_record=ins_list[row_index]
                    row_id = ins_record['id'] 
                    client.update_instructors(row_id, column_name, new_value)
            st.session_state["data_editor_key"]["edited_rows"] = None
            
def show_add_instructors():
    name=st.text_input("Name")
    email_address=st.text_input("Email Address")
    if name and email_address and st.button("Add"):
        add_instructor(name,email_address)

def show_instructors_page():
    tab1, tab2, tab3 = st.tabs(["Instructors", "Student-Instructors", "Future"])

    with tab1:
        show_update_instructors()
        st.divider()
        show_add_instructors()

    with tab2:
        st.title("Student-Instructors")
        st.info("Student-Instructors content coming soon.")

    with tab3:
        st.title("Future")
        st.info("Future content coming soon.")
