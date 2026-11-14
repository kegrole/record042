"""Build the analysis report for a parsed CSV table."""

from . import classify, escape


def column_letter(index):
    """Return the spreadsheet column letters for a 0-based column index."""
    letters = ""
    index += 1
    while index:
        index, remainder = divmod(index - 1, 26)
        letters = chr(ord("A") + remainder) + letters
    return letters


def build_report(rows):
    """Analyze rows (list of list of raw field strings) and return the report
    dict with keys cells, findings, summary."""
    cells = []
    findings = []
    total_formulas = 0
    injectable = 0
    for row_number, row in enumerate(rows, start=1):
        for column_index, value in enumerate(row):
            result = classify.classify_field(value)
            cell_ref = "%s%d" % (column_letter(column_index), row_number)
            is_injectable = result.formula_count > 0
            if is_injectable:
                injectable += 1
            total_formulas += result.formula_count
            cells.append(
                {
                    "cell_ref": cell_ref,
                    "raw_value": escape.escape_raw(value),
                    "verdict": "injectable" if is_injectable else "safe",
                    "formula_count": result.formula_count,
                    "kind": result.kind,
                    "trigger": (
                        "%02x" % ord(result.trigger)
                        if result.trigger is not None
                        else None
                    ),
                    "dde_token": result.dde_token,
                    "sanitized": escape.sanitize_value(value),
                }
            )
            if result.dde_token is not None:
                findings.append(
                    {
                        "rule": "dde",
                        "cell_ref": cell_ref,
                        "detail": "DDE token '%s' matched in formula segment"
                        % result.dde_token,
                    }
                )
            if result.formula_count >= 2:
                findings.append(
                    {
                        "rule": "multi_formula",
                        "cell_ref": cell_ref,
                        "detail": "%d formula segments in one cell"
                        % result.formula_count,
                    }
                )
    by_rule = {}
    for finding in findings:
        by_rule[finding["rule"]] = by_rule.get(finding["rule"], 0) + 1
    summary = {
        "cells": len(cells),
        "injectable": injectable,
        "safe": len(cells) - injectable,
        "formulas": total_formulas,
        "findings": len(findings),
        "by_rule": by_rule,
    }
    return {"cells": cells, "findings": findings, "summary": summary}
