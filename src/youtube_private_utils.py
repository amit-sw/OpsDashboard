import io
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from langsmith import traceable

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

from src.core_utils import parse_srt

# This variable specifies the name of a file that contains the OAuth 2.0
# client secret information for your application, including your client ID and
# client secret.
CLIENT_SECRETS_FILE = "client_secret.json"

# This OAuth 2.0 access scope allows for full read access to the
# authenticated user's account, but not write access.
SCOPES = [
    'https://www.googleapis.com/auth/youtube.readonly',
    'https://www.googleapis.com/auth/youtube.force-ssl',
]
API_SERVICE_NAME = 'youtube'
API_VERSION = 'v3'
TOKEN_FILE = Path(".tokens") / "youtube.json"
PREFERRED_LANGUAGES: Sequence[str] = ("en-US", "en", "en-GB")
REQUIRED_SCOPES = set(SCOPES)


def _ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def get_authenticated_service(credentials):
    return build(API_SERVICE_NAME, API_VERSION, credentials=credentials)


class TranscriptRetrievalError(RuntimeError):
    """Raised when a YouTube transcript cannot be retrieved."""


def get_user_credentials(authorization_code):
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri='http://localhost:8501'
    )
    flow.fetch_token(code=authorization_code)
    return flow.credentials


def get_authorization_url():
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri='http://localhost:8501'
    )
    authorization_url, _ = flow.authorization_url(
        prompt='consent',
        access_type='offline',
        include_granted_scopes='true'
    )
    return authorization_url


def get_transcript_segments(
    video_id: str,
    *,
    credentials: Optional[Credentials] = None,
    service=None,
    preferred_languages: Sequence[str] = PREFERRED_LANGUAGES,
) -> List[Dict[str, Any]]:
    if service is None:
        if credentials is None:
            raise ValueError("credentials or service must be provided")
        service = get_authenticated_service(credentials)
    try:
        response = (
            service
            .captions()
            .list(part="id,snippet", videoId=video_id)
            .execute()
        )
    except HttpError as exc:
        if exc.resp.status == 403:
            raise TranscriptRetrievalError(
                "Caption list failed: insufficient permission. Please reauthorize the application."
            ) from exc
        raise TranscriptRetrievalError(f"Caption list failed: {exc}") from exc

    items = response.get("items", [])
    if not items:
        raise TranscriptRetrievalError("No caption tracks available.")

    caption = _select_caption_track(items, preferred_languages)
    if caption is None:
        raise TranscriptRetrievalError("No suitable caption track found.")

    try:
        srt_text = download_caption_srt(service, caption["id"])
    except HttpError as exc:
        if exc.resp.status == 403:
            raise TranscriptRetrievalError(
                "Caption download failed: insufficient permission. Please reauthorize the application."
            ) from exc
        raise TranscriptRetrievalError(f"Caption download failed: {exc}") from exc

    segments = parse_srt(srt_text)
    if not segments:
        raise TranscriptRetrievalError("Caption track is empty.")
    return segments


def _select_caption_track(
    items: Iterable[Dict[str, Any]],
    preferred_languages: Sequence[str],
) -> Optional[Dict[str, Any]]:
    best_item = None
    best_score = -1
    for item in items:
        snippet = item.get("snippet", {})
        language = snippet.get("language")
        track_kind = snippet.get("trackKind")
        is_auto = track_kind == "ASR"
        score = 0
        if language in preferred_languages:
            score += 2
        if track_kind == "standard":
            score += 1
        if not snippet.get("isDraft"):
            score += 1
        if is_auto:
            score -= 1
        if score > best_score:
            best_item = item
            best_score = score
    return best_item


def download_caption_srt(service, caption_id: str, tfmt: str = "srt") -> str:
    request = service.captions().download(id=caption_id, tfmt=tfmt)
    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)
    done = False
    while not done:
        _status, done = downloader.next_chunk()
    return buffer.getvalue().decode("utf-8", errors="replace")


def credentials_have_required_scopes(credentials: Optional[Credentials]) -> bool:
    if not credentials:
        return False
    scopes = set(getattr(credentials, "scopes", []) or [])
    return REQUIRED_SCOPES.issubset(scopes)


def save_credentials(credentials: Credentials, token_path: Path = TOKEN_FILE) -> None:
    if not credentials:
        return
    _ensure_parent_dir(token_path)
    token_path.write_text(credentials.to_json())


def load_stored_credentials(token_path: Path = TOKEN_FILE) -> Optional[Credentials]:
    if not token_path.exists():
        return None
    try:
        data = json.loads(token_path.read_text())
    except json.JSONDecodeError:
        return None
    return Credentials.from_authorized_user_info(data, scopes=SCOPES)


def refresh_credentials(credentials: Credentials, token_path: Path = TOKEN_FILE) -> Optional[Credentials]:
    if not credentials:
        return None
    if not credentials.expired:
        return credentials
    if not credentials.refresh_token:
        return None
    credentials.refresh(Request())
    save_credentials(credentials, token_path)
    return credentials


def clear_stored_credentials(token_path: Path = TOKEN_FILE) -> None:
    if token_path.exists():
        token_path.unlink()


def _format_rfc3339(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _to_rfc3339(value: Optional[Any]) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        if text.endswith("Z"):
            if "." in text:
                try:
                    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
                    return _format_rfc3339(parsed)
                except ValueError:
                    return text.split(".")[0] + "Z"
            return text
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return text
        return _format_rfc3339(parsed)
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return _format_rfc3339(value)
    return str(value)


def list_my_channels(service) -> List[Dict[str, Any]]:
    response = service.channels().list(
        part="snippet,contentDetails",
        mine=True,
        maxResults=50,
    ).execute()
    channels: List[Dict[str, Any]] = []
    for item in response.get("items", []):
        channels.append(
            {
                "channel_id": item.get("id"),
                "title": item.get("snippet", {}).get("title", ""),
                "uploads_playlist_id": item.get("contentDetails", {})
                .get("relatedPlaylists", {})
                .get("uploads"),
            }
        )
    return channels


def _get_uploads_playlist_id(service, channel_id: Optional[str] = None) -> str:
    channels = list_my_channels(service)
    if not channels:
        raise RuntimeError("No channels found for the authenticated user.")
    if channel_id:
        for channel in channels:
            if channel.get("channel_id") == channel_id:
                playlist_id = channel.get("uploads_playlist_id")
                break
        else:
            raise RuntimeError(f"Channel {channel_id} is not available.")
    else:
        playlist_id = channels[0].get("uploads_playlist_id")
    if not playlist_id:
        raise RuntimeError("Uploads playlist is unavailable for this account.")
    return playlist_id


def _playlist_item_to_video(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    details = item.get("contentDetails", {})
    snippet = item.get("snippet", {})
    video_id = details.get("videoId") or snippet.get("resourceId", {}).get("videoId")
    if not video_id:
        return None
    published_at = details.get("videoPublishedAt") or snippet.get("publishedAt")
    return {
        "video_id": video_id,
        "title": snippet.get("title", ""),
        "published_at": published_at,
    }


def _playlist_pages(service, playlist_id: str):
    page_token: Optional[str] = None
    while True:
        params = {
            "part": "snippet,contentDetails",
            "playlistId": playlist_id,
            "maxResults": 50,
        }
        if page_token:
            params["pageToken"] = page_token
        response = service.playlistItems().list(**params).execute()
        yield response
        page_token = response.get("nextPageToken")
        if not page_token:
            break


def _search_pages(service, **kwargs):
    page_token: Optional[str] = None
    while True:
        params = kwargs.copy()
        if page_token:
            params["pageToken"] = page_token
        response = service.search().list(**params).execute()
        yield response
        page_token = response.get("nextPageToken")
        if not page_token:
            break


def _search_item_to_video(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if item.get("id", {}).get("kind") != "youtube#video":
        return None
    video_id = item.get("id", {}).get("videoId")
    if not video_id:
        return None
    snippet = item.get("snippet", {})
    return {
        "video_id": video_id,
        "title": snippet.get("title", ""),
        "published_at": snippet.get("publishedAt"),
    }


def _search_videos(
    service,
    channel_id: str,
    max_results: Optional[int],
    published_after: Optional[str],
    published_before: Optional[str],
) -> List[Dict[str, Any]]:
    collected: List[Dict[str, Any]] = []
    params = {
        "part": "snippet",
        "type": "video",
        "order": "date",
        "maxResults": 50,
        "forMine": True,
    }
    if published_after:
        params["publishedAfter"] = published_after
    if published_before:
        params["publishedBefore"] = published_before
    for response in _search_pages(service, **params):
        for item in response.get("items", []):
            snippet = item.get("snippet", {})
            if channel_id and snippet.get("channelId") != channel_id:
                continue
            video = _search_item_to_video(item)
            if not video:
                continue
            published_at = video.get("published_at") or ""
            if published_after and published_at and published_at < published_after:
                continue
            collected.append(video)
            if max_results and len(collected) >= max_results:
                return collected
    return collected


def _collect_videos_from_playlist(
    service,
    playlist_id: str,
    max_results: Optional[int],
    published_after: Optional[str],
) -> List[Dict[str, Any]]:
    collected: List[Dict[str, Any]] = []
    for response in _playlist_pages(service, playlist_id):
        for item in response.get("items", []):
            video = _playlist_item_to_video(item)
            if not video:
                continue
            published_at = video.get("published_at") or ""
            if published_after and published_at and published_at < published_after:
                return collected
            collected.append(video)
            if max_results and len(collected) >= max_results:
                return collected
    return collected


@traceable(run_type="tool")
def get_my_videos(
    credentials: Optional[Credentials],
    max_results: int = 10,
    published_after: Optional[Any] = None,
    published_before: Optional[Any] = None,
    *,
    service=None,
    channel_id: Optional[str] = None,
    uploads_playlist_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    if service is None:
        if credentials is None:
            raise ValueError("credentials or service must be provided")
        service = get_authenticated_service(credentials)
    collected: List[Dict[str, Any]] = []
    published_after_str = _to_rfc3339(published_after)
    if published_after_str:
        now_iso = _format_rfc3339(datetime.now(timezone.utc))
        if published_after_str > now_iso:
            published_after_str = now_iso
    published_before_str = _to_rfc3339(published_before)
    if published_before_str:
        now_iso = _format_rfc3339(datetime.now(timezone.utc))
        if published_before_str > now_iso:
            published_before_str = now_iso
    channel_id = channel_id or list_my_channels(service)[0]["channel_id"]
    if not channel_id:
        raise RuntimeError("Unable to determine the channel ID.")
    collected = _search_videos(
        service,
        channel_id,
        max_results,
        published_after_str,
        published_before_str,
    )
    if published_after_str:
        collected.sort(key=lambda v: v.get("published_at") or "")
    if max_results and len(collected) > max_results:
        return collected[:max_results]
    return collected

@traceable(run_type="tool")
def get_transcript(
    video_id: str,
    *,
    credentials: Optional[Credentials] = None,
    service=None,
) -> str:
    try:
        segments = get_transcript_segments(
            video_id,
            credentials=credentials,
            service=service,
        )
    except TranscriptRetrievalError as exc:
        return f"Could not retrieve transcript: {exc}"
    return " ".join(segment["text"] for segment in segments if segment.get("text"))
