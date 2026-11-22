"""The Product Line and Margin Sheet as the build assembles it: the views the ticket asks for, every figure a
master measure, and objects that fill the grid below the shared header without overlapping. No tenant needed;
the numbers themselves are checked on the reloaded App by verify (check_margin_sheet)."""
import json
import unittest

from tests.sheets import MEASURE_IDS, own
from valtera import verify
from valtera.paths import APP_DIR

SHEET = "product-line-and-margin"


class ProductLineAndMarginSheet(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cells, cls.own = own(SHEET)

    def cube(self, object_id):
        cube = self.own[object_id]["qHyperCubeDef"]
        return ([d["qLibraryId"] for d in cube.get("qDimensions", [])],
                [m.get("qLibraryId") for m in cube["qMeasures"]])

    def test_gross_margin_by_product_line_and_channel_amount_and_percentage_against_prior_year(self):
        dimensions, measures = self.cube("plm-product-channel")
        self.assertIn("d_product_line", dimensions)
        self.assertIn("d_channel", dimensions)
        self.assertLessEqual({"m_gross_margin_amount_ytd_in_eur_m", "m_gross_margin_ytd", "m_gross_margin_ytd_vs_prior_year"},
                             set(measures))

    def test_margin_change_by_region_shows_without_a_selection(self):
        dimensions, measures = self.cube("plm-margin-change")
        self.assertIn("d_region", dimensions)
        self.assertEqual(measures, ["m_gross_margin_ytd_vs_prior_year"])

    def test_gross_margin_trend_by_month_beside_sales(self):
        dimensions, measures = self.cube("plm-trend")
        self.assertEqual(dimensions, ["d_year_month"])
        self.assertLessEqual({"m_gross_margin", "m_sales_in_eur_m"}, set(measures))

    def test_sales_bridge_with_a_business_group_selector(self):
        self.assertEqual(self.own["plm-bridge"]["visualization"], "claude-test-sales-bridge")
        fields = [o["qListObjectDef"]["qDef"]["qFieldDefs"] for o in self.own.values() if "qListObjectDef" in o]
        self.assertIn(["Business Group"], fields)

    def test_amounts_are_in_eur_m(self):
        # Product Lines are small: in EUR bn their amounts read €0.01 bn, so this Sheet shows EUR m throughout.
        formats = {m["qInfo"]["qId"]: m["qMeasure"].get("qNumFormat", {}).get("qFmt", "")
                   for m in json.loads((APP_DIR / "measures.json").read_text())}
        for object_id, o in self.own.items():
            for m in o.get("qHyperCubeDef", {}).get("qMeasures", []):
                if m.get("qLibraryId"):
                    with self.subTest(object=object_id, measure=m["qLibraryId"]):
                        self.assertNotIn(" bn", formats[m["qLibraryId"]])

    def test_verify_reads_the_objects_the_sheet_has(self):
        self.assertLessEqual(set(verify.MARGIN_OBJECTS), set(self.own))

    def test_every_figure_is_a_master_measure(self):
        for object_id, o in self.own.items():
            for m in o.get("qHyperCubeDef", {}).get("qMeasures", []):
                if object_id == "plm-bridge" and not m.get("qLibraryId"):
                    continue  # the bridge's year label, Year($(vLatestDate)), as on the Executive Overview
                with self.subTest(object=object_id):
                    self.assertIn(m.get("qLibraryId"), MEASURE_IDS)
                    self.assertFalse(m["qDef"].get("qDef"), "an inline expression next to the master measure")

    def test_objects_fill_rows_2_to_11_without_overlapping(self):
        taken = {}
        for c in self.cells:
            for row in range(c["row"], c["row"] + c["rowspan"]):
                for col in range(c["col"], c["col"] + c["colspan"]):
                    self.assertTrue(2 <= row <= 11 and 0 <= col <= 23, f"{c['name']} outside the grid")
                    self.assertNotIn((row, col), taken, f"{c['name']} overlaps {taken.get((row, col))}")
                    taken[(row, col)] = c["name"]
        self.assertEqual(len(taken), 10 * 24, "the Sheet leaves part of its grid empty")

    def test_every_cell_has_its_object(self):
        tops = {c["name"] for c in self.cells}
        self.assertTrue(tops)
        self.assertLessEqual(tops, set(self.own))


if __name__ == "__main__":
    unittest.main()
