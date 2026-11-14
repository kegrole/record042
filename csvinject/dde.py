"""DDE token table and matching.

Tokens are checked case-insensitively, in table order; the first token that
appears in any formula segment wins, and the reported name is the canonical
right-hand-side name from the table.
"""

DDE_TOKENS = [
    ("cmd|", "cmd"),
    ("mshta", "mshta"),
    ("powershell", "powershell"),
    ("rundll32", "rundll32"),
    ("regsvr32", "regsvr32"),
    ("wscript", "wscript"),
    ("cscript", "cscript"),
    ("hyperlink(", "HYPERLINK"),
    ("importxml(", "IMPORTXML"),
    ("webservice(", "WEBSERVICE"),
    ("iexec(", "IEXEC"),
]


def find_dde_token(bodies):
    """Return the canonical name of the first token found in the given
    formula-segment bodies, or None."""
    lowered = [body.lower() for body in bodies]
    for pattern, name in DDE_TOKENS:
        for body in lowered:
            if pattern in body:
                return name
    return None
