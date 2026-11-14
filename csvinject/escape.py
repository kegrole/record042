"""Printable escaping of raw values and formula sanitization."""

import re

from . import detect

_SEGMENT_SPLIT_RE = re.compile(r"([\t\r\n])")


def escape_raw(value):
    """Render a raw value in printable form.

    Backslash is doubled, TAB becomes \\t, CR becomes \\r, LF becomes \\n,
    and any other control character becomes \\xNN (two lowercase hex digits).
    """
    out = []
    for ch in value:
        if ch == "\\":
            out.append("\\\\")
        elif ch == "\t":
            out.append("\\t")
        elif ch == "\r":
            out.append("\\r")
        elif ch == "\n":
            out.append("\\n")
        elif ord(ch) < 0x20 or ord(ch) == 0x7F:
            out.append("\\x%02x" % ord(ch))
        else:
            out.append(ch)
    return "".join(out)


def sanitize_value(value):
    """Insert a single quote before the trigger character of every formula
    segment, leaving all other characters (including leading whitespace and
    control chars, which stay in front of the quote) untouched."""
    parts = _SEGMENT_SPLIT_RE.split(value)
    out = []
    for part in parts:
        if len(part) == 1 and part in detect.SEPARATORS:
            out.append(part)
            continue
        if detect.analyze_segment(part) is not None:
            prefix, body = detect.strip_leading(part)
            out.append(prefix + "'" + body)
        else:
            out.append(part)
    return "".join(out)
