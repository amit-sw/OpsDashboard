import os

from datetime import date, datetime, timedelta, timezone
import time
from typing import Iterable, Tuple, List, Dict, Any, Optional
from googleapiclient.errors import HttpError



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

def _bucket_internal_ms(bucket_day: date) -> int:
    """Return a stable synthetic timestamp for the discovery day bucket.

    Discovery intentionally stores a lightweight index only. We avoid
    `messages.get(..., format="metadata")` per message because it makes the
    index step much slower and more expensive. The exact payload and exact
    Gmail `internalDate` are fetched later during hydration.
    """
    return int(datetime.combine(bucket_day, datetime.min.time(), tzinfo=timezone.utc).timestamp() * 1000)


def _list_ids(service, q: str, cap: int = 1000, include_spam_trash: bool = False) -> Iterable[Dict[str, Any]]:
    token, fetched = None, 0
    while True:
        req = (service.users().messages()
               .list(userId="me", q=q, maxResults=min(100, cap - fetched),
                     pageToken=token,
                     includeSpamTrash=include_spam_trash))
        resp = req.execute()
        msgs = resp.get("messages", [])
        if not msgs:
            break
        for m in msgs:
            msg_id = m.get("id")
            if not msg_id:
                continue
            yield {
                "id": msg_id,
                "thread_id": m.get("threadId"),
            }
        fetched += len(msgs)
        token = resp.get("nextPageToken")
        if not token or fetched >= cap:
            break

def _upsert_index_batch(rows: List[Dict[str, Any]]):
    # rows: [{id, thread_id, internal_ms, ymd}]
    if not rows:
        return {"attempted": 0, "inserted": 0, "existing": 0}
    existing_ids = supabase.get_existing_gmail_index_ids([row["id"] for row in rows])
    supabase.insert_gmail_index_records(rows)
    existing_count = len(existing_ids)
    return {
        "attempted": len(rows),
        "inserted": len(rows) - existing_count,
        "existing": existing_count,
    }

def backfill_index_for_date_range(
    service,
    start_date: date,
    end_date: date,
    window_days: int = 4,
    include_spam_trash: bool = False,
    progress_callback=None,
):
    """Discover Gmail ids for a date range and store a lightweight index only.

    Chosen tradeoff:
    Discovery stores only `id`, `thread_id` when available from Gmail list
    results, and the scanned `ymd` bucket. We also persist a synthetic
    `internal_ms` anchored to that bucket so the existing schema and ordering
    still work. Exact Gmail metadata and full message content are intentionally
    deferred to the fetch/hydration step.
    """
    start = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
    end = datetime.combine(end_date + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)
    seen: set[str] = set()             # in-memory dedupe across windows (idempotent if rerun)
    stats = {
        "gmail_ids_found": 0,
        "unique_ids_discovered": 0,
        "duplicates_in_scan": 0,
        "attempted_upserts": 0,
        "inserted": 0,
        "already_in_supabase": 0,
    }
    for after_ts, before_ts in _windows(start, end, window_days):
        bucket_day = datetime.fromtimestamp(after_ts, tz=timezone.utc).date()
        q = f"after:{after_ts} before:{before_ts}"   # whole mailbox (Inbox+Sent; Spam/Trash excluded unless flag)
        ids = list(_list_ids(service, q, cap=1000, include_spam_trash=include_spam_trash))
        stats["gmail_ids_found"] += len(ids)
        if progress_callback:
            progress_callback(
                {
                    "stage": "scan_window",
                    "window_query": q,
                    "gmail_ids_found": stats["gmail_ids_found"],
                    "unique_ids_discovered": stats["unique_ids_discovered"],
                    "duplicates_in_scan": stats["duplicates_in_scan"],
                    "attempted_upserts": stats["attempted_upserts"],
                    "inserted": stats["inserted"],
                    "already_in_supabase": stats["already_in_supabase"],
                }
            )
        if not ids:
            continue

        batch: List[Dict[str, Any]] = []
        for message_ref in ids:
            mid = message_ref["id"]
            if mid in seen:
                stats["duplicates_in_scan"] += 1
                continue
            seen.add(mid)
            stats["unique_ids_discovered"] += 1
            batch.append({
                "id": mid,
                "thread_id": message_ref.get("thread_id"),
                "internal_ms": _bucket_internal_ms(bucket_day),
                "ymd": bucket_day.isoformat(),
            })
            # flush periodically to keep memory small
            if len(batch) >= 200:
                batch_stats = _upsert_index_batch(batch)
                stats["attempted_upserts"] += batch_stats["attempted"]
                stats["inserted"] += batch_stats["inserted"]
                stats["already_in_supabase"] += batch_stats["existing"]
                if progress_callback:
                    progress_callback(
                        {
                            "stage": "index_batch",
                            "batch_attempted": batch_stats["attempted"],
                            "gmail_ids_found": stats["gmail_ids_found"],
                            "unique_ids_discovered": stats["unique_ids_discovered"],
                            "duplicates_in_scan": stats["duplicates_in_scan"],
                            "attempted_upserts": stats["attempted_upserts"],
                            "inserted": stats["inserted"],
                            "already_in_supabase": stats["already_in_supabase"],
                        }
                    )
                batch.clear()

        batch_stats = _upsert_index_batch(batch)  # flush remainder
        stats["attempted_upserts"] += batch_stats["attempted"]
        stats["inserted"] += batch_stats["inserted"]
        stats["already_in_supabase"] += batch_stats["existing"]
        if progress_callback and batch_stats["attempted"]:
            progress_callback(
                {
                    "stage": "index_batch",
                    "batch_attempted": batch_stats["attempted"],
                    "gmail_ids_found": stats["gmail_ids_found"],
                    "unique_ids_discovered": stats["unique_ids_discovered"],
                    "duplicates_in_scan": stats["duplicates_in_scan"],
                    "attempted_upserts": stats["attempted_upserts"],
                    "inserted": stats["inserted"],
                    "already_in_supabase": stats["already_in_supabase"],
                }
            )
    return stats

# ---- STEP 1: backfill index for last 6 months ----
def backfill_index_last_six_months(service, window_days: int = 4, include_spam_trash: bool = False):
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=182)  # ~6 months
    backfill_index_for_date_range(
        service,
        start.date(),
        now.date(),
        window_days=window_days,
        include_spam_trash=include_spam_trash,
    )
