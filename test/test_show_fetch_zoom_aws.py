import src.show_fetch_zoom_aws as fetch_zoom


def test_get_bucket_contents_decodes_utf8(monkeypatch):
    monkeypatch.setattr(
        fetch_zoom, "fetch_s3_object", lambda bucket, key, region: b"hello world"
    )
    assert (
        fetch_zoom.get_bucket_contents("bucket", "key", "region") == "hello world"
    )


def test_get_bucket_contents_returns_base64_for_binary(monkeypatch):
    monkeypatch.setattr(fetch_zoom, "fetch_s3_object", lambda *args: b"\xff")
    assert fetch_zoom.get_bucket_contents("bucket", "key", "region") == "/w=="


def test_process_one_record_merges_transcripts_and_saves(monkeypatch):
    saved = []
    monkeypatch.setattr(fetch_zoom, "extract_field_value", lambda field: field)
    monkeypatch.setattr(fetch_zoom, "decode_json_value", lambda value: value)
    monkeypatch.setattr(
        fetch_zoom,
        "get_bucket_contents",
        lambda bucket, key, region: f"{bucket}-{key}",
    )
    monkeypatch.setattr(
        fetch_zoom, "save_to_supabase", lambda row: saved.append(row.copy())
    )

    record = [
        "session-1",
        [{"bucket": "b1", "key": "k1"}, {"bucket": "b2", "key": "k2"}],
        "UTC",
    ]
    result = fetch_zoom.process_one_record(
        record, ["session_id", "transcript", "time_zone"], "us-east-1"
    )

    assert result["transcript"] == "b1-k1b2-k2"
    assert "time_zone" not in result
    assert saved and saved[0]["session_id"] == "session-1"


def test_process_one_record_handles_missing_transcript(monkeypatch):
    monkeypatch.setattr(fetch_zoom, "extract_field_value", lambda field: field)
    monkeypatch.setattr(fetch_zoom, "decode_json_value", lambda value: None)

    def _fail(_):
        raise AssertionError("save_to_supabase should not be called")

    monkeypatch.setattr(fetch_zoom, "save_to_supabase", _fail)

    record = ["session-1", None, "UTC"]
    result = fetch_zoom.process_one_record(
        record, ["session_id", "transcript", "time_zone"], "us-east-1"
    )

    assert result["transcript"] is None


def test_process_zoomsession_for_qna_invokes_llm_and_updates_status(monkeypatch):
    calls = []
    logged = []

    class DummySupabase:
        def __init__(self):
            self.status_updates = []

        def update_zoomsession_status(self, session_id, status):
            self.status_updates.append((session_id, status))

    def fake_llm_request_response(supabase, model, session_id, transcript, topic, prompt):
        calls.append((model, session_id, topic, prompt))
        return "ok"

    def fake_log_qna_response(**kwargs):
        logged.append(kwargs)

    monkeypatch.setattr(fetch_zoom, "question_prompts", [{"title": "Topic", "prompt": "Prompt"}])
    monkeypatch.setattr(fetch_zoom, "llm_request_response", fake_llm_request_response)
    monkeypatch.setattr(fetch_zoom, "log_qna_response", fake_log_qna_response)
    monkeypatch.setenv("OPENAI_MODEL", "fake-model")

    supabase = DummySupabase()
    row = {"session_id": "session-9", "transcript": "hello", "topic": "Focus"}
    fetch_zoom.process_zoomsession_for_qna(supabase, row)

    assert calls == [("fake-model", "session-9", "Focus", "Prompt")]
    assert supabase.status_updates == [("session-9", "QnA Completed")]
    assert logged and logged[0]["session_id"] == "session-9"
