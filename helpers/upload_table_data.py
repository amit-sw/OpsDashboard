import os
import streamlit as st
import csv
import json
import sys

from supabase import create_client, Client


def setup_env_from_dict(dict_env):
    for k in dict_env.keys():
        v=dict_env.get(k)
        print(f"DEBUG: setup-env-from-dict: {k=},{v=}")
        os.environ[k]=v

def add_student_to_db(supabase,record):
    try:
        response = supabase.table('research_program_students').insert(record).execute()
        return response
    except Exception as e:
        print(f"Error fetching students from database: {e}")
        return []


def process_record(supabase,row):
    print(f"About to process {row}")
    record=row
    se=row['student_emails']
    pe=row['parent_emails']
    print(f"DEBUG:{se=},{pe=}")
    record["student_emails"] = json.loads(se.replace("'", '"')) if se else []
    record["parent_emails"]  = json.loads(pe.replace("'", '"')) if pe else []
    add_student_to_db(supabase,record)


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
                process_record(supabase,row)


env_secrets=st.secrets.get("env")  
print(f"DEBUG: ENV Secrets: {env_secrets=}")  
if env_secrets:
    setup_env_from_dict(env_secrets)
one_run('helpers/research_program_students_rows.csv')
    