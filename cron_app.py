import os
from dotenv import load_dotenv

load_dotenv() 

import base64
import datetime
import pandas as pd

try:
    import boto3
except ImportError:  # pragma: no cover - boto3 optional in tests
    boto3 = None  # type: ignore
from concurrent.futures import ThreadPoolExecutor, as_completed
import tiktoken

try:
    from agentmail import AgentMail
except ImportError:  # pragma: no cover - optional in tests
    AgentMail = None  # type: ignore

from utils import configs

from utils.utils_aws import save_to_supabase, fetch_s3_object, extract_field_value
from utils.utils_aws import derive_column_names, decode_json_value, get_sql_query_aws_date 

from utils.supabase_integration import SupabaseClient

from utils.utils_transcript_chat import llm_request_response
from utils.prompts import question_prompts

from utils.braintree_integration import sync_transactions_last_n_days
from utils.agentmail_integration import process_messages
from src.langsmith_logging import log_qna_response

TOKEN_ENCODING_ENV = "TOKEN_COUNT_ENCODING"
_token_encoder = None
DEFAULT_PROMPT_GROUP = "common"


def _mask_secret(value):
    """Return value with only the first three characters visible."""
    if value is None:
        return ""
    text = str(value)
    if len(text) <= 3:
        return text + "***"
    return text[:3] + "*" * (len(text) - 3)

def get_bucket_contents(bucket,key,region):
    content=""
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
    region=os.environ.get("AWS_REGION")
    cluster_arn=os.environ.get("AWS_CLUSTER_ARN")
    secret_arn=os.environ.get("AWS_SECRET_ARN")
    db_name=os.environ.get("AWS_DB_NAME")

    if boto3 is None:
        raise RuntimeError("boto3 is required to fetch Zoom sessions from AWS")
    
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

def qna_email_out(topic, response_list, prompt_group, to_address):
    if AgentMail is None:
        raise RuntimeError("AgentMail SDK is required to send QnA emails")
    API_KEY=os.environ['AGENTMAIL_API_KEY']
    FROM_ADDRESS=os.environ['AGENTMAIL_FROM_ADDRESS'] 
    client = AgentMail(api_key=API_KEY)
    subject = f"[{prompt_group}] ACSV Session Summary for {topic}"
    text="\n\n".join([ f"TOPIC: {rsp['qt']}\n {rsp['rc']} " for rsp in response_list])
    print(f"\n\nDEBUGGING: {subject=}, {text=}, to={to_address}")
    sent_message = client.inboxes.messages.send(
        inbox_id = FROM_ADDRESS,
        to = to_address,
        labels=["session","bot","test"],
        subject=subject,
        text=text,
        #html="<div dir=\"ltr\">Hello,<br /><br />I'm just testing..."
    )
    print(f"Message sent successfully with ID: {sent_message.message_id}")

def _load_qna_email_map(supabase):
    """Return a dict of prompt_group -> recipient email."""
    mapping = {}
    rows = []
    try:
        rows = supabase.list_qna_emails()
    except Exception as exc:  # pragma: no cover - defensive only
        print(f"Error loading qna email map: {exc}")
        return mapping
    for row in rows or []:
        group = (row.get("prompt_group") or "").strip()
        email = (row.get("email") or "").strip()
        if group and email:
            mapping[group] = email
    return mapping


def _resolve_qna_recipient(prompt_group, qna_email_map, default_address):
    normalized_group = (prompt_group or "").strip()
    if normalized_group and qna_email_map.get(normalized_group):
        return qna_email_map[normalized_group]
    return default_address


def process_zoomsession_for_qna(supabase, row, qna_email_map=None, default_to_address=None):
    session_id=row.get("session_id")
    transcript=row.get("transcript")
    topic=row.get("topic") or "General"
    model=os.environ.get("OPENAI_MODEL","gpt-5-mini")
    responses_by_group={}
    try:
        for prompt in question_prompts:
            q_topic = prompt["title"]
            q_prompt = prompt["prompt"]
            q_group = prompt.get("prompt_group") or DEFAULT_PROMPT_GROUP
            print(f"Processing QnA for session {session_id}, topic: {q_topic}")
            response_content=llm_request_response(
                supabase,
                model,
                session_id,
                transcript,
                topic,
                q_prompt,
                q_group,
            )
            #print(f"Response Content: {response_content}")
            responses_by_group.setdefault(q_group, []).append({"qt":q_topic,"rc":response_content})
            log_qna_response(
                session_id=session_id,
                topic=topic,
                question_topic=q_topic,
                prompt=q_prompt,
                transcript=transcript,
                response=response_content,
                source="cron_app",
                tags=["cron"],
            )
        supabase.update_zoomsession_status(session_id, "QnA Completed")
        for group, response_list in responses_by_group.items():
            to_address=_resolve_qna_recipient(group, qna_email_map or {}, default_to_address)
            if not to_address:
                print(f"Skipping QnA email for group '{group}': no recipient configured.")
                continue
            qna_email_out(topic,response_list,group,to_address)
    except Exception as e:
        print(f"ERROR processing ZoomSession for QnA for session {session_id}: {e}")


def process_one_day_qna(supabase, date_str):
    INITIAL_STATUS="Initial"
    print(f"DEBUG: Fetching QnA for date: {date_str}")
    rows=supabase.get_zoomsession_status_date(INITIAL_STATUS,date_str)
    qna_email_map=_load_qna_email_map(supabase)
    default_address=os.environ.get("AGENTMAIL_TO_ADDRESS")
    
    print(f"DEBUG: Found {len(rows)} sessions with status {INITIAL_STATUS} for date {date_str}")
    if rows:
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(
                    process_zoomsession_for_qna,
                    supabase,
                    row,
                    qna_email_map,
                    default_address,
                )
                for row in rows
            ]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"Error processing row: {e}")
        #for row in rows:
        #    process_zoomsession_for_qna(supabase, row, qna_email_map, default_address)
    return rows

def process_braintree(supabase,duration):
    merchant_id=os.environ.get("BRAINTREE_MERCHANT_ID")
    public_key=os.environ.get("BRAINTREE_PUBLIC_KEY")
    private_key=os.environ.get("BRAINTREE_PRIVATE_KEY")
    sync_transactions_last_n_days(supabase, duration, merchant_id,public_key,private_key)
    return

def process_finance_mails(supabase,duration):
    print("TO-DO TO-DO TO-DO: Finance mail processing")
    finance_allowed_list=configs.finance_approved_list
    params={'allowed_senders':finance_allowed_list}
    print(f"Params are: {params=}")
    process_messages(print,'finance@aiclubagent.com',['unread'], ['processed'],['unread'], params)
    
    return

def _normalize_transcript(transcript):
    if transcript is None:
        return ""
    if isinstance(transcript, (list, tuple)):
        return "\n".join(str(part) for part in transcript if part)
    if isinstance(transcript, dict):
        return str(transcript)
    return str(transcript)

def _count_tokens(text: str) -> int:
    global _token_encoder
    if _token_encoder is None:
        encoding_name = os.environ.get(TOKEN_ENCODING_ENV, "cl100k_base")
        try:
            _token_encoder = tiktoken.get_encoding(encoding_name)
        except Exception:
            _token_encoder = tiktoken.get_encoding("cl100k_base")
    return len(_token_encoder.encode(text))

def process_one_day_token_counts(supabase, date_str):
    rows = supabase.get_zoomsession_negative_tokenlength_by_date(date_str, 0)
    print(f"DEBUG TokenCount: Found {len(rows)} sessions for date {date_str}")
    updated = 0
    for row in rows:
        transcript_text = _normalize_transcript(row.get("transcript")).strip()
        if not transcript_text:
            continue
        try:
            token_count = _count_tokens(transcript_text)
        except Exception as exc:
            session_id = row.get("session_id")
            print(f"ERROR counting tokens for session {session_id}: {exc}")
            continue
        supabase.update_zoom_session_tokenlength(row.get("id"), token_count)
        updated += 1
    print(f"DEBUG TokenCount: Updated {updated} sessions for date {date_str}")
    return updated
        
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
        process_finance_mails(supabase,int(duration))
    if cronId=="TokenCount":
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime("%Y-%m-%d")
            print(f"DEBUG TokenCount: Selected date: {date_str}")
            process_one_day_token_counts(supabase, date_str)
            current_date += datetime.timedelta(days=1)
        
def main():
    for key, value in os.environ.items():
        print(key, _mask_secret(value))
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
    print(f"Trace: Before TokenCount")
    main_cron_processing(supabase_url, supabase_key, "TokenCount", duration)
    print(f"Trace: After All")
    
if __name__ == "__main__":
    main()
