"""The Reference calculator for a chart cell: the cell's dimension values narrow the rows, but every window still
ends on the selection's Latest Date, as in the App (docs/measures.md, Time rules)."""
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from valtera.reference import Reference
from tests.test_what_if import FILES, bn


class ChartCell(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(tmp.cleanup)
        for name, text in FILES.items():
            (Path(tmp.name) / name).write_text(text)
        cls.ref = Reference(tmp.name)

    def test_a_cell_keeps_the_selections_latest_date(self):
        # The last Sales are on 1 March; Germany's on 10 January. In a chart cell for Germany YTD still runs to
        # 1 March, so it holds all of January's Budget.
        cell = self.ref.figures({}, cell={"Country": "Germany"})
        self.assertEqual(cell["Sales YTD"].value, bn("1000"))
        self.assertEqual(cell["Budget YTD"].value, bn("1000"))

    def test_amounts_in_eur_m(self):
        f = self.ref.figures({})
        self.assertEqual(f["Sales YTD in EUR m"], (Decimal("0.0017"), "EUR m"))  # Sales YTD is EUR 1,700
        self.assertEqual(f["Sales in EUR m"], (Decimal("0.0017"), "EUR m"))
        self.assertEqual(f["Gross Margin Amount YTD in EUR m"], (Decimal("0.0005"), "EUR m"))

    def test_a_selection_moves_the_latest_date(self):
        selected = self.ref.figures({"Country": "Germany"})
        self.assertEqual(selected["Budget YTD"].value, bn(Decimal(1000) * 10 / 31))


if __name__ == "__main__":
    unittest.main()
