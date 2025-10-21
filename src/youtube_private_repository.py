from datetime import datetime, timedelta, timezone
from typing import Iterable, List, Mapping, Optional, Set

from langsmith import traceable


class YouTubeVideoRepository:
    """Supabase-backed storage for YouTube private video transcripts."""

    def __init__(self, client, table_name: str = "youtube_private_videos"):
        self._client = client
        self._table_name = table_name

    def existing_ids(self) -> Set[str]:
        supabase = getattr(self._client, "supabase", None)
        if supabase is None:
            return set()
        try:
            response = supabase.table(self._table_name).select("video_id").execute()
        except Exception as exc:  # pragma: no cover - logged for observability
            print(f"Error fetching stored YouTube videos: {exc}")
            return set()
        rows = getattr(response, "data", []) or []
        return {row.get("video_id") for row in rows if row.get("video_id")}

    def latest_published_at(self) -> Optional[str]:
        supabase = getattr(self._client, "supabase", None)
        if supabase is None:
            return None
        try:
            response = (
                supabase.table(self._table_name)
                .select("published_at")
                .order("published_at", desc=True)
                .limit(1)
                .execute()
            )
        except Exception as exc:  # pragma: no cover - logged for observability
            print(f"Error fetching latest YouTube video timestamp: {exc}")
            return None
        rows = getattr(response, "data", []) or []
        if not rows:
            return None
        return rows[0].get("published_at")

    def earliest_published_at(self) -> Optional[str]:
        supabase = getattr(self._client, "supabase", None)
        if supabase is None:
            return None
        try:
            response = (
                supabase.table(self._table_name)
                .select("published_at")
                .order("published_at", desc=False)
                .limit(1)
                .execute()
            )
        except Exception as exc:  # pragma: no cover - logged for observability
            print(f"Error fetching earliest YouTube video timestamp: {exc}")
            return None
        rows = getattr(response, "data", []) or []
        if not rows:
            return None
        return rows[0].get("published_at")

    def existing_ids_for(self, video_ids: Iterable[str]) -> Set[str]:
        supabase = getattr(self._client, "supabase", None)
        unique_ids = {vid for vid in video_ids if vid}
        if supabase is None or not unique_ids:
            return set()
        try:
            response = (
                supabase.table(self._table_name)
                .select("video_id")
                .in_("video_id", list(unique_ids))
                .execute()
            )
        except Exception as exc:  # pragma: no cover - logged for observability
            print(f"Error checking existing YouTube videos: {exc}")
            return set()
        rows = getattr(response, "data", []) or []
        return {row.get("video_id") for row in rows if row.get("video_id")}

    def insert_records(self, records: Iterable[Mapping]) -> List[Mapping]:
        supabase = getattr(self._client, "supabase", None)
        payload = list(records)
        if supabase is None or not payload:
            return []
        try:
            response = supabase.table(self._table_name).upsert(payload).execute()
        except Exception as exc:  # pragma: no cover - logged for observability
            print(f"Error storing YouTube videos: {exc}")
            return []
        return getattr(response, "data", []) or []
