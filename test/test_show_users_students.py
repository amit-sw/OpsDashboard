import types

import pandas as pd

import src.show_users_students as users_students_page


def test_show_users_students_handles_empty_student_list(monkeypatch):
    calls = []
    fake_st = types.SimpleNamespace(
        session_state={"student_list": pd.DataFrame()},
        title=lambda text: calls.append(("title", text)),
        info=lambda text: calls.append(("info", text)),
    )
    monkeypatch.setattr(users_students_page, "st", fake_st)

    users_students_page.show_users_students()

    assert ("info", "No students are currently linked to your account.") in calls
