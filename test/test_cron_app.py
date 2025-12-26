import sys
import types


class _DummyTransactionSearch:
    class created_at:
        @staticmethod
        def between(start, end):
            return (start, end)


class _DummyGateway:
    def __init__(self, *_, **__):
        self.transaction = types.SimpleNamespace(
            search=lambda *args, **kwargs: types.SimpleNamespace(items=[])
        )


sys.modules.setdefault(
    "braintree",
    types.SimpleNamespace(
        BraintreeGateway=_DummyGateway,
        Configuration=lambda *args, **kwargs: None,
        Environment=types.SimpleNamespace(Production="production"),
        TransactionSearch=_DummyTransactionSearch,
    ),
)


class _DummyAgentMailSDK:
    def __init__(self, *args, **kwargs):
        pass


sys.modules.setdefault("agentmail", types.SimpleNamespace(AgentMail=_DummyAgentMailSDK))

import cron_app


def test_qna_email_out_uses_prompt_group_and_to_address(monkeypatch):
    captured = {}

    class DummyMessages:
        def send(self, **kwargs):
            captured.update(kwargs)
            return types.SimpleNamespace(message_id="123")

    class DummyAgentMail:
        def __init__(self, api_key):
            captured["api_key"] = api_key
            self.inboxes = types.SimpleNamespace(messages=DummyMessages())

    monkeypatch.setenv("AGENTMAIL_API_KEY", "api-key")
    monkeypatch.setenv("AGENTMAIL_FROM_ADDRESS", "from@example.com")
    monkeypatch.setattr(cron_app, "AgentMail", DummyAgentMail)

    cron_app.qna_email_out(
        topic="Focus Session",
        response_list=[{"qt": "Topic A", "rc": "Answer"}],
        prompt_group="finance",
        to_address="finance@example.com",
    )

    assert captured["api_key"] == "api-key"
    assert captured["inbox_id"] == "from@example.com"
    assert captured["to"] == "finance@example.com"
    assert captured["subject"].startswith("[finance]")


def test_load_qna_email_map_filters_invalid_rows():
    class DummySupabase:
        def list_qna_emails(self):
            return [
                {"prompt_group": "alpha", "email": "alpha@example.com"},
                {"prompt_group": " ", "email": "missing@example.com"},
                {"prompt_group": "beta", "email": ""},
            ]

    mapping = cron_app._load_qna_email_map(DummySupabase())
    assert mapping == {"alpha": "alpha@example.com"}


def test_resolve_qna_recipient_uses_default_when_missing():
    mapping = {"alpha": "alpha@example.com"}
    assert (
        cron_app._resolve_qna_recipient("alpha", mapping, "fallback@example.com")
        == "alpha@example.com"
    )
    assert (
        cron_app._resolve_qna_recipient("beta", mapping, "fallback@example.com")
        == "fallback@example.com"
    )


def test_process_zoomsession_for_qna_groups_emails(monkeypatch):
    sent = []

    def fake_qna_email_out(topic, responses, group, to_address):
        sent.append(
            {
                "topic": topic,
                "group": group,
                "to": to_address,
                "questions": [row["qt"] for row in responses],
            }
        )

    class DummySupabase:
        def __init__(self):
            self.status_updates = []

        def update_zoomsession_status(self, session_id, status):
            self.status_updates.append((session_id, status))

    monkeypatch.setattr(cron_app, "qna_email_out", fake_qna_email_out)
    monkeypatch.setattr(
        cron_app,
        "question_prompts",
        [
            {"title": "Alpha", "prompt": "Prompt A", "prompt_group": "group-a"},
            {"title": "Beta", "prompt": "Prompt B", "prompt_group": "group-b"},
            {"title": "Common", "prompt": "Prompt C"},
        ],
    )

    def fake_llm_request_response(*args):
        return f"response-for-{args[5]}"

    monkeypatch.setattr(cron_app, "llm_request_response", fake_llm_request_response)
    monkeypatch.setattr(cron_app, "log_qna_response", lambda **kwargs: None)

    supabase = DummySupabase()
    row = {"session_id": "session-1", "transcript": "hello", "topic": "Focus"}
    cron_app.process_zoomsession_for_qna(
        supabase,
        row,
        {"group-a": "alpha@example.com"},
        "default@example.com",
    )

    assert supabase.status_updates == [("session-1", "QnA Completed")]
    assert len(sent) == 3
    assert sent[0]["group"] == "group-a" and sent[0]["to"] == "alpha@example.com"
    assert sent[1]["group"] == "group-b" and sent[1]["to"] == "default@example.com"
    assert sent[2]["group"] == "common" and sent[2]["to"] == "default@example.com"
