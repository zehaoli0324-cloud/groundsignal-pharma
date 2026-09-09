"""Local review cues, not a de-identification detector or privacy certification.

Offsets always refer to the original Python Unicode string. A zero-match result
does not establish that a message is safe to publish. Clinical dates, ages,
diseases and laboratory values are not automatically removed. Contextual cues
can be false positives and require a human decision before any replacement.
"""

from datetime import date
import re
from typing import MutableMapping


SCANNER_VERSION = "candidate-privacy-cues/v0.1"
_PATTERNS = {
    "email": re.compile(
        r"(?<![A-Za-z0-9_.+-])[A-Za-z0-9_.+-]+@"
        r"[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+"
    ),
    "mobile": re.compile(
        r"(?<![A-Za-z0-9])(?:\+?86[ -]?)?"
        r"1[3-9][0-9][ -]?[0-9]{4}[ -]?[0-9]{4}(?![A-Za-z0-9])"
    ),
    "national_id": re.compile(r"(?<![A-Za-z0-9])[1-8][0-9]{16}[0-9Xx](?![A-Za-z0-9])"),
    "contact_handle": re.compile(
        r"(?:微信(?:号)?|微号|QQ(?:号)?|联系账号|社交账号|账号|账户)"
        r"\s*(?:[:：]|是|为)\s*(?P<value>[A-Za-z][A-Za-z0-9_-]{4,31}|[1-9][0-9]{4,11})"
        r"(?![A-Za-z0-9_-])", re.IGNORECASE
    ),
    "name": re.compile(
        r"(?:患者姓名|姓名|联系人)\s*(?:[:：]|是|为)\s*"
        r"(?P<value>[\u4e00-\u9fff]{2,4})(?=[\s，,。；;！？!?]|$)"
    ),
    "address": re.compile(
        r"(?:家庭地址|居住地址|收件地址|联系地址|住址)\s*(?:[:：]|是|为)\s*"
        r"(?P<value>[^\s，,。；;！？!?\r\n][^，,。；;！？!?\r\n]{2,79})"
    ),
    "url": re.compile(r"(?:https?://|www\.)[^\s<>\"'（），,。！？!；;]+", re.IGNORECASE),
}


def _plausible_national_id(value: str) -> bool:
    """Only structural plausibility; no resident identity or checksum claim."""
    try:
        birthday = date(int(value[6:10]), int(value[10:12]), int(value[12:14]))
    except ValueError:
        return False
    return 1800 <= birthday.year <= 2099 and value[14:17] != "000"


def scan_text(text: str) -> list[dict]:
    """Return review cues without copying potential identifiers into metadata.

    Different cues may overlap (for example a telephone used as an account).
    Reviewers must resolve overlaps before passing approved spans to redaction.
    """
    if not isinstance(text, str):
        raise ValueError("text must be a string")
    spans = []
    for kind, pattern in _PATTERNS.items():
        for match in pattern.finditer(text):
            group = "value" if "value" in pattern.groupindex else 0
            start, end = match.span(group)
            if kind == "national_id" and not _plausible_national_id(text[start:end]):
                continue
            spans.append({"kind": kind, "start": start, "end": end, "review_required": True})
    return sorted(spans, key=lambda span: (span["start"], span["end"], span["kind"]))


def redact_spans(
    text: str,
    approved_spans: list[dict],
    mapping: MutableMapping[tuple[str, str], str] | None = None,
) -> dict:
    """Replace only explicitly supplied, non-overlapping source spans.

    Calling this function does not certify human approval. The surrounding
    workflow must record that approval. Reuse a local mapping across messages
    for stable placeholders. Mapping keys contain original values: never export
    the mapping in a report, log or public repository.
    """
    if not isinstance(text, str) or not isinstance(approved_spans, list):
        raise ValueError("text must be a string and approved_spans a list")
    checked = []
    for span in approved_spans:
        if not isinstance(span, dict):
            raise ValueError("each approved span must be an object")
        start, end, kind = span.get("start"), span.get("end"), span.get("kind")
        if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(text):
            raise ValueError("span offsets must be nonempty integer bounds in the original text")
        if not isinstance(kind, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", kind):
            raise ValueError("span kind must be a lowercase identifier")
        checked.append({"start": start, "end": end, "kind": kind})
    checked.sort(key=lambda span: (span["start"], span["end"]))
    if any(right["start"] < left["end"] for left, right in zip(checked, checked[1:])):
        raise ValueError("approved spans overlap; resolve them before redaction")
    placeholders = {} if mapping is None else mapping
    pieces, replacements, cursor = [], [], 0
    for span in checked:
        start, end, kind = span["start"], span["end"], span["kind"]
        key = (kind, text[start:end])
        if key not in placeholders:
            index = 1
            while f"[REDACTED_{kind.upper()}_{index}]" in placeholders.values():
                index += 1
            placeholders[key] = f"[REDACTED_{kind.upper()}_{index}]"
        replacement = placeholders[key]
        if not isinstance(replacement, str) or not re.fullmatch(r"\[REDACTED_[A-Z0-9_]+_[1-9][0-9]*\]", replacement):
            raise ValueError("mapping values must be redaction placeholders")
        pieces.extend([text[cursor:start], replacement])
        replacements.append({**span, "replacement": replacement})
        cursor = end
    pieces.append(text[cursor:])
    return {"text": "".join(pieces), "replacements": replacements}
