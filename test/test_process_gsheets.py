import pandas as pd

import utils.process_gsheets as process_gsheets


def _patch_sheet_frames(monkeypatch, persons, relations, sessions):
    def fake_get_info_gsheets(_service_account_info, _sheets_list):
        return (
            pd.DataFrame(persons),
            pd.DataFrame(relations),
            pd.DataFrame(sessions),
        )

    monkeypatch.setattr(process_gsheets, "get_info_gsheets", fake_get_info_gsheets)
    process_gsheets.get_users_students.clear()


def test_get_users_students_returns_empty_frames_when_user_not_in_sheet(monkeypatch):
    _patch_sheet_frames(
        monkeypatch,
        persons=[{"Name": "Student One", "Email": "student@example.com"}],
        relations=[],
        sessions=[],
    )

    students, topics, persons, relations, sessions = process_gsheets.get_users_students(
        "user@pyxeda.ai",
        {},
        [],
    )

    assert students.empty
    assert topics.empty
    assert isinstance(persons, pd.DataFrame)
    assert isinstance(relations, pd.DataFrame)
    assert isinstance(sessions, pd.DataFrame)


def test_get_users_students_matches_email_case_insensitively(monkeypatch):
    _patch_sheet_frames(
        monkeypatch,
        persons=[
            {"Name": "Mentor", "Email": "mentor@pyxeda.ai"},
            {"Name": "Student One", "Email": "student@example.com"},
        ],
        relations=[{"Person": "Mentor", "Student": "Student One"}],
        sessions=[{"Person": "Student One", "Topic": "Session A"}],
    )

    students, topics, _persons, _relations, _sessions = process_gsheets.get_users_students(
        "MENTOR@PYXEDA.AI",
        {},
        [],
    )

    assert students["Name"].tolist() == ["Student One"]
    assert topics["Topic"].tolist() == ["Session A"]


def test_get_users_students_handles_missing_relationship_without_error(monkeypatch):
    _patch_sheet_frames(
        monkeypatch,
        persons=[{"Name": "Mentor", "Email": "mentor@pyxeda.ai"}],
        relations=[{"Person": "Other Mentor", "Student": "Missing Student"}],
        sessions=[{"Person": "Missing Student", "Topic": "Session A"}],
    )

    students, topics, _persons, _relations, _sessions = process_gsheets.get_users_students(
        "mentor@pyxeda.ai",
        {},
        [],
    )

    assert students.empty
    assert topics.empty
