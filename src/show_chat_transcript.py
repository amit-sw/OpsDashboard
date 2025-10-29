import streamlit as st

from langchain_core.messages import SystemMessage, BaseMessage, HumanMessage, AIMessage
from langsmith import Client
from langchain_core.callbacks import BaseCallbackHandler

from langchain_openai import ChatOpenAI

import base64
import os

import random
DEBUGGING=1

class LangsmithRunRecorder(BaseCallbackHandler):
    def __init__(self):
        self.root_run_id = None

    def on_chain_start(self, serialized, inputs, *, run_id, parent_run_id, **kwargs):
        if parent_run_id is None and self.root_run_id is None:
            self.root_run_id = str(run_id)

    def on_llm_start(self, serialized, prompts, *, run_id, parent_run_id, **kwargs):
        if parent_run_id is None and self.root_run_id is None:
            self.root_run_id = str(run_id)

def record_langsmith_feedback(feedback_id: int, feedback_value: str) -> None:
    run_id = st.session_state.get("last_langsmith_run_id")
    if not run_id:
        print("No LangSmith run id available for feedback; skipping logging.")
        return

    try:
        client = Client()
    except Exception as exc:
        print(f"Unable to initialize LangSmith client: {exc}")
        return
    
    source_info = {"source": "streamlit_feedback"}
    thread_id = st.session_state.get("thread_id")
    if thread_id:
        source_info["thread_id"] = thread_id

    try:
        client.create_feedback(
            run_id=run_id,
            key="user_feedback",
            score=feedback_id,
            value=feedback_value,
            source_info=source_info,
        )
        print(f"XXX: created feedback: {run_id=}, {feedback_id=}, {feedback_value=}")
    except Exception as exc:
        print(f"Failed to log LangSmith feedback: {exc}")
        
def record_langsmith_comment(comment: str) -> None:
    run_id = st.session_state.get("last_langsmith_run_id")
    if not run_id:
        print("No LangSmith run id available for feedback; skipping logging.")
        return

    try:
        client = Client()
    except Exception as exc:
        print(f"Unable to initialize LangSmith client: {exc}")
        return
    
    source_info = {"source": "streamlit_comment"}
    thread_id = st.session_state.get("thread_id")
    if thread_id:
        source_info["thread_id"] = thread_id

    try:
        client.create_feedback(
            run_id=run_id,
            key="user_feedback_comment",
            value=comment,
            source_info=source_info,
        )
        print(f"YYY: created feedback comment: {run_id=}, {comment=}")
    except Exception as exc:
        print(f"Failed to log LangSmith feedback: {exc}")

@st.dialog("Feedback Dialog")
def ask_followup_question():
    st.write(f"Can you please provide more details?")
    reason = st.text_input("Because...")
    if st.button("Submit"):
        st.session_state.vote = {"reason": reason}
        record_langsmith_comment(reason)
        st.rerun()    
    
def record_feedback():
    print(f"In record_feedback")
    print(f"DEBUG Record Feedback\n\n{st.session_state.get('feedback_id')}")
    feedback_id = st.session_state.get('feedback_id')
    feedback_value = "positive" if feedback_id > 0 else "negative"
    ask_followup_question()
    if feedback_id>0:
        st.balloons()
    else:
        st.snow()
    record_langsmith_feedback(feedback_id, feedback_value)
        
def accept_feedback():
    sentiment_mapping = [":material/thumb_down:", ":material/thumb_up:"]
    selected = st.feedback("thumbs", on_change=record_feedback, key="feedback_id")
    if selected is not None:
        st.markdown(f"You selected: {sentiment_mapping[selected]}")
        record_langsmith_feedback(sentiment_mapping[selected])
        
def config_for_langgraph():
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = random.randint(1000, 100000000)
    thread_id = st.session_state.thread_id
    
    metadata = {
        "url": st.context.url,
    }

    if st.session_state.get("user_record"):
        user_record = st.session_state.user_record

        if user_record.get("login"):
            metadata["login"] = user_record.get("login")

        if user_record.get("full_name"):
            metadata["full_name"] = user_record.get("full_name")

        if user_record.get("account_name"):
            metadata["account_name"] = user_record.get("account_name")
    
    run_recorder = LangsmithRunRecorder()
    config = {
        "configurable":{"thread_id":thread_id},
        "metadata": metadata,
        "callbacks": [run_recorder],
    }
    return thread_id, config, run_recorder

def process_file_upload(uploaded_file):
    mime = uploaded_file.type or "image/png"
    b64 = base64.b64encode(uploaded_file.getvalue()).decode("utf-8")
    data_url = f"data:{mime};base64,{b64}"

    response = {
        'type': 'image_url',
        'image_url': {'url':data_url}
    }
    return response

def create_llm_msg(system_prompt,transcript,history):
    resp=[SystemMessage(content=system_prompt), HumanMessage(content=transcript)]
    msgs = history
    for m in msgs:
        resp.append(m)
    return resp

def simple_graph(model,system_prompt,transcript,history):
    llm = ChatOpenAI(model_name=model)
    response=llm.invoke(create_llm_msg(system_prompt,transcript,history))
    return response.content

def start_chat(transcript="",existing_qna=None):
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Audiowide&display=swap');
        .header-container {
            display: flex;
            align-items: center;
            gap: 10px;
        }
    </style>
    """, unsafe_allow_html=True)

    #st.subheader("Your AI assistant")
    #st.markdown("Get instant answers to your questions with AI-powered assistance.")
    st.markdown("<br>", unsafe_allow_html=True)

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "thread_id" not in st.session_state:
        st.session_state.thread_id = random.randint(1000, 100000000)
    thread_id = st.session_state.thread_id


    user_record = st.session_state.get('user_record')

    if user_record:
        user_id = user_record.get('id', 0)
        #st.write(f"{user_id=}")
        conv_history = None

        if conv_history:
            for idx, conv in enumerate(conv_history):
                conv_id = conv.get('thread_id')
                short_title = conv.get('short_title')
                conv_name = short_title or f"{conv.get('thread_id')}"
                conv_key = conv_name + f"{idx}"

                if st.sidebar.button(conv_name, type="tertiary", key=conv_key):
                    #st.error("to do")
                    r = conv['conv']
                    #restore_conv_history_to_ui(conv_id, r)
    
    for qna in existing_qna or []:
        #print(f"Addding to chat history: {qna['question_text']}, {qna['response_content']}")
        with st.chat_message("user"):
            st.write(qna['question_text'])
        with st.chat_message("assistant"):
            st.write(qna['response_content'])
        #message_history.append(HumanMessage(content=qna['question_text']))
        #message_history.append(AIMessage(content=qna['response_content'])) 

    for message in st.session_state.messages:
        if message["role"] != "system":
            with st.chat_message(message["role"]):
                display_text = message["content"].replace("$", "\\$")
                display_text = display_text.replace("\\\\$", "\\$")
                st.markdown(display_text)
                #st.markdown(message["content"].replace("$", "\\$")) 
    
    if prompt := st.chat_input("Ask me anything .", accept_file=True, file_type=["gif","jpg","png"]):
        
        user_prompt = prompt.text
        st.session_state.messages.append({"role": "user", "content": user_prompt})
        
        with st.chat_message("user"):
            st.write(user_prompt.replace("$", "\\$"))

        message_history = []
        

        
        msgs = st.session_state.messages
    
        # Iterate through chat history, and based on the role (user or assistant) tag it as HumanMessage or AIMessage
        for m in msgs:
            if m["role"] == "user":
                message_history.append(HumanMessage(content=m["content"]))
            elif m["role"] == "assistant":
                message_history.append(AIMessage(content=m["content"]))
        
        if prompt and prompt["files"]:
            uploaded_file=prompt["files"][0]
            basic_message_list=[]
            if user_prompt:
                basic_message_list.append({"type": "text", "text": user_prompt})
            img_object= process_file_upload(uploaded_file)
            basic_message_list.append(img_object)
            message_history.append(HumanMessage(content=basic_message_list))
            st.image(uploaded_file)
        elif user_prompt:
            message_history.append(HumanMessage(content=user_prompt))
            
        st.session_state.messages.append({"role": "user", "content": user_prompt})
        
        thread_id, config, run_recorder = config_for_langgraph()
        
        parameters = {'messages': message_history}
        model = os.environ.get("OPENAI_MODEL", "gpt-5-mini")
        system_prompt="You are a helpful AI assistant. Answer the questions as best as you can based only on the transcript provided."

        with st.spinner("Thinking ...", show_time=True):
            full_response = ""
            response = simple_graph(model,system_prompt,transcript,message_history)

            if run_recorder.root_run_id and st.session_state.get("last_langsmith_run_id") != run_recorder.root_run_id:
                st.session_state["last_langsmith_run_id"] = run_recorder.root_run_id

            with st.chat_message("assistant"):
                # Clean up response: remove weird line breaks
                #cleaned_resp = response.replace('\n', ' ').replace('  ', ' ')
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
                accept_feedback()
                #save_conv_history_to_db(thread_id)
                


if __name__ == '__main__':
    st.set_page_config(page_title="Your AI assistant")
    start_chat()