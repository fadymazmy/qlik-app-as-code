"""The What-If Simulator's model in the Reference calculator, on three hand-written sales rows.

Expected values are worked out by hand from the model in docs/measures.md (What-If Simulator)."""
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from valtera.reference import Reference, Scenario

FILES = {
    "calendar.csv": "Date,Year,Quarter,Month\n2026-01-10,2026,Q1,Jan\n2026-02-10,2026,Q1,Feb\n2026-03-01,2026,Q1,Mar\n",
    "product_lines.csv": "Product Line ID,Product Line,Business Group\nPL01,Electric Motors,Propulsion\n",
    "customers.csv": "Customer ID,Customer\nC01,Aurelion Motors\n",
    "countries.csv": "Country ID,Country,Region\nDE,Germany,Europe\nGB,United Kingdom,Europe\n"
                     "US,United States,North America\n",
    "production_sites.csv": "Production Site ID,Production Site\nS01,Brno\n",
    "channels.csv": "Channel ID,Channel\nOE,Original Equipment\n",
    # Germany is in the euro area; the United Kingdom and the United States are not.
    "sales.csv": "Date,Product Line ID,Customer ID,Country ID,Production Site ID,Channel ID,Volume,List Price,"
                 "Net Price,Sales,Cost\n"
                 "2026-01-10,PL01,C01,DE,S01,OE,10,100.00,100.00,1000.00,800.00\n"
                 "2026-02-10,PL01,C01,US,S01,OE,5,100.00,100.00,500.00,300.00\n"
                 "2026-03-01,PL01,C01,GB,S01,OE,2,100.00,100.00,200.00,100.00\n",
    "budget.csv": "Date,Product Line ID,Country ID,Channel ID,Budget\n2026-01-01,PL01,DE,OE,1000.00\n",
    "order_intake.csv": "Date,Product Line ID,Customer ID,Country ID,Channel ID,Order Intake\n"
                        "2026-01-10,PL01,C01,DE,OE,900.00\n",
}

SIMULATED = ["Simulated Sales YTD", "Simulated Sales YTD vs Actual", "Simulated Sales YTD vs Actual %",
             "Simulated Gross Margin Amount YTD", "Simulated Gross Margin Amount YTD vs Actual",
             "Simulated Gross Margin YTD", "Simulated Gross Margin YTD vs Actual"]


def bn(eur):
    return Decimal(eur) / 10**9


class WhatIf(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(tmp.cleanup)
        for name, text in FILES.items():
            (Path(tmp.name) / name).write_text(text)
        cls.ref = Reference(tmp.name)

    def value(self, figures, name):
        return figures[name].value

    def test_no_change_gives_the_actual_figures(self):
        f = self.ref.figures({})
        self.assertEqual(self.value(f, "Simulated Sales YTD"), bn("1700"))
        self.assertEqual(self.value(f, "Simulated Gross Margin Amount YTD"), bn("500"))
        self.assertEqual(self.value(f, "Simulated Gross Margin YTD"), self.value(f, "Gross Margin YTD"))
        self.assertEqual(self.value(f, "Simulated Sales YTD vs Actual"), 0)
        self.assertEqual(self.value(f, "Simulated Sales YTD vs Actual %"), 0)
        self.assertEqual(self.value(f, "Simulated Gross Margin Amount YTD vs Actual"), 0)
        self.assertEqual(self.value(f, "Simulated Gross Margin YTD vs Actual"), 0)

    def test_price_change_moves_sales_and_margin_but_not_cost(self):
        f = self.ref.figures({}, Scenario(price=10, volume=0, exchange_rate=0))
        self.assertEqual(self.value(f, "Simulated Sales YTD"), bn("1870"))  # 1,700 x 1.1
        self.assertEqual(self.value(f, "Simulated Gross Margin Amount YTD"), bn("670"))  # cost stays 1,200
        self.assertEqual(self.value(f, "Simulated Sales YTD vs Actual"), bn("170"))

    def test_volume_change_scales_sales_and_cost(self):
        f = self.ref.figures({}, Scenario(price=0, volume=-20, exchange_rate=0))
        self.assertEqual(self.value(f, "Simulated Sales YTD"), bn("1360"))
        self.assertEqual(self.value(f, "Simulated Gross Margin Amount YTD"), bn("400"))  # 1,360 - 960
        self.assertEqual(self.value(f, "Simulated Gross Margin YTD vs Actual"), 0)  # Gross Margin % unchanged

    def test_stronger_euro_shrinks_sales_outside_the_euro_area_and_the_local_share_of_their_cost(self):
        # +25%: a foreign amount is worth 1 / 1.25 = 0.8 of its EUR value. Outside the euro area all Sales
        # and 60% of cost are in local currency, so cost there is worth 0.4 + 0.6 x 0.8 = 0.88.
        f = self.ref.figures({}, Scenario(price=0, volume=0, exchange_rate=25))
        self.assertEqual(self.value(f, "Simulated Sales YTD"), bn("1560"))  # 1,000 + 700 x 0.8
        self.assertEqual(self.value(f, "Simulated Gross Margin Amount YTD"), bn("408"))  # 1,560 - (800 + 400 x 0.88)

    def test_all_three_together(self):
        f = self.ref.figures({}, Scenario(price=10, volume=-20, exchange_rate=25))
        # Germany 1,000 x 1.1 x 0.8 = 880, cost 800 x 0.8 = 640; abroad 700 x 1.1 x 0.8 x 0.8 = 492.8,
        # cost 400 x 0.8 x 0.88 = 281.6.
        self.assertEqual(self.value(f, "Simulated Sales YTD"), bn("1372.8"))
        self.assertEqual(self.value(f, "Simulated Sales YTD vs Actual"), bn("-327.2"))
        self.assertAlmostEqual(self.value(f, "Simulated Sales YTD vs Actual %"), Decimal("1372.8") / 1700 - 1)
        self.assertEqual(self.value(f, "Simulated Gross Margin Amount YTD"), bn("451.2"))
        self.assertEqual(self.value(f, "Simulated Gross Margin Amount YTD vs Actual"), bn("-48.8"))
        self.assertAlmostEqual(self.value(f, "Simulated Gross Margin YTD"), Decimal("451.2") / Decimal("1372.8"))
        self.assertAlmostEqual(self.value(f, "Simulated Gross Margin YTD vs Actual"),
                               (Decimal("451.2") / Decimal("1372.8") - Decimal(500) / 1700) * 100)
        self.assertEqual(self.ref.figures({}, Scenario(10, -20, 25))["Simulated Gross Margin YTD vs Actual"].unit, "pp")

    def test_exchange_rate_does_not_touch_the_euro_area(self):
        f = self.ref.figures({"Country": "Germany"}, Scenario(price=0, volume=0, exchange_rate=25))
        self.assertEqual(self.value(f, "Simulated Sales YTD"), bn("1000"))
        europe = self.ref.figures({"Region": "Europe"}, Scenario(price=0, volume=0, exchange_rate=25))
        self.assertEqual(self.value(europe, "Simulated Sales YTD"), bn("1160"))  # the United Kingdom is exposed

    def test_simulated_figures_are_ytd_and_keep_the_other_measures_unchanged(self):
        base, scenario = self.ref.figures({}), self.ref.figures({}, Scenario(10, -20, 25))
        self.assertEqual(sorted(set(scenario) - set(base)), [])
        self.assertTrue(set(SIMULATED) <= set(base))
        for name in set(base) - set(SIMULATED):
            self.assertEqual(scenario[name], base[name], name)
        # Selecting a month moves the Latest Date, so YTD ends there.
        jan = self.ref.figures({"Month": "Jan"}, Scenario(10, 0, 0))
        self.assertEqual(self.value(jan, "Simulated Sales YTD"), bn("1100"))


if __name__ == "__main__":
    unittest.main()
