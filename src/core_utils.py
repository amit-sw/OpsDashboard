import re
from io import BytesIO
from typing import Any, Iterable, Mapping, Optional, Sequence

from markitdown import MarkItDown

def normalize_query_value(value: Any) -> Optional[str]:
    """Return a single string value from Streamlit query parameters."""
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        return value[0] if value else None
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return next(iter(value), None)
    return str(value)


def transcript_segments_to_text(segments: Iterable[Mapping[str, Any]]) -> str:
    """Join transcript segment text content into a single string."""
    parts = []
    for segment in segments:
        text = segment.get("text")
        if text:
            parts.append(text.strip())
    return " ".join(parts)


_SRT_TIMING_PATTERN = re.compile(
    r"(?P<start>\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(?P<end>\d{2}:\d{2}:\d{2},\d{3})"
)


def _parse_srt_timestamp(value: str) -> float:
    hours, minutes, rest = value.split(":")
    seconds, millis = rest.split(",")
    return (
        int(hours) * 3600
        + int(minutes) * 60
        + int(seconds)
        + int(millis) / 1000.0
    )


def parse_srt(srt_text: str) -> list[dict[str, Any]]:
    """Convert an SRT caption into a list of timestamped segments."""
    if not srt_text:
        return []
    blocks = re.split(r"\r?\n\r?\n", srt_text.strip())
    segments = []
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if len(lines) < 3:
            continue
        match = _SRT_TIMING_PATTERN.search(lines[1])
        if not match:
            continue
        start = _parse_srt_timestamp(match.group("start"))
        end = _parse_srt_timestamp(match.group("end"))
        text = " ".join(lines[2:]).strip()
        if not text:
            continue
        segments.append(
            {
                "start": start,
                "end": end,
                "duration": max(end - start, 0.0),
                "text": text,
            }
        )
    return segments


def pdf_bytes_to_text(pdf_bytes: bytes) -> str:
    """Return extracted text from raw PDF bytes."""
    if not pdf_bytes:
        return ""
    converter = MarkItDown(enable_plugins=True)
    result = converter.convert(BytesIO(pdf_bytes))
    return result.text_content or ""
