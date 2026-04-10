from datetime import date

from src.show_gmail_fetch_control import _iter_ymd_range
from utils import gmail_backfill_ids


def test_iter_ymd_range_is_inclusive():
    values = list(_iter_ymd_range(date(2026, 1, 1), date(2026, 1, 3)))
    assert values == ["2026-01-01", "2026-01-02", "2026-01-03"]


def test_backfill_index_for_date_range_uses_requested_window(monkeypatch):
    captured = {"queries": [], "rows": []}

    monkeypatch.setattr(
        gmail_backfill_ids,
        "_windows",
        lambda start, end, window_days: [(100, 200)],
    )
    monkeypatch.setattr(
        gmail_backfill_ids,
        "_list_ids",
        lambda service, q, cap=1000, include_spam_trash=False: captured["queries"].append((q, include_spam_trash)) or ["msg-1"],
    )
    monkeypatch.setattr(
        gmail_backfill_ids,
        "_get_meta",
        lambda service, msg_id: {"threadId": "thread-1", "internalDate": "1704067200000"},
    )
    monkeypatch.setattr(
        gmail_backfill_ids,
        "_upsert_index_batch",
        lambda rows: captured["rows"].extend(rows),
    )

    gmail_backfill_ids.backfill_index_for_date_range(
        service=object(),
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 7),
        include_spam_trash=True,
    )

    assert captured["queries"] == [("after:100 before:200", True)]
    assert captured["rows"] == [
        {
            "id": "msg-1",
            "thread_id": "thread-1",
            "internal_ms": 1704067200000,
            "ymd": "2024-01-01",
        }
    ]
