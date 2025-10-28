import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from googleapiclient.errors import HttpError

from src import youtube_private_utils


class _DummyFlow:
    def __init__(self):
        self.credentials = SimpleNamespace(token="dummy-token")
        self.called_with = None

    def fetch_token(self, **kwargs):
        self.called_with = kwargs


class _DummyCredentials:
    def __init__(self, token, refresh_token=None, expired=False, scopes=None):
        self.token = token
        self.refresh_token = refresh_token
        self.expired = expired
        self.refreshed = False
        self.scopes = list(scopes if scopes is not None else youtube_private_utils.SCOPES)

    def to_json(self):
        return json.dumps({"token": self.token, "refresh_token": self.refresh_token})

    def refresh(self, _request):
        self.refreshed = True
        self.expired = False
        self.token = "new-token"

    @classmethod
    def from_authorized_user_info(cls, info, scopes):
        _ = scopes
        return cls(info["token"], info.get("refresh_token"))


class _FakePlaylistItemsInvoker:
    def __init__(self, parent, params):
        self._parent = parent
        self._params = params

    def execute(self):
        self._parent.calls.append(self._params)
        return self._parent.responses.pop(0)


class _FakePlaylistItems:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def list(self, **params):
        return _FakePlaylistItemsInvoker(self, params)


class _FakeSearchInvoker:
    def __init__(self, parent, params):
        self._parent = parent
        self._params = params

    def execute(self):
        self._parent.calls.append(self._params)
        return self._parent.responses.pop(0)


class _FakeSearch:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def list(self, **params):
        return _FakeSearchInvoker(self, params)


class _FakeChannels:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def list(self, **params):
        self.calls.append(params)
        return SimpleNamespace(execute=lambda: self.response)


class _FakeCaptions:
    def __init__(self, response):
        self.response = response
        self.list_calls = []

    def list(self, **params):
        self.list_calls.append(params)
        return SimpleNamespace(execute=lambda: self.response)

    def download(self, **params):
        raise NotImplementedError


class _FakeYouTubeService:
    def __init__(self, search_responses, caption_response, channels_response):
        self._search = _FakeSearch(search_responses)
        self._captions = _FakeCaptions(caption_response)
        self._channels = _FakeChannels(channels_response)

    def search(self):
        return self._search

    def captions(self):
        return self._captions

    def channels(self):
        return self._channels


def test_get_user_credentials_passes_code(monkeypatch):
    dummy = _DummyFlow()

    def fake_from_client_secrets_file(*_args, **_kwargs):
        return dummy

    monkeypatch.setattr(
        youtube_private_utils,
        "Flow",
        SimpleNamespace(from_client_secrets_file=fake_from_client_secrets_file),
    )

    credentials = youtube_private_utils.get_user_credentials("abc123")

    assert dummy.called_with == {"code": "abc123"}
    assert credentials.token == "dummy-token"


def test_save_and_load_credentials_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(youtube_private_utils, "Credentials", _DummyCredentials)
    token_path = tmp_path / "youtube.json"
    youtube_private_utils.save_credentials(_DummyCredentials("abc", "refresh"), token_path=token_path)

    loaded = youtube_private_utils.load_stored_credentials(token_path=token_path)

    assert isinstance(loaded, _DummyCredentials)
    assert loaded.token == "abc"
    assert loaded.refresh_token == "refresh"


def test_refresh_credentials_persists_updates(monkeypatch):
    monkeypatch.setattr(youtube_private_utils, "Credentials", _DummyCredentials)
    monkeypatch.setattr(youtube_private_utils, "Request", lambda: object())

    saved = {}

    def fake_save(creds, token_path):
        saved["token"] = creds.token
        saved["path"] = token_path

    monkeypatch.setattr(youtube_private_utils, "save_credentials", fake_save)

    creds = _DummyCredentials("old", "refresh", expired=True)
    result = youtube_private_utils.refresh_credentials(creds, token_path=Path("dummy"))

    assert result is creds
    assert creds.refreshed
    assert saved["token"] == "new-token"


def test_refresh_credentials_without_refresh_token(monkeypatch):
    monkeypatch.setattr(youtube_private_utils, "Credentials", _DummyCredentials)
    creds = _DummyCredentials("old", refresh_token=None, expired=True)

    assert youtube_private_utils.refresh_credentials(creds, token_path=Path("dummy")) is None


def test_credentials_have_required_scopes():
    creds = _DummyCredentials("token", scopes=youtube_private_utils.SCOPES)
    assert youtube_private_utils.credentials_have_required_scopes(creds)

    missing = _DummyCredentials("token", scopes=[youtube_private_utils.SCOPES[0]])
    assert not youtube_private_utils.credentials_have_required_scopes(missing)


def test_get_my_videos_paginates_and_sorts(monkeypatch):
    responses = [
        {
            "items": [
                {
                    "id": {"kind": "youtube#video", "videoId": "b"},
                    "snippet": {
                        "channelId": "channel-1",
                        "title": "Two",
                        "publishedAt": "2024-01-02T00:00:00Z",
                    },
                },
            ],
            "nextPageToken": "TOKEN",
        },
        {
            "items": [
                {
                    "id": {"kind": "youtube#video", "videoId": "c"},
                    "snippet": {
                        "channelId": "channel-1",
                        "title": "Three",
                        "publishedAt": "2024-01-03T00:00:00Z",
                    },
                },
                {
                    "id": {"kind": "youtube#video", "videoId": "a"},
                    "snippet": {
                        "channelId": "channel-1",
                        "title": "One",
                        "publishedAt": "2024-01-01T00:00:00Z",
                    },
                },
            ],
        },
    ]
    channel_payload = {
        "items": [
            {
                "id": "channel-1",
                "snippet": {"title": "Channel 1"},
                "contentDetails": {"relatedPlaylists": {"uploads": "UPLOADS"}},
            },
        ]
    }
    service = _FakeYouTubeService(
        search_responses=responses,
        caption_response={"items": []},
        channels_response=channel_payload,
    )
    monkeypatch.setattr(youtube_private_utils, "get_authenticated_service", lambda _creds: service)

    videos = youtube_private_utils.get_my_videos("creds", max_results=3, published_after="2024-01-01T00:00:00Z")

    assert [v["video_id"] for v in videos] == ["a", "b", "c"]
    assert all(call.get("forMine") for call in service.search().calls)
    assert all("channelId" not in call for call in service.search().calls)
    assert service.channels().calls[0]["mine"] is True


def test_get_my_videos_accepts_datetime(monkeypatch):
    responses = [
        {
            "items": [
                {
                    "id": {"kind": "youtube#video", "videoId": "keep"},
                    "snippet": {
                        "channelId": "channel-1",
                        "title": "Keep",
                        "publishedAt": "2024-01-02T00:00:00Z",
                    },
                },
                {
                    "id": {"kind": "youtube#video", "videoId": "skip"},
                    "snippet": {
                        "channelId": "channel-1",
                        "title": "Skip",
                        "publishedAt": "2023-12-31T23:00:00Z",
                    },
                },
            ],
        }
    ]
    channel_payload = {
        "items": [
            {
                "id": "channel-1",
                "snippet": {"title": "Channel 1"},
                "contentDetails": {"relatedPlaylists": {"uploads": "UPLOADS"}},
            },
        ]
    }
    service = _FakeYouTubeService(
        search_responses=responses,
        caption_response={"items": []},
        channels_response=channel_payload,
    )
    monkeypatch.setattr(youtube_private_utils, "get_authenticated_service", lambda _creds: service)

    videos = youtube_private_utils.get_my_videos(
        "creds",
        max_results=2,
        published_after=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )

    assert [v["video_id"] for v in videos] == ["keep"]


def test_get_my_videos_normalizes_iso_strings(monkeypatch):
    responses = [
        {
            "items": [
                {
                    "id": {"kind": "youtube#video", "videoId": "keep"},
                    "snippet": {
                        "channelId": "channel-1",
                        "title": "Keep",
                        "publishedAt": "2024-01-01T00:00:00Z",
                    },
                },
                {
                    "id": {"kind": "youtube#video", "videoId": "skip"},
                    "snippet": {
                        "channelId": "channel-1",
                        "title": "Skip",
                        "publishedAt": "2023-12-31T23:59:59Z",
                    },
                },
            ],
        }
    ]
    channel_payload = {
        "items": [
            {
                "id": "channel-1",
                "snippet": {"title": "Channel 1"},
                "contentDetails": {"relatedPlaylists": {"uploads": "UPLOADS"}},
            },
        ]
    }
    service = _FakeYouTubeService(
        search_responses=responses,
        caption_response={"items": []},
        channels_response=channel_payload,
    )
    monkeypatch.setattr(youtube_private_utils, "get_authenticated_service", lambda _creds: service)

    videos = youtube_private_utils.get_my_videos(
        "creds",
        max_results=2,
        published_after="2024-01-01T00:00:00+00:00",
    )

    assert [v["video_id"] for v in videos] == ["keep"]


def test_list_my_channels_returns_expected_shape():
    responses = [{"items": []}]
    channel_payload = {
        "items": [
            {
                "id": "channel-1",
                "snippet": {"title": "Primary"},
                "contentDetails": {"relatedPlaylists": {"uploads": "UPLOADS1"}},
            },
            {
                "id": "channel-2",
                "snippet": {"title": "Brand"},
                "contentDetails": {"relatedPlaylists": {"uploads": "UPLOADS2"}},
            },
        ]
    }
    service = _FakeYouTubeService(
        search_responses=responses,
        caption_response={"items": []},
        channels_response=channel_payload,
    )

    channels = youtube_private_utils.list_my_channels(service)

    assert channels[0]["channel_id"] == "channel-1"
    assert channels[1]["uploads_playlist_id"] == "UPLOADS2"


def test_get_my_videos_respects_explicit_channel(monkeypatch):
    responses = [
        {
            "items": [
                {
                    "id": {"kind": "youtube#video", "videoId": "x"},
                    "snippet": {
                        "channelId": "channel-x",
                        "title": "X",
                        "publishedAt": "2024-01-02T00:00:00Z",
                    },
                },
                {
                    "id": {"kind": "youtube#video", "videoId": "y"},
                    "snippet": {
                        "channelId": "channel-y",
                        "title": "Y",
                        "publishedAt": "2024-01-03T00:00:00Z",
                    },
                }
            ]
        }
    ]
    channel_payload = {"items": []}
    service = _FakeYouTubeService(
        search_responses=responses,
        caption_response={"items": []},
        channels_response=channel_payload,
    )
    monkeypatch.setattr(youtube_private_utils, "get_authenticated_service", lambda _creds: service)

    videos = youtube_private_utils.get_my_videos(
        "creds",
        max_results=1,
        published_after=None,
        channel_id="channel-x",
    )

    assert [v["video_id"] for v in videos] == ["x"]
    assert all(call.get("forMine") for call in service.search().calls)


def test_get_transcript_segments_uses_caption_download(monkeypatch):
    caption_response = {
        "items": [
            {"id": "caption1", "snippet": {"language": "en", "trackKind": "standard", "isDraft": False}}
        ]
    }
    service = _FakeYouTubeService(
        search_responses=[{"items": []}],
        caption_response=caption_response,
        channels_response={"items": []},
    )
    downloaded = {"called_with": None}

    def fake_download_caption_srt(_service, caption_id, tfmt="srt"):
        downloaded["called_with"] = caption_id
        return "1\n00:00:01,000 --> 00:00:02,000\nHello\n"

    monkeypatch.setattr(youtube_private_utils, "download_caption_srt", fake_download_caption_srt)

    segments = youtube_private_utils.get_transcript_segments("video123", service=service)

    assert downloaded["called_with"] == "caption1"
    assert segments[0]["text"] == "Hello"


def test_get_transcript_segments_raises_when_missing_caption(monkeypatch):
    service = _FakeYouTubeService(
        search_responses=[{"items": []}],
        caption_response={"items": []},
        channels_response={"items": []},
    )

    with pytest.raises(youtube_private_utils.TranscriptRetrievalError):
        youtube_private_utils.get_transcript_segments("video123", service=service)


def test_get_transcript_segments_reports_insufficient_permissions(monkeypatch):
    service = _FakeYouTubeService(
        search_responses=[{"items": []}],
        caption_response={"items": []},
        channels_response={"items": []},
    )

    class Response:
        def __init__(self, status):
            self.status = status
            self.reason = "Forbidden"

    def failing_list(**_params):
        def execute():
            raise HttpError(Response(403), b"{}");
        return SimpleNamespace(execute=execute)

    service._captions.list = failing_list

    with pytest.raises(youtube_private_utils.TranscriptRetrievalError) as exc_info:
        youtube_private_utils.get_transcript_segments("video123", service=service)

    assert "insufficient permission" in str(exc_info.value).lower()


def test_get_transcript_returns_error_message(monkeypatch):
    def fake_get_segments(*_args, **_kwargs):
        raise youtube_private_utils.TranscriptRetrievalError("boom")

    monkeypatch.setattr(youtube_private_utils, "get_transcript_segments", fake_get_segments)

    text = youtube_private_utils.get_transcript(
        "video123",
        service=_FakeYouTubeService(
            search_responses=[],
            caption_response={"items": []},
            channels_response={"items": []},
        ),
    )

    assert "boom" in text
