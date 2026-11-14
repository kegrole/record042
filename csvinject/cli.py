"""Command-line entry point.

Usage: python -m csvinject.cli --csv INPUT.csv --out REPORT.json --safe SAFE.csv
"""

import argparse
import json
import os
import sys

from . import csvparse, escape, report


def _ensure_parent_dir(path):
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)


def run(csv_path, out_path, safe_path):
    """Run the full pipeline and write the JSON report and sanitized CSV."""
    with open(csv_path, "r", encoding="utf-8", newline="") as handle:
        text = handle.read()
    rows = csvparse.parse_csv(text)
    report_data = report.build_report(rows)
    safe_rows = [
        [escape.sanitize_value(value) for value in row] for row in rows
    ]
    _ensure_parent_dir(out_path)
    _ensure_parent_dir(safe_path)
    with open(out_path, "w", encoding="utf-8", newline="") as handle:
        handle.write(json.dumps(report_data, ensure_ascii=False, indent=2))
        handle.write("\n")
    with open(safe_path, "w", encoding="utf-8", newline="") as handle:
        handle.write(csvparse.dump_csv(safe_rows))
    return report_data


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="csvinject",
        description="Detect spreadsheet formula injection in CSV exports.",
    )
    parser.add_argument("--csv", required=True, help="input CSV file")
    parser.add_argument("--out", required=True, help="output JSON report path")
    parser.add_argument("--safe", required=True, help="output sanitized CSV path")
    args = parser.parse_args(argv)
    report_data = run(args.csv, args.out, args.safe)
    summary = report_data["summary"]
    print(
        "cells=%d injectable=%d safe=%d formulas=%d"
        % (
            summary["cells"],
            summary["injectable"],
            summary["safe"],
            summary["formulas"],
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
