import io
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

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


def _to_rfc3339(value: Optional[Any]) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return str(value)


def get_my_videos(
    credentials: Optional[Credentials],
    max_results: int = 10,
    published_after: Optional[Any] = None,
    *,
    service=None,
) -> List[Dict[str, Any]]:
    if service is None:
        if credentials is None:
            raise ValueError("credentials or service must be provided")
        service = get_authenticated_service(credentials)
    collected: List[Dict[str, Any]] = []
    page_token: Optional[str] = None
    published_after_str = _to_rfc3339(published_after)
    while len(collected) < max_results:
        params = {
            "part": "snippet",
            "forMine": True,
            "type": "video",
            "order": "date",
            "maxResults": min(50, max_results - len(collected)),
        }
        if page_token:
            params["pageToken"] = page_token
        if published_after_str:
            params["publishedAfter"] = published_after_str
        response = service.search().list(**params).execute()
        items = response.get("items", [])
        collected.extend({
            "video_id": item["id"]["videoId"],
            "title": item.get("snippet", {}).get("title", ""),
            "published_at": item.get("snippet", {}).get("publishedAt"),
        } for item in items if item.get("id", {}).get("videoId"))
        page_token = response.get("nextPageToken")
        if not page_token:
            break
    collected.sort(key=lambda v: v.get("published_at") or "")
    return collected


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
