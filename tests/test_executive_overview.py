"""The Executive Overview Sheet as the build assembles it: the objects of mock-up variant A in its grid cells,
and every figure a master measure. No tenant needed."""
import json
import unittest

from tests.sheets import MEASURE_IDS, own

SHEET = "executive-overview"

# Mock-up variant A (prototype/executive-overview/index.html, VARIANTS.A) on the 0-based 24 x 12 grid:
# {cell: (col, row, colspan, rowspan)}. Rows 0 and 1 are the shared header.
VARIANT_A = {
    "eo-hero-kpi-strip": (0, 2, 24, 2),
    "eo-sales-trend": (0, 4, 16, 4),
    "eo-sales-bridge": (16, 4, 8, 4),
    "eo-sales-by-business-group": (0, 8, 8, 4),  # one column wider than the mock-up: "Driving Intelligence" fits
    "eo-sales-by-region": (8, 8, 7, 4),
    "eo-top-customers": (15, 8, 9, 4),
}

# Text that is not a figure: the Sales Bridge reads the Latest Date's year for its labels ("2026 YTD").
LABELS = {"Year($(vLatestDate))"}


class ExecutiveOverviewSheet(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cells, cls.own = own(SHEET)
        cls.cells = {c["name"]: c for c in cells}

    def cube(self, object_id):
        return self.own[object_id]["qHyperCubeDef"]

    def test_places_the_objects_of_variant_a(self):
        placed = {name: (c["col"], c["row"], c["colspan"], c["rowspan"]) for name, c in self.cells.items()}
        self.assertEqual(placed, VARIANT_A)
        self.assertEqual(set(self.own), set(VARIANT_A))

    def test_trend_is_sales_as_bars_against_budget_and_prior_year_as_lines_by_month(self):
        trend = self.own["eo-sales-trend"]
        self.assertEqual(trend["visualization"], "combochart")
        self.assertEqual([d["qLibraryId"] for d in trend["qHyperCubeDef"]["qDimensions"]], ["d_month"])
        series = [(m["qLibraryId"], m["qDef"]["series"]["type"]) for m in trend["qHyperCubeDef"]["qMeasures"]]
        self.assertEqual(series, [("m_sales_ytd", "bar"), ("m_budget_ytd", "line"), ("m_sales_ytd_prior_year", "line")])
        self.assertNotIn("dashed", json.dumps(trend.get("components", [])), "both lines are solid")

    def test_sales_by_business_group_and_by_region_are_horizontal_bars(self):
        for object_id, dimension in [("eo-sales-by-business-group", "d_business_group"),
                                     ("eo-sales-by-region", "d_region")]:
            with self.subTest(object=object_id):
                o = self.own[object_id]
                self.assertEqual((o["visualization"], o["orientation"]), ("barchart", "horizontal"))
                self.assertTrue(o["dataPoint"]["showLabels"])
                self.assertEqual([d["qLibraryId"] for d in o["qHyperCubeDef"]["qDimensions"]], [dimension])
                self.assertEqual([m["qLibraryId"] for m in o["qHyperCubeDef"]["qMeasures"]], ["m_sales_ytd"])

    def test_top_customers_shows_sales_variance_and_gross_margin_by_customer(self):
        cube = self.cube("eo-top-customers")
        self.assertEqual(self.own["eo-top-customers"]["visualization"], "sn-table")
        self.assertEqual([d["qLibraryId"] for d in cube["qDimensions"]], ["d_customer"])
        self.assertEqual([m["qLibraryId"] for m in cube["qMeasures"]],
                         ["m_sales_ytd", "m_sales_ytd_vs_prior_year_pct", "m_gross_margin_ytd"])
        variance = cube["qMeasures"][1]
        self.assertIn("cellForegroundColor", [a["id"] for a in variance.get("qAttributeExpressions", [])])
        self.assertEqual(variance["qDef"]["qNumFormat"]["qFmt"].split(";")[0][0], "▲", "an arrow as well as a colour")
        self.assertEqual(variance["qDef"]["qNumFormat"]["qFmt"].split(";")[1][0], "▼")
        self.assertEqual(cube["qDimensions"][0]["qOtherTotalSpec"]["qOtherCounted"]["qv"], "6", "six Customers")

    def test_every_figure_is_a_master_measure(self):
        for object_id, o in self.own.items():
            cubes = [o.get("qHyperCubeDef", {}), o.get("sparkline", {}).get("qHyperCubeDef", {})]
            for m in (m for cube in cubes for m in cube.get("qMeasures", [])):
                if m["qDef"].get("qDef") in LABELS:
                    continue
                with self.subTest(object=object_id):
                    self.assertIn(m.get("qLibraryId"), MEASURE_IDS)
                    self.assertFalse(m["qDef"].get("qDef"), "an inline expression next to the master measure")


if __name__ == "__main__":
    unittest.main()
