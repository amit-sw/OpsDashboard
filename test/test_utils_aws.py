import os

from utils.utils_aws import (
    decode_json_value,
    derive_column_names,
    extract_field_value,
    setup_env_from_dict,
)


def test_extract_field_value_handles_null_input():
    assert extract_field_value({"isNull": True, "stringValue": "ignore"}) is None


def test_extract_field_value_prefers_known_keys():
    assert extract_field_value({"doubleValue": 3.14}) == 3.14
    assert extract_field_value({"stringValue": "hello"}) == "hello"
    assert extract_field_value({"booleanValue": False}) is False


def test_extract_field_value_falls_back_to_first_value():
    assert extract_field_value({"unknown": "value"}) == "value"


def test_derive_column_names_uses_metadata_and_fallbacks():
    metadata = [{"name": "session_id"}, {"label": "timestamp"}, {}]
    assert derive_column_names(metadata) == ["session_id", "timestamp", "column_2"]


def test_decode_json_value_unwraps_double_encoded_strings():
    value = '"{\\"foo\\": 1}"'
    assert decode_json_value(value) == {"foo": 1}


def test_decode_json_value_returns_best_effort_string():
    assert decode_json_value("not-json") == "not-json"


def test_setup_env_from_dict_sets_environment(monkeypatch):
    env = {"TEST_KEY": "value"}
    monkeypatch.delenv("TEST_KEY", raising=False)
    setup_env_from_dict(env)
    assert os.environ["TEST_KEY"] == "value"
