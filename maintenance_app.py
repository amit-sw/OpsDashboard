import streamlit as st
import os

import tiktoken

from utils.supabase_integration import SupabaseClient
from utils.utils_credentials import setup_env_from_dict


env_secrets=st.secrets.get("env")  
#print(f"DEBUG: ENV Secrets: {env_secrets=}")  
if env_secrets:
    setup_env_from_dict(env_secrets)

def main():
    st.title("Ops Dashboard Maintenance App")
    repeats=st.number_input("Number of repeats", min_value=1, max_value=10000, value=1)
    st.write(f"Repeats: {repeats}")
    if st.button("Run Maintenance Task"):
        supabase = SupabaseClient(url=os.environ["SUPABASE_URL"], key=os.environ['SUPABASE_KEY'])
        for i in range(repeats):
            # Example maintenance task: Fetch and display number of sessions
            sessions = supabase.get_zoom_session_negative_tokenlength(0)
            #st.write(f"Run {i+1}: Found {len(sessions)} sessions with negative token length.")
            transcript=sessions[0].get('transcript')
            #with st.expander("Transcript"):
            #    st.write(transcript)
            encoding = tiktoken.get_encoding("cl100k_base")  # pick the right model family
            token_count = len(encoding.encode(transcript))
            id=sessions[0].get('id')
            st.write(f"Run {i+1}: UPDATING: {id=}, {token_count=}")
            supabase.update_zoom_session_tokenlength(id, token_count)
        st.success("Maintenance task completed.")


if __name__ == "__main__":
    main()
