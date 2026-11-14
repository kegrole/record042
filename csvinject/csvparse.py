"""RFC 4180 CSV parsing and serialization.

The parser is a small state machine so that field values are preserved
byte-for-byte: no stripping, no type coercion.  Quoted fields may contain
commas, tabs, CR and LF; a doubled double-quote inside a quoted field is a
literal quote.  Both LF and CRLF (and a lone CR) terminate a record.
"""


def parse_csv(text):
    """Parse CSV text into a list of rows, each a list of raw field strings."""
    rows = []
    row = []
    field_chars = []
    in_quotes = False
    pending = False
    index = 0
    length = len(text)
    while index < length:
        ch = text[index]
        if in_quotes:
            if ch == '"':
                if index + 1 < length and text[index + 1] == '"':
                    field_chars.append('"')
                    index += 2
                    continue
                in_quotes = False
                index += 1
                continue
            field_chars.append(ch)
            index += 1
            continue
        if ch == '"':
            in_quotes = True
            pending = True
            index += 1
            continue
        if ch == ",":
            row.append("".join(field_chars))
            field_chars = []
            pending = True
            index += 1
            continue
        if ch == "\r":
            if index + 1 < length and text[index + 1] == "\n":
                index += 1
            row.append("".join(field_chars))
            field_chars = []
            rows.append(row)
            row = []
            pending = False
            index += 1
            continue
        if ch == "\n":
            row.append("".join(field_chars))
            field_chars = []
            rows.append(row)
            row = []
            pending = False
            index += 1
            continue
        field_chars.append(ch)
        pending = True
        index += 1
    if pending or field_chars or row:
        row.append("".join(field_chars))
        rows.append(row)
    return rows


def format_field(value):
    """Serialize one field per RFC 4180 (quote when it contains , " CR LF TAB)."""
    if any(ch in value for ch in (",", '"', "\r", "\n", "\t")):
        return '"' + value.replace('"', '""') + '"'
    return value


def dump_csv(rows):
    """Serialize rows to CSV text: comma-separated, LF-terminated, trailing LF."""
    return "".join(",".join(format_field(value) for value in row) + "\n" for row in rows)
