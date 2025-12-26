from __future__ import annotations

import os

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any, Dict

try:
    from supabase import create_client, Client  # type: ignore
except ImportError:  # pragma: no cover - optional in unit tests
    create_client = None  # type: ignore
    Client = Any  # type: ignore


def _mask_secret(value):
    """Return a secret value with only its first three characters visible."""
    if value is None:
        return ""
    text = str(value)
    if len(text) <= 3:
        return text + "***"
    return text[:3] + "*" * (len(text) - 3)

def _import_pandas():
    try:
        import pandas as pandas_module  # type: ignore
    except Exception as exc:  # pragma: no cover - optional in tests
        raise RuntimeError("pandas is required for this operation") from exc
    return pandas_module


if TYPE_CHECKING:  # pragma: no cover
    import pandas as pd

DEFAULT_DAYS=91
DEFAULT_FULL_INFO=365*10
DEFAULT_TABLE_LIMIT=200

USED_SUPABASE_TABLES=tuple(sorted({
    "authorized_users",
    "braintree_transactions",
    "calendar_events",
    "confluence_pages",
    "gm_tokens",
    "gmail_message_index",
    "gmail_messages",
    "instructors",
    "qna_emails",
    "question_prompts",
    "research_program_students",
    "session_qna",
    "yt_prompt",
    "yt_prompts",
    "yt_qna",
    "yt_tasks",
    "yt_videos",
    "yt_video_qna",
    "zoom_sessions",
}))

def format_revenue(title: str, sdf: pd.DataFrame, scol: str, n: int) -> str:
    df = sdf.sort_values(scol, ascending=False).copy()
    df = df.head(n)
    df[scol] = df[scol].astype(str)
    lines = [f"{getattr(row, scol)} {row.amount}" for row in df.itertuples(index=False)]
    lines_str="\n".join(lines)

    # Wrap with separators
    result = f"\n*********\n{title}\n\n\n{lines_str} \n*********"
    return result


class SupabaseClient:
    def __init__(self, url, key):
        try:
            if create_client is None:
                raise ImportError("supabase client is not installed")
            self.supabase: Client = create_client(url, key)
        except Exception as e:
            print(
                "ERROR. Error connecting to Supabase: "
                f"{e}. You provided {url=}, key={_mask_secret(key)}"
            )
            self.supabase = None

    def list_known_tables(self):
        """Return the sorted list of application tables tracked in Supabase."""
        return list(USED_SUPABASE_TABLES)

    def fetch_table_rows(self, table_name, limit=DEFAULT_TABLE_LIMIT):
        """Fetch up to ``limit`` rows from the requested table."""
        if not self.supabase or table_name not in USED_SUPABASE_TABLES:
            return []
        row_limit = min(max(int(limit or DEFAULT_TABLE_LIMIT), 1), 2000)
        try:
            response = (
                self.supabase
                .table(table_name)
                .select('*')
                .limit(row_limit)
                .execute()
            )
            return response.data or []
        except Exception as e:
            print(f"Error pulling table rows: {e}. {table_name=}, {row_limit=}")
            return []

    def get_calendar_events_from_db(self):
        """Gets calendar events from the 'calendar_events' table in Supabase."""
        try:
            response = self.supabase.table('calendar_events').select('*').execute()
            return response.data
        except Exception as e:
            print(f"ERROR. Error getting calendar events from database: {e}")
            return []

    def get_students_from_db(self):
        """Gets student data from the 'research_program_students' table in Supabase."""
        try:
            response = self.supabase.table('research_program_students').select('full_name, student_emails, parent_emails,instuctor_name,mentor_name,ops_name').execute()
            return response.data
        except Exception as e:
            print(f"Error fetching students from database: {e}")
            return []

    def list_question_prompts(self, status: str | None = "active", prompt_group: str | None = None):
        """Return question_prompt rows filtered by optional status/group."""
        if not self.supabase:
            return []
        try:
            query = self.supabase.table('question_prompts').select('*')
            if status:
                query = query.eq('status', status)
            if prompt_group:
                query = query.eq('prompt_group', prompt_group)
            response = query.order('title').execute()
            return response.data or []
        except Exception as e:
            print(f"Error fetching question prompts: {e}")
            return []

    def insert_question_prompt(self, title: str, prompt: str, prompt_group: str, status: str = "active"):
        """Insert a new question prompt row."""
        if not self.supabase:
            return []
        try:
            payload = {
                'title': title,
                'prompt': prompt,
                'prompt_group': prompt_group,
                'status': status,
            }
            response = self.supabase.table('question_prompts').insert(payload).execute()
            return response.data or []
        except Exception as e:
            print(f"Error inserting question prompt: {e}")
            return []

    def update_question_prompt(self, prompt_id: int, updates: Dict[str, str]):
        """Update fields on an existing question prompt row."""
        if not self.supabase or not prompt_id or not updates:
            return []
        try:
            response = (
                self.supabase
                .table('question_prompts')
                .update(updates)
                .eq('id', prompt_id)
                .execute()
            )
            return response.data or []
        except Exception as e:
            print(f"Error updating question prompt: {e}")
            return []

    def list_qna_emails(self):
        """Return sorted rows from the qna_emails table."""
        if not self.supabase:
            return []
        try:
            response = (
                self.supabase
                .table('qna_emails')
                .select('*')
                .order('prompt_group')
                .order('email')
                .execute()
            )
            return response.data or []
        except Exception as e:
            print(f"Error fetching qna_emails: {e}")
            return []

    def insert_qna_email(self, prompt_group: str, email: str):
        """Insert a qna_email row."""
        if not self.supabase:
            return []
        try:
            payload = {
                'prompt_group': prompt_group,
                'email': email,
            }
            response = self.supabase.table('qna_emails').insert(payload).execute()
            return response.data or []
        except Exception as e:
            print(f"Error inserting qna_email: {e}")
            return []

    def update_qna_email(self, record_id: int, updates: Dict[str, str]):
        """Update qna_email fields."""
        if not self.supabase or not record_id or not updates:
            return []
        try:
            response = (
                self.supabase
                .table('qna_emails')
                .update(updates)
                .eq('id', record_id)
                .execute()
            )
            return response.data or []
        except Exception as e:
            print(f"Error updating qna_email: {e}")
            return []

    def get_student_emails_from_db(self):
        """Gets calendar events from the 'calendar_events' table in Supabase."""
        try:
            response = self.supabase.table('research_program_students').select('*').execute()
            return response.data
        except Exception as e:
            print(f"Error getting calendar events from database: {e}")
            return []

    def update_calendar_events_in_db(self, events):
        """Updates the 'calendar_events' table in Supabase with the given events."""
        try:
            # Insert new events
            if events:
                data_to_insert = []
                for event in events:
                    start = event['start'].get('dateTime', event['start'].get('date'))
                    end = event['end'].get('dateTime', event['end'].get('date'))
                    data_to_insert.append({
                        'event_id': event['id'],
                        'summary': event['summary'],
                        'start_time': start,
                        'end_time': end,
                    })
                self.supabase.table('calendar_events').insert(data_to_insert).execute()
        except Exception as e:
            print(f"Error updating calendar events in database: {e}")

    def get_user_from_db(self, email):
        """Fetches user details from the 'users' table based on email."""
        try:
            response = self.supabase.table('authorized_users').select('*').eq('email', email).execute()
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            print(f"Error fetching user from database: {e}")
            return None

    def get_token_from_db(self):
        """Fetches the first Google Meet token marked as active."""
        try:
            response = self.supabase.table('gm_tokens').select('*').eq('status', 'active').execute()
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            print(f"Error fetching user from database: {e}")
            return None

    def set_token_in_db(self, params):
        """Stores a new token row while marking previous tokens inactive."""
        try:
            self.supabase.table('gm_tokens').update({'status': 'inactive'}).neq('status', 'inactive').execute()
            if params is None:
                return None
            response = self.supabase.table('gm_tokens').insert({'token': params, 'status': 'active'}).execute()
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            print(f"Error storing token in database: {e}")
            return None

    def get_instructors(self):
        try:
            response = self.supabase.table('instructors').select('*').execute()
            return response.data or []
        except Exception as e:
            print(f"Error fetching instructors: {e}")
            return []

    def create_instructor(self, instructor):
        try:
            response = self.supabase.table('instructors').insert(instructor).execute()
            return response.data or []
        except Exception as e:
            print(f"Error creating instructor: {e}")
            return []

    def upsert_instructor(self, instructor):
        try:
            response = (
                self.supabase
                .table('instructors')
                .upsert(instructor)
                .execute()
            )
            return response.data or []
        except Exception as e:
            print(f"Error upserting instructor: {e}")
            return []

    def update_instructor(self, instructor_id, updates):
        try:
            response = (
                self.supabase
                .table('instructors')
                .update(updates)
                .eq('id', instructor_id)
                .execute()
            )
            return response.data or []
        except Exception as e:
            print(f"Error updating instructor: {e}")
            return []
        
    def update_instructors(self,row_id,column_name,new_value):
        updates={column_name:new_value}
        upd=self.update_instructor(row_id, updates)
        return upd
        
    def get_confluence_pages(self, full_name):
        """Fetches user details from the 'users' table based on email."""
        try:
            response = self.supabase.table('confluence_pages').select('*').eq('full_name', full_name).execute()
            if response.data:
                return response.data
            return None
        except Exception as e:
            print(f"Error fetching user from database: {e}")
            return None
        
    def insert_gmail_index_records(self, rows):
        try:
            response = self.supabase.table("gmail_message_index").insert(rows).execute()
            return response.data or []
        except Exception as e:
            print(f"Error creating instructor: {e}")
            return []
        
    def insert_messages_batch(self,rows):
        # rows: [{id, thread_id, internal_ms, headers, snippet, body_full, raw_json}]
        if not rows:
            return
        response=self.supabase.table("gmail_messages").insert(rows).execute()
        return response

    def get_ids(self,ymd: str, fetch_bodies: bool = True):
        """
        ymd: 'YYYY-MM-DD' (UTC)
        Fetch IDs from gmail_message_index for that date, hydrate with Gmail API, and upsert into gmail_messages.
        """
        # 1) get IDs for that day
        response = self.supabase.table("gmail_message_index").select("id, thread_id, internal_ms").eq("ymd", ymd).order("internal_ms", desc=False).execute()
        ids=response.data or []
        return ids
#
# For downnload zoom session information from AWS
#
    def create_zoom_session(self, params):
        try:
            response = self.supabase.table('zoom_sessions').insert(params).execute()
            #print(f"DEBUG: Created zoom session: {response.data}")
            return response.data or []
        except Exception as e:
            print(f"Error creating instructor: {e}")
            return []
        
    def get_zoom_session(self, session_id):
        try:
            response = self.supabase.table('zoom_sessions').select('*').eq('session_id', session_id).execute()
            return response.data or []
        except Exception as e:
            print(f"Error creating instructor: {e}")
            return []
        
    def create_session_qna(self, rows):
        try:
            response = self.supabase.table("session_qna").insert(rows).execute()
            return response.data or []
        except Exception as e:
            print(f"Error creating instructor: {e}")
            return []
        
    def get_session_qna(self, session_id):
        try:
            response = self.supabase.table('session_qna').select('*').eq('session_id', session_id).execute()
            return response.data or []
        except Exception as e:
            print(f"Error creating instructor: {e}")
            return []
    
    def get_zoomsession_status_date(self, qna_status, date):
        try:
            response = self.supabase.table('zoom_sessions').select('*').eq('qna_status', qna_status).eq('date', date).execute()
            return response.data or []
        except Exception as e:
            print(f"Error creating instructor: {e}")
            return []
        
    def get_zoomsession_negative_tokenlength_by_date(self, date, threshold=0):
        try:
            response = (
                self.supabase.table('zoom_sessions')
                .select('*')
                .eq('date', date)
                .lt('transcript_token_count', threshold)
                .execute()
            )
            return response.data or []
        except Exception as e:
            print(f"Error fetching zoom sessions for token update: {e}")
            return []
        
    def update_zoomsession_status(self, session_id,qna_status):
        try:
            response = self.supabase.table('zoom_sessions').update({'qna_status': qna_status}).eq('session_id', session_id).execute()
            return response.data or []
        except Exception as e:
            print(f"Error creating instructor: {e}")
            return []
        
#
# For transcript token length related items
#
    def get_zoom_session_negative_tokenlength(self, threshold):
        try:
            response = self.supabase.table('zoom_sessions').select('*').lt('transcript_token_count', threshold).limit(1).execute()
            return response.data or []
        except Exception as e:
            print(f"Error creating zoom-session-negative-response: {e}")
            return []
        
    def update_zoom_session_tokenlength(self, id, token_length):
        try:
            response = self.supabase.table('zoom_sessions').update({'transcript_token_count': token_length}).eq('id', id).execute()
            return response.data or []
        except Exception as e:
            print(f"Error updating zoom-session-negative-response: {e}")
            return []

#
# For YT video Prompt question answering system
#

    def insert_yt_video_records(self, rows):
        try:
            response = self.supabase.table("yt_videos").insert(rows).execute()
            return response.data or []
        except Exception as e:
            print(f"Error creating instructor: {e}")
            return []
        
    def insert_yt_video_qna(self, rows):
        try:
            response = self.supabase.table("yt_video_qna").insert(rows).execute()
            return response.data or []
        except Exception as e:
            print(f"Error creating instructor: {e}")
            return []
        
    def insert_yt_prompt(self, rows):
        try:
            response = self.supabase.table("yt_prompt").insert(rows).execute()
            return response.data or []
        except Exception as e:
            print(f"Error creating instructor: {e}")
            return []
        
    def get_yt_video_records(self, video_id):
        try:
            response = self.supabase.table('yt_videos').select('*').eq('video_id', video_id).execute()
            return response.data or []
        except Exception as e:
            print(f"Error fetching YT Videos from database: {e}")
            return None
        
    def get_yt_video_qna(self, video_id):
        try:
            response = self.supabase.table('yt_qna').select('*').eq('video_id', video_id).execute()
            return response.data or []
        except Exception as e:
            print(f"Error fetching YT Q&A from database: {e}")
            return None
        
    def get_yt_prompts(self, task_id):
        try:
            response = self.supabase.table('yt_prompts').select('*').eq('task_id', task_id).execute()
            return response.data or []
        except Exception as e:
            print(f"Error fetching YT Prompts from database: {e}")
            return None
        
    def get_yt_tasks(self):
        try:
            response = self.supabase.table('yt_tasks').select('*').execute()
            if response.data:
                return response.data
            return None
        except Exception as e:
            print(f"Error fetching YT Tasks from database: {e}")
            return None
        
    def upsert_braintree(self, record):
        try:
            response = (
                self.supabase
                .table('braintree_transactions')
                .upsert(record)
                .execute()
            )
            return response.data or []
        except Exception as e:
            print(f"Error upserting record: {e}")
            return []
        
    def get_braintree(self):
        try:
            response = self.supabase.table('braintree_transactions').select('*').execute()
            if response.data:
                return response.data
            return None
        except Exception as e:
            print(f"Error fetching Braintree transactions from database: {e}")
            return None
        
    def get_braintree_last_n_days(self,n):
        try:
            cutoff = (datetime.now(timezone.utc) - timedelta(days=n)).isoformat()
            limit = 1000
            offset = 0
            rows = []
            while True:
                batch = (
                    self.supabase
                    .table('braintree_transactions')
                    .select('*')
                    .gte('created_at', cutoff)
                    .range(offset, offset + limit - 1)
                    .execute()
                ).data or []
                rows.extend(batch)
                if len(batch) < limit:
                    break
                offset += limit
            return rows
        except Exception as e:
            print(f"Error fetching Braintree transactions from database: {e}")
            return []
        
    def get_braintree_formatted_last_n_days(self, n):
        trans=self.get_braintree_last_n_days(n)
        results=[]
        for t in trans:
            status=t.get('status')
            dat=t.get('created_at')
            amount=t.get('amount')
            customer_email=t.get('customer_email')
            if status=="settled":
                results.append(f"Date={dat},Amount={amount},Customer={customer_email}")
        return results
    
    def get_basic_braintree_info(self, num_days):
        records=self.get_braintree_last_n_days(DEFAULT_FULL_INFO)
        pd = _import_pandas()
        df1=pd.DataFrame(records)
        df1 = df1[df1["status"] == "settled"]
        df1["created_at"] = pd.to_datetime(df1["created_at"])
        
        df1["day"] = df1["created_at"].dt.to_period("D")
        df1["month"] = df1["created_at"].dt.to_period("M")
        df1["quarter"] = df1["created_at"].dt.to_period("Q")
        df1["year"] = df1["created_at"].dt.to_period("Y")
        daily_revenue = df1.groupby("day")["amount"].sum().reset_index()
        monthly_revenue = df1.groupby("month")["amount"].sum().reset_index()
        quarterly_revenue = df1.groupby("quarter")["amount"].sum().reset_index()
        annual_revenue = df1.groupby("year")["amount"].sum().reset_index()
        
        #st.caption("Basic braintree information")
        #st.dataframe(df1)
        #st.dataframe(daily_revenue)
        #st.dataframe(monthly_revenue)
        #st.dataframe(quarterly_revenue)
        #st.dataframe(annual_revenue)
        #combined="Background information:\n"+"\n".join(records)
        daily_revenue_str=format_revenue("Daily Revenue", daily_revenue, "day", num_days)
        monthly_revenue_str=format_revenue("Monthly Revenue", monthly_revenue, "month", 1234)
        quarterly_revenue_str=format_revenue("Quarterly Revenue", quarterly_revenue, "quarter", 1234)
        annual_revenue_str=format_revenue("Annual Revenue", annual_revenue, "year", 1234)
        response_str="All revenue amounts are in USD \n"+annual_revenue_str+quarterly_revenue_str+monthly_revenue_str+ daily_revenue_str
        #with st.sidebar.expander("Raw data"):
        #    st.write(response_str)
        return response_str
