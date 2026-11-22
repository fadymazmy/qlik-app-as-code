"""Budget in the Reference calculator: it has no Customer and no Production Site, so a selection in either
leaves every Budget figure undefined (null, shown as a dash), never 0 or Sales against 0."""
import tempfile
import unittest
from pathlib import Path

from valtera.reference import Reference
from tests.test_what_if import FILES, bn

BUDGET_FIGURES = ["Budget", "Budget Attainment", "Budget YTD", "Budget Attainment YTD", "Budget YTD Prior Year",
                  "Budget Attainment YTD Prior Year", "Budget Attainment YTD vs Prior Year", "Sales YTD vs Budget",
                  "Sales YTD vs Budget %", "Budget Rolling 12 Months", "Budget Attainment Rolling 12 Months",
                  "Sales Rolling 12 Months vs Budget", "Sales Rolling 12 Months vs Budget %"]


class BudgetLevel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(tmp.cleanup)
        for name, text in FILES.items():
            (Path(tmp.name) / name).write_text(text)
        cls.ref = Reference(tmp.name)

    def test_budget_is_defined_without_a_customer_or_production_site(self):
        for selection in [{}, {"Channel": "Original Equipment"}]:
            with self.subTest(selection=selection):
                f = self.ref.figures(selection)
                self.assertEqual(f["Budget YTD"].value, bn("1000"))  # January's Budget, all inside YTD
                self.assertEqual(f["Sales YTD vs Budget"].value, bn("700"))  # Sales YTD 1,700

    def test_no_budget_figure_under_a_customer_or_production_site(self):
        for selection in [{"Customer": "Aurelion Motors"}, {"Production Site": "Brno"},
                          {"Country": "Germany", "Customer": "Aurelion Motors"}]:
            f = self.ref.figures(selection)
            self.assertIsNotNone(f["Sales YTD"].value)
            for name in BUDGET_FIGURES:
                with self.subTest(selection=selection, figure=name):
                    self.assertIsNone(f[name].value)


if __name__ == "__main__":
    unittest.main()
