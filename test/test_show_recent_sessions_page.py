from datetime import datetime, timezone
import types

import src.show_recent_sessions_page as recent_page


def test_can_view_recent_sessions_only_for_superadmin(monkeypatch):
    fake_st = types.SimpleNamespace(session_state={"current_user_role": "superadmin"})
    monkeypatch.setattr(recent_page, "st", fake_st)
    assert recent_page._can_view_recent_sessions()
    fake_st.session_state["current_user_role"] = "admin"
    assert not recent_page._can_view_recent_sessions()


def test_get_cutoff_utc_defaults_to_24_hours():
    now = datetime(2025, 1, 2, 12, 0, tzinfo=timezone.utc)
    cutoff = recent_page._get_cutoff_utc(now)
    assert cutoff == datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
