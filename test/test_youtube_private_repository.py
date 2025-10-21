from types import SimpleNamespace

from src.youtube_private_repository import YouTubeVideoRepository


class _FakeSupabase:
    def __init__(self, select_data=None, latest_data=None):
        self.select_data = select_data or []
        self.latest_data = latest_data or []
        self.upsert_payloads = []
        self.last_table = None

    class _Query:
        def __init__(self, supabase):
            self._supabase = supabase
            self._mode = None
            self._payload = None
            self._ordered = False
            self._limit = None
            self._filter_field = None
            self._filter_values = None

        def select(self, *_args):
            self._mode = "select"
            return self

        def order(self, *_args, **_kwargs):
            self._ordered = True
            return self

        def limit(self, value):
            self._limit = value
            return self

        def upsert(self, payload):
            self._mode = "upsert"
            self._payload = list(payload)
            self._supabase.upsert_payloads.append(self._payload)
            return self

        def in_(self, field, values):
            self._filter_field = field
            self._filter_values = set(values)
            return self

        def execute(self):
            if self._mode == "select":
                data = self._supabase.select_data
                if self._ordered and self._limit:
                    data = self._supabase.latest_data[: self._limit]
                if self._filter_field and self._filter_values is not None:
                    data = [row for row in data if row.get(self._filter_field) in self._filter_values]
                return SimpleNamespace(data=data)
            if self._mode == "upsert":
                return SimpleNamespace(data=self._payload)
            return SimpleNamespace(data=[])

    def table(self, name):
        self.last_table = name
        return _FakeSupabase._Query(self)


def test_existing_ids_returns_set():
    supabase = _FakeSupabase(select_data=[{"video_id": "a"}, {"video_id": "b"}])
    client = SimpleNamespace(supabase=supabase)
    repo = YouTubeVideoRepository(client, table_name="youtube_private_videos")

    assert repo.existing_ids() == {"a", "b"}
    assert supabase.last_table == "youtube_private_videos"


def test_insert_records_upserts_payload():
    supabase = _FakeSupabase()
    client = SimpleNamespace(supabase=supabase)
    repo = YouTubeVideoRepository(client)

    result = repo.insert_records([{"video_id": "x"}])

    assert result == [{"video_id": "x"}]
    assert supabase.upsert_payloads == [[{"video_id": "x"}]]


def test_insert_records_returns_empty_when_no_client():
    repo = YouTubeVideoRepository(SimpleNamespace(supabase=None))

    assert repo.insert_records([{"video_id": "x"}]) == []


def test_latest_published_at_returns_timestamp():
    supabase = _FakeSupabase(latest_data=[{"published_at": "2023-01-01T00:00:00Z"}])
    client = SimpleNamespace(supabase=supabase)
    repo = YouTubeVideoRepository(client)

    assert repo.latest_published_at() == "2023-01-01T00:00:00Z"


def test_existing_ids_for_limits_results():
    supabase = _FakeSupabase(select_data=[{"video_id": "x"}, {"video_id": "y"}])
    client = SimpleNamespace(supabase=supabase)
    repo = YouTubeVideoRepository(client)

    assert repo.existing_ids_for(["x", "z"]) == {"x"}


def test_latest_published_at_returns_none_when_empty():
    supabase = _FakeSupabase(latest_data=[])
    client = SimpleNamespace(supabase=supabase)
    repo = YouTubeVideoRepository(client)

    assert repo.latest_published_at() is None
