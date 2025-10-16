import streamlit as st
from src.youtube_private_utils import get_authorization_url, get_user_credentials, get_my_videos, get_transcript
import os

st.set_page_config(page_title="YouTube Private Video Downloader", page_icon=":movie_camera:")

st.title("YouTube Private Video Downloader")

st.write("This app downloads video transcripts from your private YouTube videos.")

if not os.path.exists("client_secret.json"):
    st.error("The `client_secret.json` file is missing. Please add it to the root directory of the application.")
    st.stop()

if "credentials" not in st.session_state:
    st.session_state.credentials = None

query_params = st.query_params
if "code" in query_params and not st.session_state.credentials:
    try:
        st.session_state.credentials = get_user_credentials(query_params["code"])
        st.rerun()
    except Exception as e:
        st.error(f"Error getting credentials: {e}")

if st.session_state.credentials:
    st.write("You are logged in.")

    number_of_videos = st.number_input("Enter the number of videos to download:", min_value=1, value=10)

    if st.button("Download Transcripts"):
        with st.spinner("Downloading transcripts..."):
            videos = get_my_videos(st.session_state.credentials, number_of_videos)

            if videos:
                st.success(f"Found {len(videos)} videos.")
                for video in videos:
                    st.write(f"**{video['title']}**")
                    transcript = get_transcript(video['video_id'])
                    st.text_area("Transcript", transcript, height=200)
            else:
                st.warning("No videos found.")
else:
    auth_url = get_authorization_url()
    st.markdown(f'Please log in to your youtube account using this link: <a href="{auth_url}" target="_blank">link</a>', unsafe_allow_html=True)