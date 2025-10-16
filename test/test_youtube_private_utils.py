from types import SimpleNamespace
import sys


class _FakeTranscriptApi:
    @staticmethod
    def get_transcript(*_args, **_kwargs):
        return []


sys.modules.setdefault("youtube_transcript_api", SimpleNamespace(YouTubeTranscriptApi=_FakeTranscriptApi))

from src import youtube_private_utils


class _DummyFlow:
    def __init__(self):
        self.credentials = SimpleNamespace(token="dummy-token")
        self.called_with = None

    def fetch_token(self, **kwargs):
        self.called_with = kwargs


def test_get_user_credentials_passes_code(monkeypatch):
    dummy = _DummyFlow()

    def fake_from_client_secrets_file(*args, **kwargs):
        return dummy

    monkeypatch.setattr(
        youtube_private_utils,
        "Flow",
        SimpleNamespace(from_client_secrets_file=fake_from_client_secrets_file),
    )

    credentials = youtube_private_utils.get_user_credentials("abc123")

    assert dummy.called_with == {"code": "abc123"}
    assert credentials.token == "dummy-token"
