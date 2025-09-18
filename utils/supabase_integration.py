import os
from supabase import create_client, Client


class SupabaseClient:
    def __init__(self, url, key):
        try:
            self.supabase: Client = create_client(url, key)
        except Exception as e:
            print(f"ERROR. Error connecting to Supabase: {e}")
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
            response = self.supabase.table('research_program_students').select('full_name, student_emails, parent_emails').execute()
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
        """Fetches token details from the 'gm_tokens' table based on email."""
        try:
            response = self.supabase.table('gm_tokens').select('*').execute()
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            print(f"Error fetching user from database: {e}")
            return None