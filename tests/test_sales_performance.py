"""The Sales Performance Sheet as the build assembles it: every figure is a master measure, and its
objects fill the grid below the shared header without overlapping. No tenant needed."""
import unittest

from tests.sheets import MEASURE_IDS, own

SHEET = "sales-performance"


class SalesPerformanceSheet(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cells, objects = own(SHEET)
        cls.own = list(objects.values())

    def test_has_the_trend_rolling_12_months_and_variance_views(self):
        library = {m["qLibraryId"] for o in self.own for m in o.get("qHyperCubeDef", {}).get("qMeasures", [])}
        self.assertLessEqual({"m_sales_ytd", "m_budget_ytd", "m_sales_ytd_prior_year"}, library)
        self.assertIn("m_sales_rolling_12_months", library)
        self.assertLessEqual({"m_sales_ytd_vs_budget_pct", "m_sales_ytd_vs_prior_year_pct"}, library)
        dimensions = {d["qLibraryId"] for o in self.own for d in o.get("qHyperCubeDef", {}).get("qDimensions", [])}
        self.assertLessEqual({"d_business_group", "d_region", "d_channel"}, dimensions)

    def test_every_figure_is_a_master_measure(self):
        for o in self.own:
            for m in o.get("qHyperCubeDef", {}).get("qMeasures", []):
                with self.subTest(object=o["qInfo"]["qId"]):
                    self.assertIn(m.get("qLibraryId"), MEASURE_IDS)
                    self.assertFalse(m["qDef"].get("qDef"), "an inline expression next to the master measure")

    def test_a_variance_is_coloured_by_its_master_measure_in_the_theme_colours(self):
        # The Sheet file names the master measure and the theme variables; the build writes the theme's colours.
        colours = {m["qLibraryId"]: m["qAttributeExpressions"][0]["qExpression"] for o in self.own
                   for m in o.get("qHyperCubeDef", {}).get("qMeasures", []) if m.get("qAttributeExpressions")}
        self.assertEqual(colours["m_sales_ytd_vs_budget_pct"], "If([Sales YTD vs Budget %] < 0, '#ff7a7a', '#4ade9b')")
        self.assertEqual(colours["m_sales_ytd_vs_prior_year_pct"],
                         "If([Sales YTD vs Prior Year %] < 0, '#ff7a7a', '#4ade9b')")

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
        self.assertTrue(self.cells)
        self.assertEqual({c["name"] for c in self.cells}, {o["qInfo"]["qId"] for o in self.own})


if __name__ == "__main__":
    unittest.main()
