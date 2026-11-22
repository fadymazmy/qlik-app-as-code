"""The Hero KPI Strip as the build assembles it on the Executive Overview: full width under the filter strip,
and every figure it shows (its values, variances and sparklines) a master measure of the App. No tenant needed."""
import unittest

from tests.sheets import MEASURE_IDS, own

SHEET = "executive-overview"


class HeroKpiStrip(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cells, objects = own(SHEET)
        cls.cell = next(c for c in cells if c["name"] == "eo-hero-kpi-strip")
        cls.strip = objects["eo-hero-kpi-strip"]

    def test_spans_the_sheet_under_the_filter_strip(self):
        self.assertEqual((self.cell["row"], self.cell["col"], self.cell["colspan"], self.cell["rowspan"]), (2, 0, 24, 2))
        self.assertEqual(self.strip["visualization"], "claude-test-hero-kpi-strip")

    def test_every_figure_is_a_master_measure(self):
        cubes = [self.strip["qHyperCubeDef"], self.strip["sparkline"]["qHyperCubeDef"]]
        measures = [m for cube in cubes for m in cube["qMeasures"]]
        self.assertEqual(len(measures), 14)
        for m in measures:
            self.assertIn(m["qLibraryId"], MEASURE_IDS)
            self.assertEqual(m["qDef"], {})

    def test_shows_book_to_bill_from_its_master_measure(self):
        self.assertIn("m_book_to_bill_ytd", [m["qLibraryId"] for m in self.strip["qHyperCubeDef"]["qMeasures"]])
        self.assertIn("m_book_to_bill_ytd", MEASURE_IDS)


if __name__ == "__main__":
    unittest.main()
