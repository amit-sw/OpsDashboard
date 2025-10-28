import streamlit as st
import os

from youtube_transcript_api import YouTubeTranscriptApi
import math

from utils.supabase_integration import SupabaseClient

def get_video_id_url_from_input(user_input):
    if "youtube.com/watch?v=" in user_input:
        return user_input.split("v=")[1].split("&")[0], user_input
    elif "youtu.be/" in user_input:
        return user_input.split("youtu.be/")[1].split("?")[0],user_input
    else:
        video_url=f"https://www.youtube.com/watch?v={user_input}"
        return user_input, video_url
    
def get_transcript(transcript_list):
    segments=[]
    for tr in transcript_list:
        txt=tr.text
        ts=math.trunc(tr.start)
        segments.append(f"{ts}:{txt}")
    resp = "\n".join(segments)
    return resp


def show_yt_ui(user):
    st.write(f"Welcome, {user.name}!")
    st.write("This is the YouTube private download UI.")
    inp1=st.text_input("Youtube URL or VideoId:")
    if inp1 and st.button("Fetch Transcript"):
        yt_video_id,video_url=get_video_id_url_from_input(inp1)
        res = YouTubeTranscriptApi().fetch(yt_video_id)
        transcript = get_transcript(res)
        supabase = SupabaseClient(url=os.environ["SUPABASE_URL"], key=os.environ['SUPABASE_KEY'])
        new_record={
            'yt_video_id':yt_video_id,
            'video_url':video_url,
            'video_transcript':transcript,
        }
        supabase.insert_yt_video_records(new_record)
        
        st.session_state['transcript']=get_transcript(res)
        st.balloons()
    
def show_discuss_ui(user):
    st.write(f"Welcome to the Discuss tab, {user.name}!")
    st.write("This is where you can discuss the transcripts.")
    if 'transcript' in st.session_state:
        st.text_area("Transcript:", value=st.session_state['transcript'], height=300)
    else:
        st.write("No transcript available. Please go to the Video tab and fetch a transcript first.")
    #
    # Sequence
    #
    # User choose a video from their list
    # Fetch transcript from Supabase
    # Fetch the list of tasks
    # User chooses tasks to discuss
    # Fetch prompts for the task
    # User has option to create a new prompt (LLM assisted)
    # Now, ask the user to choose set of prompts to run.
    # For each prompt, create a new Tab.
    # In each tab, the user provides feedback on each of the prompts.
    # All information is stored back to Supabase.
    #

