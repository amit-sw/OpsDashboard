import os

from utils.prompts import system_prompt, DEFAULT_PROMPT_GROUP

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, BaseMessage, HumanMessage, AIMessage

from utils.supabase_integration import SupabaseClient

def create_llm_msg(system_prompt,transcript,history):
    resp=[SystemMessage(content=system_prompt), HumanMessage(content=transcript)]
    msgs = history
    for m in msgs:
        resp.append(m)
    return resp

def llm_request_response(
    supabase,
    model,
    session_id,
    transcript,
    topic,
    request,
    prompt_group=None,
):
    llm = ChatOpenAI(model_name=model)
    request_messages=[HumanMessage(content=request)]
    #print(f"LRR Question: {request}")
    #print(f"##### System Prompt: {system_prompt}")
    #print(f"##### Transcript Length: {len(transcript)} characters")
    #print(f"##### Model: {model}")
    #print(f"##### Request Message: {request_messages}")
    llm_request=create_llm_msg(system_prompt,transcript,request_messages)
    response=llm.invoke(llm_request)
    params={
        'session_id': session_id,
        'question_topic': topic,
        'question_text': request,
        'prompt': request,
        'prompt_group': prompt_group or DEFAULT_PROMPT_GROUP,
        'response_content': response.content,
        'model': model,
    }
    supabase.create_session_qna(params)
    return response.content
