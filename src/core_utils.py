from typing import Any, Optional, Sequence

def normalize_query_value(value: Any) -> Optional[str]:
    """Return a single string value from Streamlit query parameters."""
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        return value[0] if value else None
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return next(iter(value), None)
    return str(value)
