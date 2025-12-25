import streamlit as st
import os
import time
import json

import time

import pandas as pd

from utils.supabase_integration import SupabaseClient
from utils.utils_transcript_chat import llm_request_response
from src.show_chat_transcript import start_chat

from utils.prompts import question_prompts

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage


def create_zoom_session_table(supabase_client: SupabaseClient):
    try:
        response = supabase_client.supabase.table("zoom_sessions").select("topic,date,session_id").order("date", desc=True).order("topic").execute()
        return response.data or []
    except Exception as e:
        st.error(f"An error occurred while fetching zoom sessions: {e}")
        return None

def show_zoom_session_page():
    st.title("Zoom Sessions Page")
    supabase_client=SupabaseClient(os.getenv('SUPABASE_URL'),os.getenv('SUPABASE_KEY'))

    start = time.perf_counter()
    with st.spinner("Fetching results from Supabase…", show_time=True):
        session_table=create_zoom_session_table(supabase_client)
    elapsed = time.perf_counter() - start
    duration = f"{elapsed*1000:.0f} ms" if elapsed < 1 else f"{elapsed:.2f} s"
    st.sidebar.write(f"Data fetch took {duration}")
    df = pd.DataFrame(session_table)
    df["URL"]="/show_zoom_detail_page?q="+df['session_id']
    st.dataframe(df, column_config={"URL": st.column_config.LinkColumn("URL", display_text="Session details")}, hide_index=True)

#
# Details of one session
# 

def get_answers_one_transcript(transcript: str):
    
    start = time.perf_counter()
    with st.spinner("Fetching information from LLM…", show_time=True):
        prompt="""
        Analyze the following Zoom transcript and provide a summary of key topics discussed, any action items, and suggested next steps:\n\n
        Please provide information as per the following sections:
        1. Topics Discussed: Summarize the main topics covered during the session in a 3-5 bullet list - one line each.
        2. Action Items: List any action items or tasks that were assigned during the session in a 3-5 bullet list - one line each.
        3. Suggested Next Steps: Provide recommendations for follow-up actions or next steps based on the discussion.
        4. Unclear items: Highlight any points that were unclear for the participants in a bullet list - one line each.
        5. Questions: Prepare a bullet list of five to ten questions that can be asked to the participants to check their understanding of the session. 
           These questions should be about the new content discussed in this session, and not what was covered in the recap.
        """
        llm=ChatOpenAI(model="gpt-5-mini",api_key=os.getenv('OPENAI_API_KEY'))

        response=llm.invoke([SystemMessage(prompt),HumanMessage(transcript)])
        user_result = response.content
    elapsed = time.perf_counter() - start
    duration = f"{elapsed*1000:.0f} ms" if elapsed < 1 else f"{elapsed:.2f} s"
    print(f"DEBUG goat: LLM call took {duration}")
    return user_result, duration
    
@st.dialog("Session Summary")
def handle_session_summary(session_summary):   
    parsed_data = None
    for i in range(6):  # up to 6 attempts
        print(f"Decoding layer {i}: {session_summary[:80]}...")
        if not isinstance(session_summary, str):
            parsed_data = session_summary
            break

        # Clean up and unescape possible multiple backslashes or quotes
        cleaned = session_summary.strip()
        if cleaned.startswith(("b'", 'b"')) and cleaned.endswith(("'", '"')):
            cleaned = cleaned[2:-1]

        # Try unescaping and removing extra backslashes
        try:
            cleaned = cleaned.encode("utf-8").decode("unicode_escape")
        except Exception:
            pass

        try:
            decoded = json.loads(cleaned)
            print("✅ Decoded JSON successfully.")
        except json.JSONDecodeError as e:
            print(f"❌ Failed at layer {i}: {e}")
            # If it looks wrapped in quotes, strip and retry
            if cleaned.startswith('"') and cleaned.endswith('"'):
                session_summary = cleaned[1:-1]
                continue
            raise e

        # If decoded result is still a string that looks like JSON, keep unwrapping
        if isinstance(decoded, str) and decoded.strip().startswith(("{", "[")):
            print("🔁 Nested JSON string detected, unwrapping...")
            session_summary = decoded
            continue

        # If it’s a list with one JSON string inside, unwrap it
        if isinstance(decoded, list) and len(decoded) == 1 and isinstance(decoded[0], str):
            print("📦 List with JSON string detected, unwrapping...")
            session_summary = decoded[0]
            continue

        parsed_data = decoded
        break
    else:
        raise ValueError("Too many decoding layers — malformed data")

    # ---- Display parsed data ----
    st.write("### Session Summary")
    for topics in parsed_data.get("topics", []):
        if isinstance(topics, list):
            st.subheader(topics[0])
            for line in topics[1:]:
                st.write(line)
        elif isinstance(topics, dict):
            st.subheader(topics.get("title", "N/A"))
            st.write(topics.get("summary", ""))

    st.write("### Review")
    for item in parsed_data.get("review", []):
        st.write(item)

    st.write("### Directions")
    for direction in parsed_data.get("directions", []):
        if isinstance(direction, list):
            st.subheader(direction[0])
            for line in direction[1:]:
                st.write(line)
        elif isinstance(direction, dict):
            st.subheader(direction.get("title", "N/A"))
            st.write(direction.get("summary", ""))

@st.dialog("Raw Transcript", width="large")
def show_raw_transcript(transcript: str):
    st.code(transcript, language="text")
    
@st.dialog("Generate Answers : Single Query")
def generate_answers_single_query(transcript: str):
    rsp,duration=get_answers_one_transcript(transcript)
    st.write("### LLM Generated Summary")
    st.write(rsp)
    print(f"DEBUG ga: LLM call took {duration}")
    st.session_state['duration'] = duration
    
def refresh_qna_session(supabase_client, session_id):
    try:
        response = supabase_client.get_session_qna(session_id)
        if response:
            st.session_state['qna_response'] = response
        #print(f"DEBUG: Got QnA session for {session_id}, response: {response}")
    except Exception as e:
        st.error(f"An error occurred while refreshing QnA session: {e}")
    
@st.dialog("Generate Answers: Multi-Query", width="large")
def generate_answers(supabase_client, session_id, transcript: str):
    model = os.getenv('LLM_MODEL', 'gpt-5-mini')
    refresh_qna_session(supabase_client, session_id)
    if st.session_state.get('qna_response'):
        st.info("QnA session already exists. Skipping generation.")
        return
    
    with st.spinner("Generating answers ...", show_time=True):
        for prompt in question_prompts:
            topic = prompt["title"]
            request = prompt["prompt"]
            st.write(f"#### Topic: {topic}")
            rsp=llm_request_response(supabase_client,model,session_id,transcript,topic,request)
            st.write(rsp)
        refresh_qna_session(supabase_client, session_id)
        
@st.dialog("Youtube Video", width="large")
def show_youtube_video(youtube_link):
    try:
        print(f"DEBUG: Displaying YouTube video: {youtube_link}, with type {type(youtube_link)}")
        clean_yt = youtube_link.replace('\\"', '"')
        json_link = json.loads(clean_yt)
        print(f"DEBUG: Displaying JT JSON video: {json_link}, with type {type(json_link)}")
        st.video(json_link[0])
    except Exception as e:
        st.error(f"An error occurred while displaying the YouTube video: {e}")
        print(f"An error occurred while displaying the YouTube video: {e}")
    
    #a=llm_request_response(supabase_client,model,session_id,transcript,topic,request)
    #rsp,duration=get_answers_one_transcript(transcript)
    #st.write("### LLM Generated Summary")
    #st.write(rsp)
    #print(f"DEBUG ga: LLM call took {duration}")
    #st.session_state['duration'] = duration

def show_session_information(supabase_client,session_data):
    #with st.sidebar.expander("Session Information"):
    #    st.json(session_data)
    title=session_data.get("topic", "N/A")
    date_str=session_data.get("date", "N/A")
    session_id=session_data.get("session_id", "N/A")
    st.subheader(f"Zoom Session Chat: {title} on {date_str}")
    transcript = session_data.get("transcript", "N/A")
    refresh_qna_session(supabase_client, session_id)
    
    yt_url = session_data.get("youtube_link", "N/A")
    #with st.sidebar.expander("Youtube link"): 
    #    st.write(f"{yt_url}")
    if st.sidebar.button("Play Video"):
        show_youtube_video(yt_url)
    if st.sidebar.button("Zoom Transcript"):
        transcript = session_data.get("transcript", "N/A")
        show_raw_transcript(transcript)
    
    if st.sidebar.button("Pre-generated Summary"):
        session_summary = session_data.get("session_summary", "N/A")
        handle_session_summary(session_summary.strip())         
    if st.sidebar.button("Generate answers"):
        generate_answers(supabase_client,session_id,transcript)
        #duration = st.session_state.get('duration', 'N/A')
        #print(f"DEBUG SSI: LLM call took {duration}")
        #st.sidebar.write(f"LLM call took {duration}")
    start_chat(transcript,st.session_state.get('qna_response'))
    
def show_zoom_detail_page():
    session_id = st.query_params.get("q")
    #st.title(f"Zoom Session Details: {session_id}")
    supabase_client=SupabaseClient(os.getenv('SUPABASE_URL'),os.getenv('SUPABASE_KEY'))

    try:
        response = supabase_client.supabase.table("zoom_sessions").select("*").eq("session_id", session_id).execute()
        session_data = response.data[0] if response.data else None
        if session_data:
            show_session_information(supabase_client,session_data)
        else:
            st.error("Session not found.")
    except Exception as e:
        st.error(f"An error occurred while fetching session details: {e}")
    #st.write(f"Session Data for session_id: {session_id} is \n {session_data}")
