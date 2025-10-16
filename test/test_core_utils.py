from src.core_utils import normalize_query_value


def test_normalize_query_value_handles_list():
    assert normalize_query_value(["abc"]) == "abc"


def test_normalize_query_value_handles_string():
    assert normalize_query_value("xyz") == "xyz"


def test_normalize_query_value_handles_empty_iterable():
    assert normalize_query_value([]) is None


def test_normalize_query_value_handles_none():
    assert normalize_query_value(None) is None
