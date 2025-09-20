import streamlit as st
from utils.calendar_integration import CalendarClient

if __name__ == "__main__":
    secrets = st.secrets
    with st.expander("Secrets"):
        st.json(secrets)
    calendar = CalendarClient(st.secrets.get('calendar'))
    events = calendar.get_calendar_events(True, 3)
    with st.expander("Events"):
        st.json(events)
