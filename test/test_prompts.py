from types import SimpleNamespace

import utils.prompts as prompts


class DummyQuery:
    def __init__(self, rows):
        self.rows = rows

    def select(self, *_):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def order(self, *_args, **_kwargs):
        return self

    def execute(self):
        return SimpleNamespace(data=self.rows)


class DummyClient:
    def __init__(self, rows):
        self.supabase = self
        self.rows = rows

    def table(self, _name):
        return DummyQuery(self.rows)


def test_load_question_prompts_returns_default_when_supabase_missing(monkeypatch):
    monkeypatch.setattr(prompts, "_build_supabase_client", lambda: None)
    assert prompts.load_question_prompts() == prompts.DEFAULT_QUESTION_PROMPTS


def test_load_question_prompts_uses_supabase_rows(monkeypatch):
    rows = [
        {"title": "Sample", "prompt": "Hello", "prompt_group": "common", "status": "active"},
    ]
    monkeypatch.setattr(prompts, "_build_supabase_client", lambda: DummyClient(rows))
    assert prompts.load_question_prompts() == rows
