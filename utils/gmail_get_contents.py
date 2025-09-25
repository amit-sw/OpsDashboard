
from datetime import datetime, timedelta, timezone
import time
from typing import Iterable, Tuple, List, Dict, Any, Optional

from utils.supabase_integration import SupabaseClient

def _insert_messages_batch(supabase, rows: List[Dict[str, Any]]):
    # rows: [{id, thread_id, internal_ms, headers, snippet, body_full, raw_json}]
    if not rows:
        return
    response=supabase.insert_messages_batch(rows)
    return response

def fetch_and_store_messages_for_day(supabase, service, ymd: str, fetch_bodies: bool = True):
    """
    ymd: 'YYYY-MM-DD' (UTC)
    Fetch IDs from gmail_message_index for that date, hydrate with Gmail API, and upsert into gmail_messages.
    """
    # 1) get IDs for that day
    ids = supabase.get_ids(ymd, fetch_bodies)

    batch: List[Dict[str, Any]] = []
    count = 0
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
        if len(batch) >= 100:
            _insert_messages_batch(supabase,batch)
            count += len(batch)
            batch.clear()

    _insert_messages_batch(supabase,batch)
    count += len(batch)
    return count