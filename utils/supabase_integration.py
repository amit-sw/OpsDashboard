import os
from datetime import datetime, timedelta, timezone
from supabase import create_client, Client


class SupabaseClient:
    def __init__(self, url, key):
        try:
            self.supabase: Client = create_client(url, key)
        except Exception as e:
            print(f"ERROR. Error connecting to Supabase: {e}. You provided {url=}, {key=}")
            self.supabase = None

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
            response = (
                self.supabase
                .table('braintree_transactions')
                .select('*')
                .gte('created_at', cutoff)
                .execute()
            )
            return response.data or []
        except Exception as e:
            print(f"Error fetching Braintree transactions from database: {e}")
            return []
