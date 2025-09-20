import streamlit as st
from utils.calendar_integration import get_calendar_service, get_calendar_events

if __name__ == "__main__":
    secrets = st.secrets
    with st.expander("Secrets"):
        st.json(secrets)
    calendar=get_calendar_service()
    events=get_calendar_events(calendar,True,3)
    with st.expander("Events"):
        st.json(events)