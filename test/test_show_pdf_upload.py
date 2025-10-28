import io
import types

import pytest

import src.show_pdf_upload as show_pdf_upload


def _streamlit_stub(recorder):
    def make(name):
        def _record(*args, **kwargs):
            recorder.setdefault(name, []).append((args, kwargs))

        return _record

    return types.SimpleNamespace(
        write=make("write"),
        warning=make("warning"),
        error=make("error"),
        info=make("info"),
        text_area=make("text_area"),
    )


def test_process_uploaded_pdf_displays_extracted_text(monkeypatch):
    recorder = {}
    fake_st = _streamlit_stub(recorder)
    monkeypatch.setattr(show_pdf_upload, "st", fake_st)
    def _fake_converter(data):
        assert data == b"pdf-bytes"
        return "sample text"

    monkeypatch.setattr(show_pdf_upload, "pdf_bytes_to_text", _fake_converter)

    uploaded = io.BytesIO(b"pdf-bytes")
    show_pdf_upload.process_uploaded_pdf(uploaded)

    text_calls = recorder.get("text_area", [])
    assert text_calls, "Expected text_area to be called with extracted text"
    label, kwargs = text_calls[0]
    assert label[0] == "Extracted PDF text"
    assert label[1] == "sample text"
    assert kwargs["height"] == 360


def test_process_uploaded_pdf_handles_empty_file(monkeypatch):
    recorder = {}
    fake_st = _streamlit_stub(recorder)
    monkeypatch.setattr(show_pdf_upload, "st", fake_st)

    def _should_not_be_called(_):
        pytest.fail("pdf_bytes_to_text should not be invoked for empty uploads")

    monkeypatch.setattr(show_pdf_upload, "pdf_bytes_to_text", _should_not_be_called)

    show_pdf_upload.process_uploaded_pdf(io.BytesIO(b""))

    warnings = recorder.get("warning", [])
    assert warnings, "Expected warning to be shown for empty upload"
