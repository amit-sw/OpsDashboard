from types import SimpleNamespace

from utils.supabase_integration import SupabaseClient, USED_SUPABASE_TABLES


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
