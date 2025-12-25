from types import SimpleNamespace

from langchain_core.messages import AIMessage, HumanMessage

import utils.utils_transcript_chat as transcript_chat


def test_create_llm_msg_includes_history():
    history = [HumanMessage(content="follow-up"), AIMessage(content="response")]
    messages = transcript_chat.create_llm_msg("system", "transcript", history)
    assert messages[0].content == "system"
    assert messages[1].content == "transcript"
    assert messages[2:] == history


def test_llm_request_response_records_qna(monkeypatch):
    captured = {}

    class DummyChat:
        def __init__(self, model_name):
            captured["model"] = model_name

        def invoke(self, messages):
            captured["messages"] = messages
            return SimpleNamespace(content="LLM response")

    class DummySupabase:
        def __init__(self):
            self.saved = None

        def create_session_qna(self, params):
            self.saved = params

    monkeypatch.setattr(transcript_chat, "ChatOpenAI", DummyChat)
    supabase = DummySupabase()

    result = transcript_chat.llm_request_response(
        supabase,
        "fake-model",
        "session-1",
        "full transcript text",
        "Topic",
        "Prompt text",
        "custom-group",
    )

    assert result == "LLM response"
    assert captured["model"] == "fake-model"
    assert captured["messages"][0].content == transcript_chat.system_prompt
    assert supabase.saved["session_id"] == "session-1"
    assert supabase.saved["question_topic"] == "Topic"
    assert supabase.saved["question_text"] == "Prompt text"
    assert supabase.saved["model"] == "fake-model"
    assert supabase.saved["prompt_group"] == "custom-group"
