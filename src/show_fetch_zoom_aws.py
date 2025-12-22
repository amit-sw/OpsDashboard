import streamlit as st
import os

import base64
import datetime

from concurrent.futures import ThreadPoolExecutor, as_completed

import boto3
import pandas as pd

from utils.utils_aws import setup_env_from_dict, save_to_supabase, fetch_s3_object, extract_field_value
from utils.utils_aws import derive_column_names, decode_json_value, get_sql_query_aws_date 

from utils.supabase_integration import SupabaseClient

from utils.utils_transcript_chat import llm_request_response
from utils.prompts import question_prompts
    

def get_sql_query_aws_session_id():
    return """
    SELECT session_id,project_id,instructor_names,youtube_link,session_summary,timestamp,date,time_zone,zoom_link,topic,transcript
    FROM navigator_PRODUCTION.project_sessions
    WHERE session_id = :session_id
    LIMIT 1;
    """

def get_bucket_contents(bucket, key, region):
    content = ""
    if bucket and key:
        s3_content = fetch_s3_object(bucket, key, region)
        try:
            content = s3_content.decode("utf-8")
        except UnicodeDecodeError:
            content = base64.b64encode(s3_content).decode("ascii")
    return content

def process_one_record(rec, column_names, region):
    values = [extract_field_value(field) for field in rec]
    new_row = dict(zip(column_names, values))

    transcript_obj = decode_json_value(new_row.get("transcript"))
    #print(f"DEBUG: {transcript_obj=} with type {type(transcript_obj)}")

    if isinstance(transcript_obj, list) and transcript_obj:
        parts = []
        for entry in transcript_obj:
            if isinstance(entry, dict):
                bucket = entry.get("bucket")
                key = entry.get("key")
                transcript = get_bucket_contents(bucket, key, region)
                if transcript:
                    parts.append(transcript)
        if parts:
            new_row["transcript"] = "".join(parts)
            new_row.pop("time_zone", None)
            save_to_supabase(new_row)
        else:
            print(f"ERROR: No valid S3 bucket/key found in transcript_obj: {transcript_obj}")
            new_row["transcript"] = None
    else:
        print(f"ERROR: No valid transcript list found in transcript_obj: {transcript_obj}")
        new_row["transcript"] = None
    return new_row
    
def process_one_day_fetch_selection(date_str):
    region=os.environ.get("REGION")
    cluster_arn=os.environ.get("CLUSTER_ARN")
    secret_arn=os.environ.get("SECRET_ARN")
    db_name=os.environ.get("DB_NAME")
    
    client = boto3.client("rds-data", region_name=region)
    
    sql_qry = get_sql_query_aws_date(date_str)
    with st.sidebar.expander("SQL Query"):
        st.write(f"{sql_qry}")   
        
    response = client.execute_statement(resourceArn=cluster_arn,secretArn=secret_arn,database=db_name,sql=sql_qry,includeResultMetadata=True)

    records = response.get("records", [])
    column_metadata = response.get("columnMetadata", [])
    column_names = derive_column_names(column_metadata) if column_metadata else []

    rows = []
    for rec in records:
        new_row = process_one_record(rec, column_names, region)
        rows.append(new_row)
    return rows

def process_zoomsession_for_qna(supabase, row):
    session_id=row.get("session_id")
    transcript=row.get("transcript")
    topic=row.get("topic") or "General"
    model=os.environ.get("OPENAI_MODEL","gpt-5-mini")
    try:
        for q_topic, q_prompt in question_prompts.items():
            print(f"Processing QnA for session {session_id}, topic: {q_topic}")
            response_content=llm_request_response(supabase,model,session_id,transcript,topic,q_prompt)
            #print(f"Response Content: {response_content}")
        supabase.update_zoomsession_status(session_id, "QnA Completed")
    except Exception as e:
        print(f"ERROR processing ZoomSession for QnA for session {session_id}: {e}")

def process_one_day_qna(supabase, date_str):
    INITIAL_STATUS="Initial"
    st.write(f"DEBUG: Fetching QnA for date: {date_str}")
    rows=supabase.get_zoomsession_status_date(INITIAL_STATUS,date_str)
    
    st.write(f"DEBUG: Found {len(rows)} sessions with status {INITIAL_STATUS} for date {date_str}")
    if rows:
        st.json(rows)
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(process_zoomsession_for_qna, supabase, row) for row in rows]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"Error processing row: {e}")
        #for row in rows:
        #    process_zoomsession_for_qna(supabase, row)
    return rows
        
def process_one_session(session_id):
    region = os.environ.get("REGION")
    cluster_arn = os.environ.get("CLUSTER_ARN")
    secret_arn = os.environ.get("SECRET_ARN")
    db_name = os.environ.get("DB_NAME")
    if not all([region, cluster_arn, secret_arn, db_name]):
        st.error("Missing AWS DB env vars: REGION/CLUSTER_ARN/SECRET_ARN/DB_NAME.")
        return []

    sql_qry = get_sql_query_aws_session_id()
    with st.sidebar.expander("SQL Query"):
        st.write(sql_qry)

    try:
        client = boto3.client("rds-data", region_name=region)
        response = client.execute_statement(
            resourceArn=cluster_arn,
            secretArn=secret_arn,
            database=db_name,
            sql=sql_qry,
            parameters=[{"name": "session_id", "value": {"stringValue": str(session_id)}}],
            includeResultMetadata=True,
        )
    except Exception as e:
        st.error(f"Failed to fetch session `{session_id}` from AWS DB: {e}")
        return []

    records = response.get("records", [])
    if not records:
        st.warning(f"No AWS DB record found for session `{session_id}`.")
        return []

    column_names = derive_column_names(response.get("columnMetadata", []))
    return [process_one_record(rec, column_names, region) for rec in records]
    

def show_fetch_zoom_aws():
    env_secrets=st.secrets.get("env")  
    if env_secrets:
        setup_env_from_dict(env_secrets)
    
    supabase = SupabaseClient(url=os.environ["SUPABASE_URL"], key=os.environ['SUPABASE_KEY'])
        
    options = ["Sessions", "QnA","One Session"]
    fetch_selection = st.segmented_control("Fetch ", options, default='Sessions')
    st.markdown(f"Your selected options: {fetch_selection}.")
    if fetch_selection=="One Session":
        if session_id:=st.text_input("SessionId"):
            if st.button("Fetch Session"):
                rows = process_one_session(session_id)
                if rows:
                    st.dataframe(pd.DataFrame(rows))
        st.stop()
    
    today = datetime.date.today()
    last_week = today - datetime.timedelta(days=7)
    yesterday = today - datetime.timedelta(days=1)
    tomorrow = today + datetime.timedelta(days=1)
    d=st.date_input("Pick another date", value=(yesterday, tomorrow))
    if len(d)==2:
        start_date=d[0]
        end_date=d[1]
        print(f"DEBUG: {start_date=}, {end_date=}")

        if st.button("Fetch Data"):
            current_date=start_date
            while current_date <= end_date:
                date_str=current_date.strftime("%Y-%m-%d")
                print(f"DEBUG: Selected date: {date_str}")
                if fetch_selection=="Sessions":
                    rows= process_one_day_fetch_selection(date_str)
                if fetch_selection=="QnA":
                    rows = process_one_day_qna(supabase, date_str)


                df = pd.DataFrame(rows)
                with st.expander(f"Data {fetch_selection} for {date_str}"):
                    st.dataframe(df)
                current_date += datetime.timedelta(days=1)

if __name__ == "__main__":
    show_fetch_zoom_aws()
