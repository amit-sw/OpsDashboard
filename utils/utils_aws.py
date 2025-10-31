import os
import json

import boto3

from utils.supabase_integration import SupabaseClient



def get_sql_query():

    QUERY = """
    SELECT session_id,project_id,instructor_names,youtube_link,session_summary,timestamp,date,time_zone,zoom_link,topic,transcript
    FROM navigator_PRODUCTION.project_sessions
    WHERE youtube_link != '[]'
    AND topic LIKE '%Trane%'
    AND topic NOT LIKE '%Teacher Training%'
    ORDER BY timestamp DESC
    LIMIT 20;
    """
    return QUERY

def get_sql_query_aws_date(date_str):
    date_start = f"{date_str} 00:00:00"
    date_end = f"{date_str} 23:59:59"
    print(f"DEBUG: fetch-aws: date_start={date_start}, date_end={date_end}")

    QUERY = f"""
    SELECT session_id,project_id,instructor_names,youtube_link,session_summary,timestamp,date,time_zone,zoom_link,topic,transcript
    FROM navigator_PRODUCTION.project_sessions
    WHERE youtube_link != '[]'
    AND date BETWEEN '{date_start}' AND '{date_end}'
    ORDER BY date DESC
    LIMIT 200;
    """
    return QUERY

def setup_env_from_dict(dict_env):
    for k in dict_env.keys():
        v=dict_env.get(k)
        #print(f"DEBUG: setup-env-from-dict: {k=},{v=}")
        os.environ[k]=v

def save_to_supabase(params):
    supabase = SupabaseClient(url=os.environ["SUPABASE_URL"], key=os.environ['SUPABASE_KEY'])
    resp=supabase.create_zoom_session(params)
    return resp


def fetch_s3_object(bucket: str, key: str, region: str) -> bytes:
    """Download an object from S3 and return its raw bytes."""
    s3_client = boto3.client("s3", region_name=region)
    response = s3_client.get_object(Bucket=bucket, Key=key)
    return response["Body"].read()

def extract_field_value(field: dict):
    """Normalize RDS Data API field dicts to plain Python values."""
    if field.get("isNull"):
        return None

    for key in (
        "stringValue",
        "longValue",
        "doubleValue",
        "booleanValue",
        "blobValue",
        "arrayValue",
        "decimalValue",
    ):
        if key in field:
            return field[key]

    # Fallback to any remaining value (covers newer field types).
    return next(iter(field.values()), None)

def derive_column_names(metadata: list) -> list:
    """Return readable column names from metadata, with sensible fallbacks."""
    names = []
    #print(f"DEBUG: Column Metadata: {metadata=}")
    for idx, meta in enumerate(metadata):
        name = meta.get("name") or meta.get("label")
        if not name:
            name = f"column_{idx}"
        names.append(name)
    return names

def decode_json_value(value):
    """Best-effort JSON decoder that handles double-encoded strings."""
    parsed = value
    while isinstance(parsed, str):
        stripped = parsed.strip()
        if not stripped:
            return stripped

        try:
            parsed = json.loads(parsed)
            continue
        except json.JSONDecodeError:
            pass

        try:
            unescaped = bytes(parsed, "utf-8").decode("unicode_escape")
            parsed = json.loads(unescaped)
        except (UnicodeDecodeError, json.JSONDecodeError):
            break

    return parsed