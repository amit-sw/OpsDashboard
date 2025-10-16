import os
from datetime import datetime, timezone

import streamlit as st
from google.auth.exceptions import RefreshError
from src.core_utils import normalize_query_value, transcript_segments_to_text
from src.youtube_private_utils import (
    clear_stored_credentials,
    get_authorization_url,
    get_authenticated_service,
    get_my_videos,
    get_user_credentials,
    get_transcript_segments,
    load_stored_credentials,
    refresh_credentials,
    save_credentials,
    TranscriptRetrievalError,
    credentials_have_required_scopes,
)
from src.youtube_private_repository import YouTubeVideoRepository
from utils.supabase_integration import SupabaseClient


from utils.utils_credentials import setup_env_from_dict

st.set_page_config(page_title="YouTube Private Video Downloader", page_icon=":movie_camera:")

st.title("YouTube Private Video Downloader")

st.write("This app downloads video transcripts from your private YouTube videos.")

if not os.path.exists("client_secret.json"):
    st.error("The `client_secret.json` file is missing. Please add it to the root directory of the application.")
    st.stop()


def load_supabase_client():
    supabase_config = st.secrets.get("env", {})
    url = os.environ.get("SUPABASE_URL") or supabase_config.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY") or supabase_config.get("SUPABASE_KEY")
    if not url or not key:
        st.warning("Supabase credentials are not configured. Transcripts will not be stored.")
        return None
    client = SupabaseClient(url=url, key=key)
    if client.supabase is None:
        st.error("Unable to connect to Supabase. Check your credentials.")
        return None
    return client


def build_video_record(video, segments, transcript_text):
    return {
        "video_id": video["video_id"],
        "title": video["title"],
        "published_at": video.get("published_at"),
        "video_url": f"https://www.youtube.com/watch?v={video['video_id']}",
        "transcript_segments": segments,
        "transcript_text": transcript_text,
        "transcript_downloaded_at": datetime.now(timezone.utc).isoformat(),
    }


env_secrets=st.secrets.get("env")  
#print(f"DEBUG: ENV Secrets: {env_secrets=}")  
if env_secrets:
    setup_env_from_dict(env_secrets)

if "credentials" not in st.session_state:
    st.session_state.credentials = None

if not st.session_state.credentials:
    stored_credentials = load_stored_credentials()
    if stored_credentials:
        if not credentials_have_required_scopes(stored_credentials):
            clear_stored_credentials()
            st.warning("Stored credentials are missing required YouTube permissions. Please sign in again.")
        else:
            try:
                refreshed = refresh_credentials(stored_credentials)
            except RefreshError:
                clear_stored_credentials()
                st.warning("Stored credentials are no longer valid. Please sign in again.")
            else:
                if refreshed:
                    st.session_state.credentials = refreshed
                else:
                    clear_stored_credentials()
                    st.info("Stored credentials have expired. Please sign in again.")

if hasattr(st, "query_params"):
    query_params = st.query_params
    raw_code = query_params.get("code")
else:
    query_params = st.experimental_get_query_params()
    raw_code = query_params.get("code")

auth_code = normalize_query_value(raw_code)

if auth_code and not st.session_state.credentials:
    try:
        credentials = get_user_credentials(auth_code)
        save_credentials(credentials)
        st.session_state.credentials = credentials
        try:
            if hasattr(query_params, "clear"):
                query_params.clear()
            else:
                st.experimental_set_query_params()
        except Exception:
            pass
        st.rerun()
    except Exception as e:
        st.error(f"Error getting credentials: {e}")

if st.session_state.credentials:
    st.write("You are logged in.")
    with st.sidebar.expander("YouTube session", expanded=False):
        if st.button("Sign out"):
            clear_stored_credentials()
            st.session_state.credentials = None
            st.rerun()
    number_of_videos = st.number_input("Enter the number of videos to download:", min_value=1, value=10)

    if st.button("Download Transcripts"):
        supabase_client = load_supabase_client()
        repository = YouTubeVideoRepository(supabase_client) if supabase_client else None
        latest_published = repository.latest_published_at() if repository else None
        new_records = []
        with st.spinner("Downloading transcripts..."):
            service = get_authenticated_service(st.session_state.credentials)
            videos = get_my_videos(
                st.session_state.credentials,
                number_of_videos,
                published_after=latest_published,
                service=service,
            )

            if not videos:
                st.warning("No videos found.")
            else:
                st.success(f"Found {len(videos)} videos.")
                if repository and latest_published:
                    st.caption(f"Only videos published after {latest_published} were requested.")
                existing_ids = (
                    repository.existing_ids_for(video["video_id"] for video in videos) if repository else set()
                )
                for video in videos:
                    st.write(f"**{video['title']}**")
                    try:
                        segments = get_transcript_segments(video["video_id"], service=service)
                        transcript_text = transcript_segments_to_text(segments)
                    except TranscriptRetrievalError as exc:
                        segments = []
                        transcript_text = ""
                        message = str(exc)
                        st.warning(f"Could not retrieve transcript for {video['title']}: {message}")
                        if "insufficient permission" in message.lower():
                            clear_stored_credentials()
                            st.info("Authorization was reset. Please sign in again to continue.")
                            st.session_state.credentials = None
                            st.rerun()
                    st.text_area(f"Transcript for {video['title']}", transcript_text or "No transcript available.", height=200)
                    if repository and video["video_id"] not in existing_ids and segments:
                        new_records.append(build_video_record(video, segments, transcript_text))
        if repository:
            if new_records:
                repository.insert_records(new_records)
                st.success(f"Stored {len(new_records)} new videos in Supabase.")
            else:
                st.info("No new videos to store in Supabase.")
else:
    auth_url = get_authorization_url()
    st.markdown(f'Please log in to your youtube account using this link: <a href="{auth_url}" target="_blank">link</a>', unsafe_allow_html=True)
