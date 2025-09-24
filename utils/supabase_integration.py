import os
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