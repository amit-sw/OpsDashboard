import os
from dotenv import load_dotenv

load_dotenv() 

import base64
import datetime
import pandas as pd

import boto3
from concurrent.futures import ThreadPoolExecutor, as_completed

from agentmail import AgentMail

from utils.utils_aws import save_to_supabase, fetch_s3_object, extract_field_value
from utils.utils_aws import derive_column_names, decode_json_value, get_sql_query_aws_date 

from utils.supabase_integration import SupabaseClient

from utils.utils_transcript_chat import llm_request_response
from utils.prompts import question_prompts

from utils.braintree_integration import sync_transactions_last_n_days

def process_one_record(rec, column_names, region):
    values = [extract_field_value(field) for field in rec]
    new_row = dict(zip(column_names, values))

    transcript_obj = decode_json_value(new_row.get("transcript"))
    #print(f"DEBUG: {transcript_obj=} with type {type(transcript_obj)}")

    bucket = None
    key = None
    if isinstance(transcript_obj, list) and transcript_obj:
        entry = transcript_obj[0]
        if isinstance(entry, dict):
            bucket = entry.get("bucket")
            key = entry.get("key")

    if bucket and key:
        #print("IF C")
        s3_content = fetch_s3_object(bucket, key, region)
        try:
            #print("STEP A")
            new_row["transcript"] = s3_content.decode("utf-8")
            #new_row["transcript_encoding"] = "utf-8"
        except UnicodeDecodeError:
            print("STEP B")
            new_row["transcript"] = base64.b64encode(s3_content).decode("ascii")
            #new_row["transcript_encoding"] = "base64"
        #new_row["transcript_bucket"] = bucket
        #new_row["transcript_key"] = key
        new_row.pop('time_zone', None)
        save_to_supabase(new_row)
        return new_row
    else:
        print(f"ERROR: No valid S3 bucket/key found in transcript_obj: {transcript_obj}")
        new_row["transcript"] = None
        #new_row["transcript_encoding"] = None
        #save_to_supabase(new_row)
        return new_row
    
def process_one_day_fetch_selection(date_str):
    region=os.environ.get("AWS_REGION")
    cluster_arn=os.environ.get("AWS_CLUSTER_ARN")
    secret_arn=os.environ.get("AWS_SECRET_ARN")
    db_name=os.environ.get("AWS_DB_NAME")
    
    client = boto3.client("rds-data", region_name=region)
    
    sql_qry = get_sql_query_aws_date(date_str)
        
    response = client.execute_statement(resourceArn=cluster_arn,secretArn=secret_arn,database=db_name,sql=sql_qry,includeResultMetadata=True)

    records = response.get("records", [])
    column_metadata = response.get("columnMetadata", [])
    column_names = derive_column_names(column_metadata) if column_metadata else []

    rows = []
    for rec in records:
        new_row = process_one_record(rec, column_names, region)
        rows.append(new_row)
    return rows

def email_out(topic,response_list):
    API_KEY=os.environ['AGENTMAIL_API_KEY']
    FROM_ADDRESS=os.environ['AGENTMAIL_FROM_ADDRESS'] 
    TO_ADDRESS=os.environ['AGENTMAIL_TO_ADDRESS'] 
    client = AgentMail(api_key=API_KEY)
    subject = f"ACSV Session Summary for {topic}"
    text="\n\n".join([ f"TOPIC: {rsp['qt']}\n {rsp['rc']} " for rsp in response_list])
    print(f"\n\nDEBUGGING: {subject=}, {text=}")
    sent_message = client.inboxes.messages.send(
        inbox_id = FROM_ADDRESS,
        to = TO_ADDRESS,
        labels=["session","bot","test"],
        subject=subject,
        text=text,
        #html="<div dir=\"ltr\">Hello,<br /><br />I'm just testing..."
    )
    print(f"Message sent successfully with ID: {sent_message.message_id}")

def process_zoomsession_for_qna(supabase, row):
    session_id=row.get("session_id")
    transcript=row.get("transcript")
    topic=row.get("topic") or "General"
    model=os.environ.get("OPENAI_MODEL","gpt-5-mini")
    response_list=[]
    try:
        for q_topic, q_prompt in question_prompts.items():
            print(f"Processing QnA for session {session_id}, topic: {q_topic}")
            response_content=llm_request_response(supabase,model,session_id,transcript,topic,q_prompt)
            #print(f"Response Content: {response_content}")
            response_list.append({"qt":q_topic,"rc":response_content})
        supabase.update_zoomsession_status(session_id, "QnA Completed")
        email_out(topic,response_list)
    except Exception as e:
        print(f"ERROR processing ZoomSession for QnA for session {session_id}: {e}")


def process_one_day_qna(supabase, date_str):
    INITIAL_STATUS="Initial"
    print(f"DEBUG: Fetching QnA for date: {date_str}")
    rows=supabase.get_zoomsession_status_date(INITIAL_STATUS,date_str)
    
    print(f"DEBUG: Found {len(rows)} sessions with status {INITIAL_STATUS} for date {date_str}")
    if rows:
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

def process_braintree(supabase,duration):
    merchant_id=os.environ.get("BRAINTREE_MERCHANT_ID")
    public_key=os.environ.get("BRAINTREE_PUBLIC_KEY")
    private_key=os.environ.get("BRAINTREE_PRIVATE_KEY")
    sync_transactions_last_n_days(supabase, duration, merchant_id,public_key,private_key)
    return

def process_finance_mails(supabase,current_date,end_date):
    return
        
def main_cron_processing(supabase_url, supabase_key, cronId, duration):
    supabase = SupabaseClient(url=supabase_url, key=supabase_key)
    
    end_date = datetime.date.today()+datetime.timedelta(days=1)
    start_date = end_date - datetime.timedelta(days=int(duration))
    
    if cronId=="Sessions":    
        current_date=start_date
        while current_date <= end_date:
            date_str=current_date.strftime("%Y-%m-%d")
            print(f"DEBUG Sessions: Selected date: {date_str}")
            rows= process_one_day_fetch_selection(date_str)
            current_date += datetime.timedelta(days=1)

    if cronId=="QnA":
        current_date=start_date    
        while current_date <= end_date:
            date_str=current_date.strftime("%Y-%m-%d")
            print(f"DEBUG QnA: Selected date: {date_str}")
            rows = process_one_day_qna(supabase, date_str)
            current_date += datetime.timedelta(days=1)
        
    if cronId=="BrainTree":
        process_braintree(supabase,int(duration))
    if cronId=="FinanceMails":
        process_finance_mails(supabase,current_date,end_date)
        
def main():
    for key, value in os.environ.items():
        print(key, value)
    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key=os.environ['SUPABASE_KEY']
    
    openai_model=os.environ.get("OPENAI_MODEL","gpt-5-mini")
    openai_api_key=os.environ.get("OPENAI_API_KEY","Invalid_Key")

    duration=os.environ.get("duration","2")
    
    print(f"Trace: Before Sessions")
    main_cron_processing(supabase_url, supabase_key, "Sessions", duration)
    print(f"Trace: Before QnA")
    main_cron_processing(supabase_url, supabase_key, "QnA", duration)
    print(f"Trace: Before BrainTree")
    main_cron_processing(supabase_url, supabase_key, "BrainTree", duration)
    print(f"Trace: Before FinanceMails")
    main_cron_processing(supabase_url, supabase_key, "FinanceMails", duration)
    print(f"Trace: After All")
    
if __name__ == "__main__":
    main()