"""Tests for the csvinject detector, covering the 14 acceptance criteria."""

import json
import os
import sys
import tempfile
import unittest
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from csvinject import csvparse, cli, report  # noqa: E402

TAB = "\t"
CR = "\r"
LF = "\n"
TAB = "\t"
CR = "\r"
LF = "\n"

DEMO_CSV = (
    "note,amount,url,extra\n"
    '"=1+1",+1+1,-1+1,-12.3\n'
    "@SUM(1+1)*cmd|' /C calc'!A0,"
    '"=cmd|\' /C calc\'!A0",'
    '"=HYPERLINK(""http://evil.example"",""x"")",-1.2E+3\n'
    '"' + TAB + "=1+1" + TAB + '=2+2","' + CR + "=1+1" + CR + '=2+2","=1+1",=@A1\n'
    '" =cmd|\'/C calc\'!A0","=1+1,=2+2",plain text,\n'
)

VARIANT_CSV = (
    "note,amount,url,extra\n"
    '"=1+1",+1+1,-1+1,-12.3\n'
    "@SUM(1+1)*cmd|' /C calc'!A0,"
    '"=cmd|\' /C calc\'!A0",'
    '"=HYPERLINK(""http://evil.example"",""x"")",-1.2E+3\n'
    '"' + TAB + "=1+1" + TAB + '=2+2","' + TAB + "=1+1" + TAB + '=2+2","=1+1",=@A1\n'
    '"=cmd|\'/C calc\'!A0","=1+1,=2+2",plain text,\n'
)

EXPECTED_SAFE_CSV = (
    "note,amount,url,extra\n"
    "'=1+1,'+1+1,'-1+1,-12.3\n"
    "'@SUM(1+1)*cmd|' /C calc'!A0,'=cmd|' /C calc'!A0,"
    '"\'=HYPERLINK(""http://evil.example"",""x"")",-1.2E+3\n'
    '"' + TAB + "'=1+1" + TAB + "'=2+2" + '","' + CR + "'=1+1" + CR + "'=2+2"
    + '",' + "'=1+1,'=@A1\n"
    " '=cmd|'/C calc'!A0,\"'=1+1,=2+2\",plain text,\n"
)

EXPECTED_INJECTABLE = {
    "A2": ("formula", 1, "3d", None),
    "B2": ("formula", 1, "2b", None),
    "C2": ("formula", 1, "2d", None),
    "A3": ("dde", 1, "40", "cmd"),
    "B3": ("dde", 1, "3d", "cmd"),
    "C3": ("dde", 1, "3d", "HYPERLINK"),
    "A4": ("multi_formula", 2, "3d", None),
    "B4": ("multi_formula", 2, "3d", None),
    "C4": ("formula", 1, "3d", None),
    "D4": ("formula", 1, "3d", None),
    "A5": ("dde", 1, "3d", "cmd"),
    "B5": ("formula", 1, "3d", None),
}

EXPECTED_SAFE_REFS = ["A1", "B1", "C1", "D1", "D2", "D3", "C5", "D5"]
EXPECTED_SAFE_REFS = ["A1", "B1", "C1", "D1", "D2", "D3", "C5", "D5"]


def analyze(csv_text):
    rows = csvparse.parse_csv(csv_text)
    return report.build_report(rows)


def cells_by_ref(report_data):
    return {cell["cell_ref"]: cell for cell in report_data["cells"]}


class Criterion01DemoFileTest(unittest.TestCase):
    def test_demo_file_matches_spec_bytes(self):
        demo_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "demo",
            "export.csv",
        )
        with open(demo_path, "rb") as handle:
            data = handle.read()
        self.assertEqual(data, DEMO_CSV.encode("utf-8"))
        self.assertIn(TAB, DEMO_CSV)
        self.assertIn(CR, DEMO_CSV)

    def test_parser_rfc4180_features(self):
        text = (
            '"a,b","c' + TAB + 'd","e' + CR + 'f","g' + LF + 'h",'
            '"he said ""hi"""\n'
            "plain,\r\n"
            "trailing,"
        )
        rows = csvparse.parse_csv(text)
        self.assertEqual(
            rows[0],
            ["a,b", "c" + TAB + "d", "e" + CR + "f", "g" + LF + "h", 'he said "hi"'],
        )
        self.assertEqual(rows[1], ["plain", ""])
        self.assertEqual(rows[2], ["trailing", ""])
        self.assertEqual(len(rows), 3)

    def test_parser_does_not_strip(self):
        rows = csvparse.parse_csv("  spaced  ," + TAB + "lead\n")
        self.assertEqual(rows[0][0], "  spaced  ")
        self.assertEqual(rows[0][1], TAB + "lead")
        self.assertEqual(rows[0][1], TAB + "lead")


class DemoReportTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = analyze(DEMO_CSV)
        cls.cells = cells_by_ref(cls.report)

    def test_criterion_02_verdict_counts(self):
        summary = self.report["summary"]
        self.assertEqual(summary["injectable"], 12)
        self.assertEqual(summary["safe"], 8)
        for ref in ("A1", "B1", "C1", "D1"):
            self.assertEqual(self.cells[ref]["verdict"], "safe")

    def test_criterion_03_total_formulas(self):
        self.assertEqual(self.report["summary"]["formulas"], 14)
        self.assertEqual(
            sum(cell["formula_count"] for cell in self.report["cells"]), 14
        )

    def test_criterion_04_kind_distribution(self):
        kinds = Counter(cell["kind"] for cell in self.report["cells"])
        self.assertEqual(
            kinds,
            {"safe": 8, "formula": 6, "multi_formula": 2, "dde": 4},
        )

    def test_criterion_05_injectable_cells(self):
        for ref, expected in EXPECTED_INJECTABLE.items():
            kind, count, trigger, token = expected
            cell = self.cells[ref]
            self.assertEqual(cell["verdict"], "injectable", ref)
            self.assertEqual(cell["kind"], kind, ref)
            self.assertEqual(cell["formula_count"], count, ref)
            self.assertEqual(cell["trigger"], trigger, ref)
            self.assertEqual(cell["dde_token"], token, ref)
        for ref in EXPECTED_SAFE_REFS:
            cell = self.cells[ref]
            self.assertEqual(cell["verdict"], "safe", ref)
            self.assertEqual(cell["kind"], "safe", ref)
            self.assertEqual(cell["formula_count"], 0, ref)
            self.assertIsNone(cell["trigger"], ref)
            self.assertIsNone(cell["dde_token"], ref)

    def test_criterion_06_number_exception(self):
        self.assertEqual(self.cells["D2"]["raw_value"], "-12.3")
        self.assertEqual(self.cells["D3"]["raw_value"], "-1.2E+3")
        self.assertEqual(self.cells["D2"]["verdict"], "safe")
        self.assertEqual(self.cells["D3"]["verdict"], "safe")
        self.assertEqual(self.cells["C2"]["raw_value"], "-1+1")
        self.assertEqual(self.cells["C2"]["verdict"], "injectable")
        self.assertEqual(self.cells["C2"]["kind"], "formula")

    def test_criterion_07_raw_value_escapes(self):
        self.assertEqual(self.cells["A4"]["raw_value"], "\\t=1+1\\t=2+2")
        self.assertEqual(self.cells["B4"]["raw_value"], "\\r=1+1\\r=2+2")

    def test_criterion_08_multi_formula_sanitized(self):
        a4 = self.cells["A4"]
        b4 = self.cells["B4"]
        self.assertEqual(a4["formula_count"], 2)
        self.assertEqual(b4["formula_count"], 2)
        self.assertEqual(a4["kind"], "multi_formula")
        self.assertEqual(b4["kind"], "multi_formula")
        self.assertEqual(a4["sanitized"], TAB + "'=1+1" + TAB + "'=2+2")
        self.assertEqual(b4["sanitized"], CR + "'=1+1" + CR + "'=2+2")

    def test_criterion_09_sanitized_values(self):
        self.assertEqual(self.cells["A2"]["sanitized"], "'=1+1")
        self.assertEqual(
            self.cells["C3"]["sanitized"],
            "'=HYPERLINK(\"http://evil.example\",\"x\")",
        )
        self.assertEqual(self.cells["A5"]["sanitized"], " '=cmd|'/C calc'!A0")

    def test_criterion_10_safe_csv_bytes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = os.path.join(tmpdir, "export.csv")
            out_path = os.path.join(tmpdir, "report.json")
            safe_path = os.path.join(tmpdir, "safe.csv")
            with open(csv_path, "w", encoding="utf-8", newline="") as handle:
                handle.write(DEMO_CSV)
            cli.run(csv_path, out_path, safe_path)
            with open(safe_path, "rb") as handle:
                data = handle.read()
        self.assertEqual(data, EXPECTED_SAFE_CSV.encode("utf-8"))
        self.assertEqual(data.count(b"\n"), 5)
        self.assertTrue(data.endswith(b"\n"))
        self.assertTrue(data.endswith(b"\n"))

    def test_criterion_11_report_structure(self):
        for cell in self.report["cells"]:
            self.assertEqual(
                set(cell),
                {
                    "cell_ref",
                    "raw_value",
                    "verdict",
                    "formula_count",
                    "kind",
                    "trigger",
                    "dde_token",
                    "sanitized",
                },
            )
        for finding in self.report["findings"]:
            self.assertEqual(set(finding), {"rule", "cell_ref", "detail"})
        summary = self.report["summary"]
        self.assertEqual(summary["cells"], 20)
        self.assertEqual(summary["injectable"], 12)
        self.assertEqual(summary["safe"], 8)
        self.assertEqual(summary["formulas"], 14)
        self.assertEqual(summary["findings"], 6)
        self.assertEqual(summary["by_rule"], {"dde": 4, "multi_formula": 2})

    def test_criterion_12_findings(self):
        findings = self.report["findings"]
        self.assertEqual(len(findings), 6)
        dde_refs = sorted(f["cell_ref"] for f in findings if f["rule"] == "dde")
        multi_refs = sorted(
            f["cell_ref"] for f in findings if f["rule"] == "multi_formula"
        )
        self.assertEqual(dde_refs, ["A3", "A5", "B3", "C3"])
        self.assertEqual(multi_refs, ["A4", "B4"])

    def test_criterion_13_edge_fields(self):
        d5 = self.cells["D5"]
        self.assertEqual(d5["verdict"], "safe")
        self.assertEqual(d5["raw_value"], "")
        b5 = self.cells["B5"]
        self.assertEqual(b5["formula_count"], 1)
        self.assertEqual(b5["kind"], "formula")

    def test_cell_ref_sequence(self):
        refs = [cell["cell_ref"] for cell in self.report["cells"]]
        expected = [
            "%s%d" % (column, row) for row in range(1, 6) for column in "ABCD"
        ]
        self.assertEqual(refs, expected)


class Criterion14VariantTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline = analyze(DEMO_CSV)
        cls.variant = analyze(VARIANT_CSV)
        cls.base_cells = cells_by_ref(cls.baseline)
        cls.var_cells = cells_by_ref(cls.variant)

    def test_variant_summary(self):
        summary = self.variant["summary"]
        self.assertEqual(summary["cells"], 20)
        self.assertEqual(summary["injectable"], 12)
        self.assertEqual(summary["safe"], 8)
        self.assertEqual(summary["formulas"], 14)
        self.assertEqual(summary["findings"], 6)
        self.assertEqual(summary["by_rule"], {"dde": 4, "multi_formula": 2})

    def test_variant_sanitized(self):
        self.assertEqual(self.var_cells["A5"]["sanitized"], "'=cmd|'/C calc'!A0")
        self.assertEqual(
            self.var_cells["B4"]["sanitized"], TAB + "'=1+1" + TAB + "'=2+2"
        )

    def test_variant_other_cells_unchanged(self):
        for ref, base_cell in self.base_cells.items():
            if ref in ("A5", "B4"):
                continue
            var_cell = self.var_cells[ref]
            for key in ("raw_value", "kind", "formula_count", "trigger", "dde_token"):
                self.assertEqual(
                    var_cell[key], base_cell[key], "%s.%s" % (ref, key)
                )


class DeterminismTest(unittest.TestCase):
    def test_same_input_byte_identical_output(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = os.path.join(tmpdir, "export.csv")
            with open(csv_path, "w", encoding="utf-8", newline="") as handle:
                handle.write(DEMO_CSV)
            outputs = []
            for run_index in (1, 2):
                out_path = os.path.join(tmpdir, "report%d.json" % run_index)
                safe_path = os.path.join(tmpdir, "safe%d.csv" % run_index)
                cli.run(csv_path, out_path, safe_path)
                with open(out_path, "rb") as handle:
                    report_bytes = handle.read()
                with open(safe_path, "rb") as handle:
                    safe_bytes = handle.read()
                outputs.append((report_bytes, safe_bytes))
            self.assertEqual(outputs[0], outputs[1])
            json.loads(outputs[0][0].decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
