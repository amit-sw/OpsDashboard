import streamlit as st

from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timezone, timedelta

class CalendarClient:
    def __init__(self, credentials):
        self.service = None
        try:
            creds = service_account.Credentials.from_service_account_info(credentials)
            self.service = build('calendar', 'v3', credentials=creds)
        except Exception as e:
            print(f"Error creating Google Calendar service: {e}; {credentials=}")

    def get_calendar_events(self, future_only=True, max_days=30):
        try:
            now = datetime.now(timezone.utc)
            start = now if future_only else now - timedelta(days=max_days)
            time_min = start.isoformat().replace("+00:00", "Z")
            time_max = (now + timedelta(days=max_days)).isoformat().replace("+00:00", "Z")
            events_result = self.service.events().list(
                calendarId='coordinator@pyxeda.ai',
                timeMin=time_min,
                timeMax=time_max,
                maxResults=2000,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            events = events_result.get('items', [])
            print(f"Fetched {len(events)=} events from Google Calendar.")
            return events
        except Exception as e:
            print(f"Error fetching calendar events: {e}")
            return []

    def get_events_for_emails(self, emails):
        try:
            all_events = self.get_calendar_events(future_only=True, max_days=30)
            #print(f"DEBUG. CalendarIntegration.GetEventsForEmails. {len(all_events)=}")
            #print(f"DEBUG. CalendarIntegration.GetEventsForEmails. first event is {all_events[0]}")
            #with st.expander("all_events in CalendarIntegration.GetEventsForEmails."):
            #    st.dataframe(all_events)
            #    st.json(all_events)
            lower_emails = [email.lower() for email in emails if email]
            if not lower_emails:
                return {}
            email_events = {email: [] for email in emails if email}
            for event in all_events:
                attendees = event.get("attendees", [])
                if not attendees:
                    continue
                attendee_emails = [attendee.get("email", "").lower() for attendee in attendees]
                for i, email in enumerate(emails):
                    if email and lower_emails[i] in attendee_emails:
                        email_events[email].append(event)
            #with st.expander("email_events in CalendarIntegration.GetEventsForEmails."):
            #    st.dataframe(email_events)
            return email_events
        except Exception as e:
            print(f"Error fetching events for emails: {e}")
            return {}

