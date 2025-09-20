import streamlit as st
import os

from datetime import datetime, timezone


from utils.supabase_integration import SupabaseClient
from utils.calendar_integration import CalendarClient

def find_closest_future_event(events):
    """Find the closest future event from a list of events.
    
    Args:
        events: List of calendar events
        
    Returns:
        The closest future event, or None if no future events
    """
    if not events:
        return None
        
    # Since we're already fetching only future events, we just need to sort by start time
    events_with_time = []
    
    for event in events:
        # Get event start time
        start_str = event.get('start', {}).get('dateTime')
        if not start_str:
            continue
            
        try:
            # Convert to timezone-aware datetime
            if 'Z' in start_str:
                # UTC time with Z suffix
                start_time = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
            elif '+' in start_str or '-' in start_str and 'T' in start_str:
                # Already has timezone info
                start_time = datetime.fromisoformat(start_str)
            else:
                # No timezone info, assume UTC
                start_time = datetime.fromisoformat(start_str).replace(tzinfo=timezone.utc)
                
            events_with_time.append((start_time, event))
        except ValueError:
            # Skip events with invalid datetime format
            continue
    
    # Sort by start time
    if events_with_time:
        events_with_time.sort(key=lambda x: x[0])  # Sort by datetime
        return events_with_time[0][1]  # Return the closest event
    
    return None

def parse_event_datetime(date_str):
    """Parse event datetime string to datetime object."""
    if not date_str:
        return None
        
    try:
        # Handle different datetime formats
        if 'Z' in date_str:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        elif '+' in date_str or '-' in date_str and 'T' in date_str:
            # Already has timezone info
            dt = datetime.fromisoformat(date_str)
        else:
            # No timezone info, assume UTC
            dt = datetime.fromisoformat(date_str).replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None
        
def calculate_days_until_event(event):
    """Calculate days until event.
    
    Returns:
        int: Number of days until event, or None if no valid event
    """
    if not event:
        return None
        
    start_str = event.get('start', {}).get('dateTime')
    if not start_str:
        return None
        
    start_dt = parse_event_datetime(start_str)
    if not start_dt:
        return None
        
    # Calculate days difference
    now = datetime.now(timezone.utc)
    delta = start_dt - now
    
    # Return days as integer
    return max(0, delta.days)

def format_event_datetime(event):
    """Format event date and time for display."""
    if not event:
        return "None"
        
    start_str = event.get('start', {}).get('dateTime')
    if not start_str:
        return "None"
        
    start_dt = parse_event_datetime(start_str)
    if not start_dt:
        return "None"
        
    return start_dt.strftime('%b %d, %Y - %I:%M %p')

def get_event_title(event):
    """Get event title."""
    if not event:
        return "None"
        
    return event.get('summary', 'Untitled Event')



def show_student_details(student_name, students, calendar):
    """Show detailed calendar events for a specific student"""
    st.title(f"Calendar Events for {student_name}")
    
    # Find the student record that matches the selected student name
    selected_student_data = None
    for student in students:
        if student.get("full_name") == student_name:
            selected_student_data = student
            break
    
    if not selected_student_data:
        st.error(f"Could not find student data for {student_name}")
        return
        
    # Extract student and parent emails
    student_emails = selected_student_data.get("student_emails", []) or []
    parent_emails = selected_student_data.get("parent_emails", []) or []
    #student_specific_emails = student_emails + parent_emails
    student_specific_emails = student_emails
    
    st.write(f"Showing calendar events for the next 30 days for {student_name}.")
    
    if not calendar:
        st.warning("Could not connect to Google Calendar. Event information will not be available.")
        return
        
    # Get events for this student
    with st.spinner("Fetching calendar events..."):
        student_events = calendar.get_events_for_emails(student_specific_emails)
        
        # Flatten events list and remove duplicates
        all_student_events = []
        seen_event_ids = set()
        
        for email in student_specific_emails:
            if email in student_events:
                for event in student_events.get(email, []):
                    # Only add events we haven't seen yet (avoid duplicates)
                    event_id = event.get('id')
                    if event_id and event_id not in seen_event_ids:
                        all_student_events.append(event)
                        seen_event_ids.add(event_id)
        
        # Process events to include days until and ensure student is an attendee
        processed_events = []
        for event in all_student_events:
            # Get all attendee emails for this event
            student_is_attendee = False
            if "attendees" in event:
                attendee_emails = [attendee.get("email", "").lower() for attendee in event["attendees"]]
                
                # Check if any of this student's emails are in the attendees
                for email in student_specific_emails:
                    if email.lower() in attendee_emails:
                        student_is_attendee = True
                        break
            
            # Only include events where this student is an attendee
            if student_is_attendee:
                processed_events.append({
                    "days_until": calculate_days_until_event(event),
                    "date_time": format_event_datetime(event),
                    "event_name": get_event_title(event),
                    "calendar_email": event.get('organizer', {}).get('email', 'Unknown')
                })
        
        if not processed_events:
            st.info(f"No calendar events found for {student_name} in the next 30 days.")
            return
            
        # Display events in a table with sorting and filtering options
        st.subheader(f"Upcoming Events ({len(processed_events)})")
        
        # Add filtering
        col1, col2 = st.columns([3, 1])
        
        # Add a search box
        event_search = col1.text_input("Search events", key="event_search", placeholder="Search events...")
        event_search = event_search.lower() if event_search else ""
        
        # Add sorting options
        sort_options = ["Days Until (Ascending)", "Days Until (Descending)", 
                       "Date (Ascending)", "Date (Descending)", 
                       "Event Name (A-Z)", "Event Name (Z-A)"]
        sort_by = col2.selectbox("Sort by", sort_options, key="event_sort")
        
        # Sort events based on selected option
        if sort_by == "Days Until (Ascending)":
            processed_events.sort(key=lambda x: (x["days_until"] if x["days_until"] is not None else float('inf')))
        elif sort_by == "Days Until (Descending)":
            processed_events.sort(key=lambda x: (x["days_until"] if x["days_until"] is not None else -1), reverse=True)
        elif sort_by == "Date (Ascending)":
            processed_events.sort(key=lambda x: x["date_time"] if x["date_time"] else "")
        elif sort_by == "Date (Descending)":
            processed_events.sort(key=lambda x: x["date_time"] if x["date_time"] else "", reverse=True)
        elif sort_by == "Event Name (A-Z)":
            processed_events.sort(key=lambda x: x["event_name"].lower() if x["event_name"] else "")
        elif sort_by == "Event Name (Z-A)":
            processed_events.sort(key=lambda x: x["event_name"].lower() if x["event_name"] else "", reverse=True)
        
        # Filter events based on search text
        if event_search:
            filtered_events = [e for e in processed_events 
                            if (e["days_until"] is not None and str(e["days_until"]).startswith(event_search)) or
                               (e["date_time"] and event_search in e["date_time"].lower()) or
                               (e["event_name"] and event_search in e["event_name"].lower()) or
                               (e["calendar_email"] and event_search in e["calendar_email"].lower())]
        else:
            filtered_events = processed_events
        
        # Show number of filtered events if filtering is applied
        if event_search and len(filtered_events) < len(processed_events):
            st.caption(f"Showing {len(filtered_events)} of {len(processed_events)} events")
        
        # Create columns for the header
        col1, col2, col3, col4 = st.columns([1, 2, 3, 2])
        col1.markdown("**Days Until**")
        col2.markdown("**Date and Time**")
        col3.markdown("**Event Name**")
        col4.markdown("**Calendar Email**")
        
        # Add a divider for visual separation
        st.markdown("<hr style='margin: 5px 0; padding: 0'>", unsafe_allow_html=True)
        
        # Create a container for the scrollable list
        with st.container():
            if filtered_events:
                for event in filtered_events:
                    cols = st.columns([1, 2, 3, 2])
                    cols[0].write(event["days_until"] if event["days_until"] is not None else "None")
                    cols[1].write(event["date_time"])
                    cols[2].write(event["event_name"])
                    cols[3].write(event["calendar_email"])
                    st.markdown("<hr style='margin: 3px 0; padding: 0'>", unsafe_allow_html=True)
            else:
                st.info("No events match your search criteria.")

def show_students_page():
    """Display the Students page content"""
    # Initialize session state variables if they don't exist
    if 'selected_student' not in st.session_state:
        st.session_state.selected_student = None
    
    # Get student name from URL parameters if present
    if "student" in st.query_params and st.query_params["student"]:
        st.session_state.selected_student = st.query_params["student"]
    
    # Get Supabase client
    supabase = SupabaseClient(url=os.environ["SUPABASE_URL"], key=os.environ['SUPABASE_KEY'])

    
    if not supabase:
        st.error("Could not connect to the database.")
        return
    
    # Create Google Calendar service
    with st.spinner("Connecting to Google Calendar..."):
        calendar = CalendarClient(st.secrets.get('calendar'))
    
    if not calendar:
        st.warning("Could not connect to Google Calendar. Event information will not be available.")
    
    # Fetch student data from database
    with st.spinner("Fetching students from database..."):
        students = supabase.get_students_from_db()
    
    if not students:
        st.info("No students found in the database.")
        return
    
    # If a student is selected, show their details instead of the list
    if st.session_state.selected_student:
        # Add a back button at the top
        if st.button("← Back to Students List"):
            st.session_state.selected_student = None
            # Keep the tab parameter when clearing others
            current_tab = st.session_state.get('active_tab', 'Students')
            st.query_params.clear()
            st.query_params["tab"] = current_tab
            st.rerun()
            return
            
        show_student_details(st.session_state.selected_student, students, calendar)
    else:
        st.title("Students")
        
        # Add refresh button
        if st.button("Refresh Student List"):
            st.session_state.students_refreshed = True
    
    # Process student data to include closest events
    processed_students = []
    
    # Get all unique emails across all students first
    all_student_emails = set()
    for student in students:
        student_emails = student.get("student_emails", []) or []
        parent_emails = student.get("parent_emails", []) or []
        #ll_student_emails.update(student_emails + parent_emails)
        all_student_emails.update(student_emails)
        
    #with st.expander("All student emails"):
    #    st.dataframe(list(all_student_emails))
    
    # Get events for all emails in a single API call
    all_email_events = {}
    with st.spinner("Finding upcoming events for all students..."):
        if calendar and all_student_emails:
            # This now only fetches future events for next month
            all_email_events = calendar.get_events_for_emails(list(all_student_emails))
    
    # Process each student
    with st.spinner("Processing student data..."):
        for student in students:
            # Extract student and parent emails
            student_emails = student.get("student_emails", []) or []
            parent_emails = student.get("parent_emails", []) or []
            #student_specific_emails = student_emails + parent_emails
            student_specific_emails = student_emails
            
            # Get events for this student
            all_student_events = []
            for email in student_specific_emails:
                if email in all_email_events:
                    all_student_events.extend(all_email_events.get(email, []))
            
            # Find closest future event
            closest_event = find_closest_future_event(all_student_events)
            
            # Add data to processed students with the requested columns
            processed_students.append({
                "full_name": student.get("full_name", "Unknown"),
                "next_class": calculate_days_until_event(closest_event),
                "date_time": format_event_datetime(closest_event),
                "event_name": get_event_title(closest_event)
            })
    
    # Sort students by next_class, with None values at the end
    processed_students.sort(key=lambda x: (x["next_class"] is None, x["next_class"] if x["next_class"] is not None else float('inf')))
    
    # Display the students in a standard Streamlit table with clickable links
    st.subheader(f"Student List ({len(processed_students)} students)")
    
    # Add a search box
    search_text = st.text_input("Search", key="student_search", placeholder="Search students...")
    search_text = search_text.lower() if search_text else ""
    
    # Filter students based on search text
    if search_text:
        filtered_students = [s for s in processed_students 
                          if search_text in s["full_name"].lower() or 
                             (s["next_class"] and str(s["next_class"]).lower().startswith(search_text)) or
                             (s["date_time"] and search_text in s["date_time"].lower()) or
                             (s["event_name"] and search_text in s["event_name"].lower())]
    else:
        filtered_students = processed_students
    
    # Create columns for the header
    col1, col2, col3, col4 = st.columns([3, 1, 2, 3])
    col1.markdown("**Student Name**")
    col2.markdown("**Next Class (Days)**")
    col3.markdown("**Date and Time**")
    col4.markdown("**Event Name**")
    
    # Add a divider for visual separation
    st.markdown("<hr style='margin: 5px 0; padding: 0'>", unsafe_allow_html=True)
    
    # Create a container for the scrollable list
    with st.container():
        for student in filtered_students:
            cols = st.columns([3, 1, 2, 3])
            
            # Make the student name a clickable link
            student_name = student["full_name"]
            # When clicked, this will set the URL parameter and trigger a page refresh
            # We add tab=Students to ensure we stay on the Students tab
            cols[0].markdown(f"<a href='?student={student_name}&tab=Students' target='_self'>{student_name}</a>", unsafe_allow_html=True)
            
            # Display other columns
            cols[1].write(student["next_class"] if student["next_class"] is not None else "None")
            cols[2].write(student["date_time"])
            cols[3].write(student["event_name"])
            
            # Add subtle divider between rows
            st.markdown("<hr style='margin: 3px 0; padding: 0'>", unsafe_allow_html=True)