import os

from datetime import datetime, timedelta, timezone
import time
from typing import Iterable, Tuple, List, Dict, Any, Optional



from utils.supabase_integration import SupabaseClient

# --- Supabase client (adjust env as needed) ---
supabase = SupabaseClient(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

# ---- helpers ----
def _unix(dt: datetime) -> int:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())

def _windows(start_utc: datetime, end_utc: datetime, window_days: int = 4) -> Iterable[Tuple[int, int]]:
    """Yield [after,before) unix-second windows oldest→newest with 1s overlap."""
    after = _unix(start_utc)
    end = _unix(end_utc)
    span = window_days * 86400
    while after < end:
        before = min(end, after + span)
        yield after, before
        after = before - 1  # 1s overlap to avoid gaps

def _list_ids(service, q: str, cap: int = 1000, include_spam_trash: bool = False) -> Iterable[str]:
    token, fetched = None, 0
    while True:
        req = (service.users().messages()
               .list(userId="me", q=q, maxResults=min(100, cap - fetched),
                     includeSpamTrash=include_spam_trash))
        resp = req.execute()
        msgs = resp.get("messages", [])
        if not msgs:
            break
        for m in msgs:
            yield m["id"]
        fetched += len(msgs)
        token = resp.get("nextPageToken")
        if not token or fetched >= cap:
            break

def _get_meta(service, msg_id: str) -> Dict[str, Any]:
    # metadata format is fast and includes internalDate
    return (service.users()
            .messages()
            .get(userId="me", id=msg_id, format="metadata",
                 metadataHeaders=["From", "Subject", "Date"])
            .execute())

def _ymd_from_ms(internal_ms: int) -> str:
    dt = datetime.fromtimestamp(internal_ms / 1000, tz=timezone.utc)
    return dt.strftime("%Y-%m-%d")

def _upsert_index_batch(rows: List[Dict[str, Any]]):
    # rows: [{id, thread_id, internal_ms, ymd}]
    if not rows:
        return
    supabase.insert_gmail_index_records(rows)

# ---- STEP 1: backfill index for last 6 months ----
def backfill_index_last_six_months(service, window_days: int = 4, include_spam_trash: bool = False):
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=182)  # ~6 months
    seen: set[str] = set()             # in-memory dedupe across windows (idempotent if rerun)
    for after_ts, before_ts in _windows(start, now, window_days):
        q = f"after:{after_ts} before:{before_ts}"   # whole mailbox (Inbox+Sent; Spam/Trash excluded unless flag)
        ids = list(_list_ids(service, q, cap=1000, include_spam_trash=include_spam_trash))
        if not ids:
            continue

        batch: List[Dict[str, Any]] = []
        for mid in ids:
            if mid in seen:
                continue
            seen.add(mid)
            meta = _get_meta(service, mid)
            internal_ms = int(meta.get("internalDate", 0))
            ymd = _ymd_from_ms(internal_ms)
            batch.append({
                "id": mid,
                "thread_id": meta.get("threadId"),
                "internal_ms": internal_ms,
                "ymd": ymd
            })
            # flush periodically to keep memory small
            if len(batch) >= 200:
                _upsert_index_batch(batch)
                batch.clear()

        _upsert_index_batch(batch)  # flush remainder