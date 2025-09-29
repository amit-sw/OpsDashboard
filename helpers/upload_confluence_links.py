import os
import streamlit as st
import csv
import json
import sys

from atlassian import Confluence

from supabase import create_client, Client

URL_BASE='https://aiclub.atlassian.net/wiki'


def setup_env_from_dict(dict_env):
    for k in dict_env.keys():
        v=dict_env.get(k)
        #print(f"DEBUG: setup-env-from-dict: {k=},{v=}")
        os.environ[k]=v
        
        
def get_student_list():
    try:
        supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))
        response = supabase.table('research_program_students').select('full_name').execute()
        return response.data
    except Exception as e:
        print(f"Error fetching students from database: {e}")
        return [] 
    
def get_student_confluence_links():
    try:
        supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))
        response = supabase.table('confluence_pages').select('*').execute()
        return response.data
    except Exception as e:
        print(f"Error fetching students from database: {e}")
        return []      
    
def add_student_confluence_link(params):
    # {'title':title,'url':url,'full_name':full_name})
    try:
        supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))
        response=supabase.table('confluence_pages').insert(params).execute()
        return response.data
    except Exception as e:
        print(f"Error fetching students from database: {e}")
        return []       
    
def main_run():
    setup_env_from_dict(st.secrets.get('env'))
    current_confluence_list=get_student_confluence_links()
    with st.sidebar.expander("Conf list"):
        st.write(f"{current_confluence_list}")
    confluence = Confluence(
        url="https://aiclub.atlassian.net",
        username="amit.gupta@pyxeda.ai",
        password=os.getenv('CONFLUENCE_TOKEN'),
        cloud=True
    )
    student_list = get_student_list()
    full_list={}
    if st.button("Run"):
        for student in student_list:
            li=[]
            full_name=student.get("full_name")
            if full_name:
                s_string= f"text ~ '{full_name}' and type=page"
                st.write(f"Querying {s_string} for {full_name}")
                results = confluence.cql(cql=s_string,limit=25)
                for result in results.get("results",[]):
                    try:
                        title=result['content'].get('title')
                        if title=='Students' or title == 'How did they find us?' or title == 'Potential Projects':
                            continue
                        webui_link=result["content"]["_links"].get('webui')
                        url=URL_BASE+webui_link
                        st.write(f"Title: {title} with URL: {url} for {full_name}")
                        add_student_confluence_link({'title':title,'page_url':url,'full_name':full_name})
                    except Exception as e:
                        print(f"Got exception {e} when processing student {full_name}")
                if len(li)>0:
                    full_list[full_name]=li
                    
        st.json(full_list)
            
            
if __name__ == '__main__':
    main_run()