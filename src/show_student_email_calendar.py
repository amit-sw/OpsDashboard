import streamlit as st
import pandas as pd
import time
import os

from utils.supabase_integration import SupabaseClient
from utils.calendar_integration import CalendarClient

def create_information_table(supabase,calendar):
    student_emails=supabase.get_student_emails_from_db()
    events = calendar.get_calendar_events()
    return student_emails, events

def process_time_record(event_record):
    if event_record.get("date"):
        return event_record.get("date"),"Unknown timezone"
    if event_record.get("dateTime"):
        return event_record.get("dateTime"),event_record.get("timeZone")
    
def process_attendee_record(attendee_record):
    email_list = [r.get('email') for r in attendee_record]
    return email_list
        
def match_attendee(name,event_title):
    name_parts=[w.lower() for w in name.split()]
    all_present = all(w in event_title.lower() for w in name_parts)
    return all_present

def match_email_list(list1,list2):
    matched=any(elem in list2 for elem in list1)
    return matched

def extracted_record(student_email_record):
    extracted_value={}
    student_full_name=student_email_record.get("full_name","")
    student_main_email=student_email_record.get("primary_sudent_email","")
    student_all_emails=student_email_record.get("student_emails",[])+student_email_record.get("parent_emails",[])
    extracted_value["student"]=student_full_name
    extracted_value['all_emails']=' OR '.join(student_all_emails)
    #st.write(f"Extracted: {extracted_value=} for {student_email_record=}")
    return extracted_value
    
def match_one_student_to_one_event(student_email_record,event):
    student_full_name=student_email_record.get("full_name","")
    student_main_email=student_email_record.get("primary_sudent_email","")
    student_all_emails=student_email_record.get("student_emails",[])+student_email_record.get("parent_emails",[])
    #st.write(f"DEBUG: {student_email_record=}")
    event_start_record=event.get("start",{})
    event_title=event.get("summary","")
    event_attendees_record=event.get("attendees",[])
    event_start_date, event_start_tz=process_time_record(event_start_record)
    event_attendees=process_attendee_record(event_attendees_record)
    match_name=match_attendee(student_full_name,event_title)
    match_student_email=match_email_list([student_main_email],event_attendees)
    match_parent_email=match_email_list(student_all_emails,event_attendees)
    
    return match_name, match_student_email, match_parent_email, event_start_date, event_start_tz, student_full_name,event_title, student_all_emails

def match_one_student_to_events(student_email,events,parent_match):
    #st.write(f"Matching event for student {student_email}")
    for event in events:
        mn,mse,mpe,esd,est,sfn,et,sae=match_one_student_to_one_event(student_email,event)
        one_match=mn or mse
        if parent_match:
            one_match = one_match or mpe
            
        if one_match:
            match_value={}
            match_value["student"]=sfn
            match_value["event"]=et
            match_value["start_time"]=esd
            match_value["start_tz"]=est
            match_value['all_emails']=' OR '.join(sae)
            return match_value

def match_students_events(student_emails,events,parent_match=False):
    #st.write("Matching in progress...")  
    matched_students=[]
    unmatched_students=[]
    for student_email in student_emails:
        one_match=match_one_student_to_events(student_email,events,parent_match)
        if one_match:
            matched_students.append(one_match)
        else:
            unmatched_students.append(extracted_record(student_email))
    return matched_students, unmatched_students

def show_student_email_calendar():
    supabase=SupabaseClient(os.getenv('SUPABASE_URL'),os.getenv('SUPABASE_KEY'))
    calendar = CalendarClient(st.secrets.get('calendar'))
    
    start = time.perf_counter()
    with st.spinner("Fetching results from Calendar API…", show_time=True):
        student_emails,events=create_information_table(supabase,calendar)
    elapsed = time.perf_counter() - start
    duration = f"{elapsed*1000:.0f} ms" if elapsed < 1 else f"{elapsed:.2f} s"
    st.sidebar.write(f"Data fetch took {duration}")
    start = time.perf_counter()
    with st.spinner("Fetching results from Calendar API…", show_time=True):
        matches,nonmatches=match_students_events(student_emails,events)
    elapsed = time.perf_counter() - start
    duration = f"{elapsed*1000:.0f} ms" if elapsed < 1 else f"{elapsed:.2f} s"
    st.sidebar.write(f"Match took {duration}")
    df_m=pd.DataFrame(matches)
    df_n=pd.DataFrame(nonmatches)
    df_m["URL"]="/show_search_page?q="+df_m['student']+' OR '+df_m['all_emails']
    df_n["URL"]="/show_search_page?q="+df_n['student']+' OR '+df_n['all_emails']
    df_m=df_m.drop(["all_emails"], axis=1)
    df_n=df_n.drop(["all_emails"], axis=1)
    tab1, tab2 = st.tabs(["Matches", "Non-matches"])
    with tab1:
        st.dataframe(df_m, column_config={"URL": st.column_config.LinkColumn("Email link", display_text="Go to Emails")}, hide_index=True)
    with tab2:
        st.dataframe(df_n, column_config={"URL": st.column_config.LinkColumn("Email link", display_text="Go to Emails")}, hide_index=True)

    
    
if __name__ == "__main__":
    show_student_email_calendar()