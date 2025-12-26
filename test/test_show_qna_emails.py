import types

import src.show_qna_emails as qna_page


def test_validate_email_normalizes_and_rejects_invalid():
    assert qna_page._validate_email(" Person@Example.COM ") == "person@example.com"
    assert qna_page._validate_email("missing-at") is None
    assert qna_page._validate_email("user@localhost") is None


def test_can_manage_qna_emails_only_for_finance_or_super(monkeypatch):
    fake_st = types.SimpleNamespace(session_state={"current_user_role": "financeadmin"})
    monkeypatch.setattr(qna_page, "st", fake_st)
    assert qna_page._can_manage_qna_emails()
    fake_st.session_state["current_user_role"] = "superadmin"
    assert qna_page._can_manage_qna_emails()
    fake_st.session_state["current_user_role"] = "guest"
    assert not qna_page._can_manage_qna_emails()
