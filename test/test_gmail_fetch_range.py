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
        lambda rows: captured["rows"].extend(rows) or {"attempted": len(rows), "inserted": len(rows), "existing": 0},
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


def test_backfill_index_for_date_range_reports_duplicate_stats(monkeypatch):
    monkeypatch.setattr(
        gmail_backfill_ids,
        "_windows",
        lambda start, end, window_days: [(100, 200)],
    )
    monkeypatch.setattr(
        gmail_backfill_ids,
        "_list_ids",
        lambda service, q, cap=1000, include_spam_trash=False: ["msg-1", "msg-1", "msg-2"],
    )
    monkeypatch.setattr(
        gmail_backfill_ids,
        "_get_meta",
        lambda service, msg_id: {"threadId": f"thread-{msg_id}", "internalDate": "1704067200000"},
    )
    monkeypatch.setattr(
        gmail_backfill_ids,
        "_upsert_index_batch",
        lambda rows: {"attempted": len(rows), "inserted": 1, "existing": len(rows) - 1},
    )

    stats = gmail_backfill_ids.backfill_index_for_date_range(
        service=object(),
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 7),
    )

    assert stats == {
        "gmail_ids_found": 3,
        "unique_ids_discovered": 2,
        "duplicates_in_scan": 1,
        "attempted_upserts": 2,
        "inserted": 1,
        "already_in_supabase": 1,
    }


def test_list_ids_uses_page_token():
    captured = {"tokens": []}

    class DummyExecute:
        def __init__(self):
            self.calls = 0

        def list(self, userId=None, q=None, maxResults=None, pageToken=None, includeSpamTrash=None):
            captured["tokens"].append(pageToken)
            return self

        def execute(self):
            if len(captured["tokens"]) == 1:
                return {"messages": [{"id": "msg-1"}], "nextPageToken": "page-2"}
            return {"messages": [{"id": "msg-2"}]}

    class DummyUsers:
        def messages(self):
            return DummyExecute()

    class DummyService:
        def users(self):
            return DummyUsers()

    ids = list(gmail_backfill_ids._list_ids(DummyService(), "after:1 before:2", cap=200))
    assert ids == ["msg-1", "msg-2"]
    assert captured["tokens"] == [None, "page-2"]
