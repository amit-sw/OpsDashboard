from src.core_utils import (
    normalize_query_value,
    parse_srt,
    transcript_segments_to_text,
)


def test_normalize_query_value_handles_list():
    assert normalize_query_value(["abc"]) == "abc"


def test_normalize_query_value_handles_string():
    assert normalize_query_value("xyz") == "xyz"


def test_normalize_query_value_handles_empty_iterable():
    assert normalize_query_value([]) is None


def test_normalize_query_value_handles_none():
    assert normalize_query_value(None) is None


def test_transcript_segments_to_text_concatenates_values():
    segments = [{"text": "Hello"}, {"text": "world"}]
    assert transcript_segments_to_text(segments) == "Hello world"


def test_transcript_segments_to_text_skips_empty():
    segments = [{"text": "Hello"}, {"text": ""}, {"missing": "value"}]
    assert transcript_segments_to_text(segments) == "Hello"


def test_parse_srt_converts_to_segments():
    srt = "1\n00:00:01,000 --> 00:00:03,000\nHello world\n\n2\n00:00:04,500 --> 00:00:05,000\nBye\n"
    segments = parse_srt(srt)
    assert len(segments) == 2
    assert segments[0]["start"] == 1.0
    assert segments[0]["duration"] == 2.0
    assert segments[0]["text"] == "Hello world"
    assert segments[1]["end"] == 5.0
