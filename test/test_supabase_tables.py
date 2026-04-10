from types import SimpleNamespace

import pandas as pd

import utils.supabase_integration as supabase_module
from utils.supabase_integration import (
    USED_SUPABASE_TABLES,
    SupabaseClient,
    _mask_secret,
    format_revenue,
)


class DummyQuery:
    def __init__(self, supabase, rows):
        self.supabase = supabase
        self.rows = rows

    def select(self, _):
        return self

    def limit(self, value):
        self.supabase.last_limit = value
        return self

    def execute(self):
        return SimpleNamespace(data=self.rows)


class DummySupabase:
    def __init__(self, rows):
        self.rows = rows
        self.last_table = None
        self.last_limit = None

    def table(self, name):
        self.last_table = name
        return DummyQuery(self, self.rows)


def _build_client(rows):
    client = SupabaseClient.__new__(SupabaseClient)
    client.supabase = DummySupabase(rows)
    return client


def test_list_known_tables_returns_sorted_copy():
    tables = SupabaseClient.__new__(SupabaseClient).list_known_tables()
    assert tables == sorted(tables)
    assert set(tables) == set(USED_SUPABASE_TABLES)


def test_fetch_table_rows_hits_expected_table_and_limit():
    client = _build_client([{"id": 1}])
    rows = client.fetch_table_rows("calendar_events", limit=5)
    assert rows == [{"id": 1}]
    assert client.supabase.last_table == "calendar_events"
    assert client.supabase.last_limit == 5


def test_fetch_table_rows_rejects_unknown_tables():
    client = _build_client([{ "id": 1 }])
    rows = client.fetch_table_rows("unknown_table", limit=5)
    assert rows == []
    assert client.supabase.last_table is None


def test_fetch_table_rows_handles_supabase_errors(capfd):
    class BrokenSupabase(DummySupabase):
        def table(self, name):
            self.last_table = name

            class BrokenQuery(DummyQuery):
                def execute(self_inner):
                    raise RuntimeError("boom")

            return BrokenQuery(self, [])

    client = SupabaseClient.__new__(SupabaseClient)
    client.supabase = BrokenSupabase([])

    rows = client.fetch_table_rows("calendar_events", limit=0)
    assert rows == []
    assert client.supabase.last_limit == supabase_module.DEFAULT_TABLE_LIMIT


def test_mask_secret_obscures_sensitive_portion():
    assert _mask_secret("abcdef") == "abc***"
    assert _mask_secret("ab") == "ab***"


def test_format_revenue_returns_sorted_snippet():
    df = pd.DataFrame(
        [
            {"day": "2024-01-02", "amount": 10},
            {"day": "2024-01-03", "amount": 15},
        ]
    )
    result = format_revenue("Daily", df, "day", 1)
    assert "Daily" in result
    assert "2024-01-03 15" in result


def test_list_qna_emails_orders_by_group_and_email():
    captured = {}

    class FakeQuery:
        def __init__(self):
            self.orders = []

        def select(self, value):
            captured["select"] = value
            return self

        def order(self, column, **kwargs):
            self.orders.append(column)
            return self

        def execute(self):
            captured["orders"] = self.orders
            return SimpleNamespace(data=[{"id": 1}])

    class FakeSupabase:
        def table(self, name):
            captured["table"] = name
            return FakeQuery()

    client = SupabaseClient.__new__(SupabaseClient)
    client.supabase = FakeSupabase()

    rows = client.list_qna_emails()

    assert rows == [{"id": 1}]
    assert captured["table"] == "qna_emails"
    assert captured["select"] == "*"
    assert captured["orders"] == ["prompt_group", "email"]


def test_insert_qna_email_passes_payload(monkeypatch):
    captured = {}

    class FakeInsertQuery:
        def insert(self, payload):
            captured["payload"] = payload
            return self

        def execute(self):
            return SimpleNamespace(data=[captured["payload"]])

    class FakeSupabase:
        def table(self, name):
            captured["table"] = name
            return FakeInsertQuery()

    client = SupabaseClient.__new__(SupabaseClient)
    client.supabase = FakeSupabase()

    rows = client.insert_qna_email("ops", "person@example.com")
    assert rows == [{"prompt_group": "ops", "email": "person@example.com"}]
    assert captured["table"] == "qna_emails"


def test_update_qna_email_filters_by_id():
    captured = {"filters": []}

    class FakeUpdateQuery:
        def update(self, payload):
            captured["updates"] = payload
            return self

        def eq(self, column, value):
            captured["filters"].append((column, value))
            return self

        def execute(self):
            return SimpleNamespace(data=[captured["updates"]])

    class FakeSupabase:
        def table(self, name):
            captured["table"] = name
            return FakeUpdateQuery()

    client = SupabaseClient.__new__(SupabaseClient)
    client.supabase = FakeSupabase()

    rows = client.update_qna_email(99, {"prompt_group": "ops"})
    assert rows == [{"prompt_group": "ops"}]
    assert captured["table"] == "qna_emails"
    assert captured["filters"] == [("id", 99)]


def test_insert_gmail_index_records_upserts_on_id():
    captured = {}

    class FakeUpsertQuery:
        def upsert(self, payload, on_conflict=None):
            captured["payload"] = payload
            captured["on_conflict"] = on_conflict
            return self

        def execute(self):
            return SimpleNamespace(data=captured["payload"])

    class FakeSupabase:
        def table(self, name):
            captured["table"] = name
            return FakeUpsertQuery()

    client = SupabaseClient.__new__(SupabaseClient)
    client.supabase = FakeSupabase()

    rows = [{"id": "msg-1", "thread_id": "thread-1", "internal_ms": 1, "ymd": "2025-04-01"}]
    response = client.insert_gmail_index_records(rows)

    assert response == rows
    assert captured["table"] == "gmail_message_index"
    assert captured["payload"] == rows
    assert captured["on_conflict"] == "id"


def test_insert_messages_batch_upserts_on_id():
    captured = {}

    class FakeUpsertQuery:
        def upsert(self, payload, on_conflict=None):
            captured["payload"] = payload
            captured["on_conflict"] = on_conflict
            return self

        def execute(self):
            return SimpleNamespace(data=captured["payload"])

    class FakeSupabase:
        def table(self, name):
            captured["table"] = name
            return FakeUpsertQuery()

    client = SupabaseClient.__new__(SupabaseClient)
    client.supabase = FakeSupabase()

    rows = [{"id": "msg-1", "thread_id": "thread-1", "snippet": "hello"}]
    response = client.insert_messages_batch(rows)

    assert response.data == rows
    assert captured["table"] == "gmail_messages"
    assert captured["payload"] == rows
    assert captured["on_conflict"] == "id"


def test_get_braintree_formatted_last_n_days_only_includes_settled(monkeypatch):
    client = SupabaseClient.__new__(SupabaseClient)

    def fake_get(days):
        assert days == 5
        return [
            {
                "status": "settled",
                "created_at": "2024-01-01T00:00:00Z",
                "amount": "10",
                "customer_email": "a@example.com",
            },
            {
                "status": "pending",
                "created_at": "2024-01-02T00:00:00Z",
                "amount": "20",
                "customer_email": "b@example.com",
            },
        ]

    monkeypatch.setattr(client, "get_braintree_last_n_days", fake_get)
    rows = client.get_braintree_formatted_last_n_days(5)
    assert rows == ["Date=2024-01-01T00:00:00Z,Amount=10,Customer=a@example.com"]


def test_get_basic_braintree_info_combines_all_sections(monkeypatch):
    client = SupabaseClient.__new__(SupabaseClient)
    sample_data = [
        {
            "status": "settled",
            "created_at": "2024-01-01T12:00:00Z",
            "amount": 100,
            "customer_email": "a@example.com",
        },
        {
            "status": "settled",
            "created_at": "2024-02-15T08:00:00Z",
            "amount": 50,
            "customer_email": "b@example.com",
        },
    ]

    monkeypatch.setattr(client, "get_braintree_last_n_days", lambda _: sample_data)
    monkeypatch.setattr(supabase_module, "_import_pandas", lambda: pd)

    sections = []

    def fake_format(title, df, scol, n):
        sections.append((title, scol, n, len(df)))
        return f"{title}-{scol}-{len(df)}"

    monkeypatch.setattr(supabase_module, "format_revenue", fake_format)
    output = client.get_basic_braintree_info(num_days=7)

    assert output.startswith("All revenue amounts are in USD")
    assert "Annual Revenue" in output
    assert sections[0][0] == "Daily Revenue"
    assert sections[-1][0] == "Annual Revenue"
    assert len(sections) == 4
