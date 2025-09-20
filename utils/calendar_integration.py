import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timezone, timedelta

#
# Code originally LLM-generated. Needs more clean-up
#

def get_calendar_service():
    """Creates and returns a Google Calendar service object."""
    try:
        creds_json = st.secrets.get('calendar')
        creds = service_account.Credentials.from_service_account_info(creds_json)
        service = build('calendar', 'v3', credentials=creds)
        return service
    except Exception as e:
        st.error(f"Error creating Google Calendar service: {e}")
        print(f"Error creating Google Calendar service: {e}")
        return None

def get_calendar_events(service, future_only=True, max_days=30):
    """Fetches events from the primary calendar.
    
    Args:
        service: Google Calendar service object
        future_only: If True, only fetch future events
        max_days: Number of days in the future to fetch events for
        
    Returns:
        List of calendar events
    """
    if not service:
        print(f"ERROR: No valid Google Calendar service provided.")
        return []
    
    try:
        # Get current time
        now = datetime.now(timezone.utc)
        
        # Time range for fetching events
        if future_only:
            # Only fetch events from now to max_days in the future
            time_min = now.isoformat().replace("+00:00", "Z")
            time_max = (now + timedelta(days=max_days)).isoformat().replace("+00:00", "Z")
        else:
            # Fetch events from max_days in the past to max_days in the future
            time_min = (now - timedelta(days=max_days)).isoformat().replace("+00:00", "Z")
            time_max = (now + timedelta(days=max_days)).isoformat().replace("+00:00", "Z")
        
        # Call Google Calendar API
        events_result = service.events().list(
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
        st.error(f"Error fetching calendar events: {e}")
        print(f"Error fetching calendar events: {e}")
        return []

def get_events_for_emails(service, emails):
    """Fetches calendar events where any of the given emails are attendees.
    
    Args:
        service: Google Calendar service object
        emails: List of email addresses to search for in events
        
    Returns:
        Dictionary mapping email addresses to their associated events
    """
    if not service or not emails:
        return {}
        
    try:
        # Only fetch future events for the next month
        all_events = get_calendar_events(service, future_only=True, max_days=30)
        
        # Pre-process emails to lowercase for case-insensitive matching
        lower_emails = [email.lower() for email in emails if email]
        
        if not lower_emails:
            return {}
            
        # Create dictionary to map emails to events
        email_events = {email: [] for email in emails if email}
        
        # Process all events once
        for event in all_events:
            if "attendees" not in event:
                continue
                
            # Extract attendee emails for this event
            attendee_emails = [attendee.get("email", "").lower() for attendee in event["attendees"]]
            
            # For each requested email, check if it's an attendee
            for i, email in enumerate(emails):
                if email and lower_emails[i] in attendee_emails:
                    email_events[email].append(event)
        
        return email_events
        
    except Exception as e:
        st.error(f"Error fetching events for emails: {e}")
        print(f"Error fetching events for emails: {e}")
        return {}
    
if __name__ == "__main__":
    secrets = st.secrets
    st.json(secrets)