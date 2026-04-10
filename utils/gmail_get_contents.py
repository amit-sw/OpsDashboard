
from datetime import datetime, timedelta, timezone
import time
from typing import Iterable, Tuple, List, Dict, Any, Optional

from utils.supabase_integration import SupabaseClient

def _insert_messages_batch(supabase, rows: List[Dict[str, Any]]):
    # rows: [{id, thread_id, internal_ms, headers, snippet, body_full, raw_json}]
    if not rows:
        return {
            "attempted": 0,
            "inserted": 0,
            "existing": 0,
            "body_filled": 0,
            "already_complete": 0,
        }
    existing_records = supabase.get_existing_gmail_message_records([row["id"] for row in rows])
    response=supabase.insert_messages_batch(rows)
    existing_count = len(existing_records)
    body_filled = 0
    already_complete = 0
    for row in rows:
        msg_id = row["id"]
        existing = existing_records.get(msg_id)
        if not existing:
            continue
        had_body = bool((existing.get("body_full") or "").strip())
        new_body = bool((row.get("body_full") or "").strip())
        if had_body:
            already_complete += 1
        elif new_body:
            body_filled += 1
        else:
            already_complete += 1
    return {
        "attempted": len(rows),
        "inserted": len(rows) - existing_count,
        "existing": existing_count,
        "body_filled": body_filled,
        "already_complete": already_complete,
    }

def fetch_and_store_messages_for_day(supabase, service, ymd: str, fetch_bodies: bool = True, progress_callback=None):
    """
    ymd: 'YYYY-MM-DD' (UTC)
    Fetch IDs from gmail_message_index for that date, hydrate with Gmail API, and upsert into gmail_messages.
    """
    # 1) get IDs for that day
    ids = supabase.get_ids(ymd, fetch_bodies)

    batch: List[Dict[str, Any]] = []
    stats = {
        "indexed_for_day": len(ids),
        "attempted_upserts": 0,
        "inserted": 0,
        "already_in_supabase": 0,
        "processed_messages": 0,
        "body_filled": 0,
        "already_complete": 0,
    }
    for row in ids:
        mid = row["id"]
        # fetch full or metadata depending on your needs
        msg = (service.users().messages()
               .get(userId="me", id=mid, format="full" if fetch_bodies else "metadata",
                    metadataHeaders=["From","To","Subject","Date"])
               .execute())

        payload = {
            "id": mid,
            "thread_id": msg.get("threadId") or row.get("thread_id"),
            "internal_ms": int(msg.get("internalDate", row.get("internal_ms", 0))),
            "headers": None,
            "snippet": msg.get("snippet"),
            "body_full": None,
            "raw_json": msg if not fetch_bodies else None,   # optional: store entire JSON
        }

        # extract headers
        payload["headers"] = {}
        for h in msg.get("payload", {}).get("headers", []):
            name = h.get("name")
            if name in ("From", "To", "Subject", "Date", "Message-ID"):
                payload["headers"][name] = h.get("value", "")

        # (optional) extract body text when format="full"
        if fetch_bodies:
            import base64
            def _decode(part):
                data = part.get("body", {}).get("data")
                if data:
                    return base64.urlsafe_b64decode(data.encode("utf-8")).decode("utf-8", errors="replace")
                return None

            body_text = None
            payload_part = msg.get("payload", {})
            if "parts" in payload_part:
                stack = payload_part["parts"][:]
                while stack:
                    p = stack.pop()
                    mt = p.get("mimeType", "")
                    if mt == "text/plain" and not body_text:
                        body_text = _decode(p)
                    if "parts" in p:
                        stack.extend(p["parts"])
            else:
                body_text = _decode(payload_part) or body_text

            payload["body_full"] = body_text

        batch.append(payload)
        stats["processed_messages"] += 1
        if progress_callback and stats["processed_messages"] % 25 == 0:
            progress_callback(
                {
                    "ymd": ymd,
                    "stage": "fetch_message",
                    "indexed_for_day": stats["indexed_for_day"],
                    "processed_messages": stats["processed_messages"],
                    "attempted_upserts": stats["attempted_upserts"],
                    "inserted": stats["inserted"],
                    "already_in_supabase": stats["already_in_supabase"],
                    "body_filled": stats["body_filled"],
                    "already_complete": stats["already_complete"],
                }
            )
        if len(batch) >= 100:
            batch_stats = _insert_messages_batch(supabase,batch)
            stats["attempted_upserts"] += batch_stats["attempted"]
            stats["inserted"] += batch_stats["inserted"]
            stats["already_in_supabase"] += batch_stats["existing"]
            stats["body_filled"] += batch_stats["body_filled"]
            stats["already_complete"] += batch_stats["already_complete"]
            if progress_callback:
                progress_callback(
                    {
                        "ymd": ymd,
                        "stage": "fetch_batch",
                        "indexed_for_day": stats["indexed_for_day"],
                        "processed_messages": stats["processed_messages"],
                        "attempted_upserts": stats["attempted_upserts"],
                        "inserted": stats["inserted"],
                        "already_in_supabase": stats["already_in_supabase"],
                        "body_filled": stats["body_filled"],
                        "already_complete": stats["already_complete"],
                    }
                )
            batch.clear()

    batch_stats = _insert_messages_batch(supabase,batch)
    stats["attempted_upserts"] += batch_stats["attempted"]
    stats["inserted"] += batch_stats["inserted"]
    stats["already_in_supabase"] += batch_stats["existing"]
    stats["body_filled"] += batch_stats["body_filled"]
    stats["already_complete"] += batch_stats["already_complete"]
    if progress_callback:
        progress_callback(
            {
                "ymd": ymd,
                "stage": "fetch_batch",
                "indexed_for_day": stats["indexed_for_day"],
                "processed_messages": stats["processed_messages"],
                "attempted_upserts": stats["attempted_upserts"],
                "inserted": stats["inserted"],
                "already_in_supabase": stats["already_in_supabase"],
                "body_filled": stats["body_filled"],
                "already_complete": stats["already_complete"],
            }
        )
    return stats
