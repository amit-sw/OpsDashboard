import streamlit as st
import os
import csv
import json


from supabase import create_client, Client

def setup_env_from_dict(dict_env):
    for k in dict_env.keys():
        v=dict_env.get(k)
        print(f"DEBUG: setup-env-from-dict: {k=},{v=}")
        os.environ[k]=v
        
        
def find_student_in_db(supabase,student):
    try:
        response = supabase.table('research_program_students').select('*').eq("full_name",student).execute()
        return response
    except Exception as e:
        print(f"Error fetching students from database: {e}")
        return []

def update_student_in_db(supabase,student,instructor,mentor,ops):
    try:
        updates = {
            "p_full_name": student,
            "p_instructor": instructor,
            "p_mentor": mentor,
            "p_ops": ops
        }
        response = supabase.rpc( "update_contact_by_full_name",updates).execute()
        return response
    except Exception as e:
        print(f"Error fetching students from database: {e}")
        return []
    
def one_run(filepath):
    url=os.getenv('SUPABASE_URL')
    key=os.getenv('SUPABASE_KEY')
    supabase = create_client(url, key)

    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise RuntimeError("CSV has no header row; please add a header or provide a valid CSV.")
        for idx,row in enumerate(reader):
            if True:
                student=row["Student Name"]
                instructor=row["Instructor"]
                mentor=row["Mentor"]
                ops=row["Operations"]
                r1=find_student_in_db(supabase,student)
                st.write(f"For {student}, found {r1}")
                records=update_student_in_db(supabase,student,instructor,mentor,ops)
                st.write(f"Updated {records} records for {student}")


env_secrets=st.secrets.get("env")  
print(f"DEBUG: ENV Secrets: {env_secrets=}")  
if env_secrets:
    setup_env_from_dict(env_secrets)
if st.button("Run"):
    one_run('/Users/amitamit/Documents/GitHub/OpsDashboard/helpers/list_students_instructors_mentors.csv')

