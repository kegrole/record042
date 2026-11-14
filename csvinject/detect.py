"""Segment splitting and per-segment formula detection.

A field is split into segments on TAB, CR and LF (the separators are not
part of any segment).  Each segment is examined after removing leading
characters in the range U+0000..U+0020:

* empty segment                                 -> safe
* decimal/scientific number (optional sign)     -> safe
* first char in = + - @                         -> formula segment
* anything else                                 -> safe
"""

import re

SEPARATORS = "\t\r\n"
TRIGGER_CHARS = "=+-@"

_NUMBER_RE = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$")


def split_segments(value):
    """Split a field value on TAB/CR/LF, returning the list of segments."""
    segments = []
    current = []
    for ch in value:
        if ch in SEPARATORS:
            segments.append("".join(current))
            current = []
        else:
            current.append(ch)
    segments.append("".join(current))
    return segments


def strip_leading(segment):
    """Split a segment into (leading control/space chars, remaining body)."""
    index = 0
    while index < len(segment) and ord(segment[index]) <= 0x20:
        index += 1
    return segment[:index], segment[index:]


def analyze_segment(segment):
    """Return the trigger character if the segment is a formula, else None."""
    _, body = strip_leading(segment)
    if not body:
        return None
    if _NUMBER_RE.match(body):
        return None
    if body[0] in TRIGGER_CHARS:
        return body[0]
    return None


def find_formula_segments(value):
    """Return a list of (segment_index, trigger, body) per formula segment."""
    found = []
    for index, segment in enumerate(split_segments(value)):
        trigger = analyze_segment(segment)
        if trigger is not None:
            _, body = strip_leading(segment)
            found.append((index, trigger, body))
    return found
