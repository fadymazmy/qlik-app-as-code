"""Test point 1: the generated CSV files."""
import csv
import filecmp
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from valtera import data
from valtera.reference import Reference

FILES = ["budget.csv", "calendar.csv", "channels.csv", "countries.csv", "customers.csv",
         "order_intake.csv", "product_lines.csv", "production_sites.csv", "sales.csv"]

# fact file -> {key column: (dimension file, key column)}
REFERENCES = {
    "sales.csv": {"Date": ("calendar.csv", "Date"),
                  "Product Line ID": ("product_lines.csv", "Product Line ID"),
                  "Customer ID": ("customers.csv", "Customer ID"),
                  "Country ID": ("countries.csv", "Country ID"),
                  "Production Site ID": ("production_sites.csv", "Production Site ID"),
                  "Channel ID": ("channels.csv", "Channel ID")},
    "budget.csv": {"Date": ("calendar.csv", "Date"),
                   "Product Line ID": ("product_lines.csv", "Product Line ID"),
                   "Country ID": ("countries.csv", "Country ID"),
                   "Channel ID": ("channels.csv", "Channel ID")},
    "order_intake.csv": {"Date": ("calendar.csv", "Date"),
                         "Product Line ID": ("product_lines.csv", "Product Line ID"),
                         "Customer ID": ("customers.csv", "Customer ID"),
                         "Country ID": ("countries.csv", "Country ID"),
                         "Channel ID": ("channels.csv", "Channel ID")},
}

# Words from the names of real carmakers, their brands and automotive suppliers: none may appear in a
# Customer name. ("Motors", "Automotive" and the like are generic and allowed.)
REAL_COMPANY_WORDS = set("""
abarth acura aiways aito alfa alpine aptiv aston audi avatr baic bentley bmw borgwarner bosch bugatti buick
byd cadillac changan chery chevrolet chrysler citroen continental cupra dacia daf daimler denso denza dodge
dongfeng exeed faurecia faw ferrari fiat ford forvia gac geely genesis gm gmc haval hella hino honda hongqi
hyundai infiniti isuzu iveco jaguar jeep jetour kia koenigsegg lada lamborghini lancia land lear
leapmotor lexus lincoln lotus lucid lynk magna mahindra man marelli maserati maybach mazda mclaren mercedes
mg mini mitsubishi navistar neta nio nissan omoda opel ora paccar pagani perodua peugeot polestar porsche
proton ram renault rivian rover saic scania seat seres skoda smart ssangyong stellantis subaru suzuki tata
tesla togg toyota vauxhall vinfast volkswagen volvo vw wuling xpeng zeekr zf
""".split())


def read(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class GeneratedFiles(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def generate(self, name, seed, size=2000):
        out = self.root / name
        data.generate(seed=seed, size=size, out_dir=out)
        return out

    def test_same_seed_gives_identical_files(self):
        a, b = self.generate("a", seed=7), self.generate("b", seed=7)
        files = sorted(p.name for p in a.iterdir())
        self.assertEqual(files, FILES)
        match, mismatch, errors = filecmp.cmpfiles(a, b, files, shallow=False)
        self.assertEqual((mismatch, errors), ([], []))

    def test_other_seed_gives_other_sales(self):
        a, b = self.generate("a", seed=7), self.generate("b", seed=8)
        self.assertNotEqual((a / "sales.csv").read_bytes(), (b / "sales.csv").read_bytes())

    def test_size_is_the_number_of_sales_rows(self):
        self.assertEqual(len(read(self.generate("a", seed=1, size=123) / "sales.csv")), 123)

    def test_every_fact_row_references_existing_dimension_rows(self):
        out = self.generate("a", seed=3)
        for fact, refs in REFERENCES.items():
            rows = read(out / fact)
            self.assertTrue(rows, fact)
            for column, (dim, key) in refs.items():
                keys = [r[key] for r in read(out / dim)]
                self.assertEqual(len(keys), len(set(keys)), f"{dim}: {key} is not unique")
                missing = {r[column] for r in rows} - set(keys)
                self.assertEqual(missing, set(), f"{fact}.{column} not in {dim}")

    def test_product_lines_sit_in_the_three_business_groups(self):
        lines = read(self.generate("a", seed=3) / "product_lines.csv")
        self.assertEqual({r["Business Group"] for r in lines},
                         {"Propulsion", "Driving Intelligence", "Lighting"})

    def test_calendar_covers_three_years_at_daily_grain(self):
        cal = read(self.generate("a", seed=3) / "calendar.csv")
        self.assertEqual({r["Year"] for r in cal}, {"2024", "2025", "2026"})
        self.assertEqual(len(cal), len({r["Date"] for r in cal}))
        self.assertEqual(len(cal), 366 + 365 + 365)

    def test_customer_names_are_fictional(self):
        customers = [r["Customer"] for r in read(self.generate("a", seed=3) / "customers.csv")]
        self.assertGreaterEqual(len(customers), 20)
        self.assertEqual(len(customers), len(set(customers)))
        for name in customers:
            words = {w.lower() for w in name.replace("-", " ").split()}
            with self.subTest(customer=name):
                self.assertEqual(words & REAL_COMPANY_WORDS, set())

    def test_budget_is_at_monthly_grain(self):
        budget = read(self.generate("a", seed=3) / "budget.csv")
        self.assertEqual({r["Date"][8:] for r in budget}, {"01"})


class PlantedStories(unittest.TestCase):
    """Each Planted Story, measured on the data set the build ships (its seed and size)."""

    @classmethod
    def setUpClass(cls):
        from valtera.build import SEED, SIZE
        tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(tmp.cleanup)
        data.generate(seed=SEED, size=SIZE, out_dir=tmp.name)
        out = Path(tmp.name)
        group = {r["Product Line ID"]: r["Business Group"] for r in read(out / "product_lines.csv")}
        region = {r["Country ID"]: r["Region"] for r in read(out / "countries.csv")}
        cls.customer = {r["Customer ID"]: r["Customer"] for r in read(out / "customers.csv")}
        cls.sales = [{"year": r["Date"][:4], "group": group[r["Product Line ID"]], "region": region[r["Country ID"]],
                      "customer": r["Customer ID"], "channel": r["Channel ID"],
                      "sales": float(r["Sales"]), "cost": float(r["Cost"])} for r in read(out / "sales.csv")]
        cls.budget = [{"year": r["Date"][:4], "channel": r["Channel ID"], "budget": float(r["Budget"])}
                      for r in read(out / "budget.csv")]
        cls.lighting_asia = Reference(out).figures({"Business Group": "Lighting", "Region": "Asia"})
        cls.lines = [{"year": r["Date"][:4], "group": group[r["Product Line ID"]], "region": region[r["Country ID"]],
                      "cell": (r["Product Line ID"], r["Customer ID"], r["Channel ID"]), "volume": int(r["Volume"]),
                      "sales": float(r["Sales"]), "cost": float(r["Cost"])} for r in read(out / "sales.csv")]

    def total(self, field="sales", rows=None, **where):
        return sum(r[field] for r in (rows or self.sales) if all(r[k] == v for k, v in where.items()))

    def gross_margin(self, **where):
        sales = self.total(**where)
        return (sales - self.total("cost", **where)) / sales

    def test_lighting_loses_gross_margin_in_asia_over_the_last_12_months_while_sales_grow(self):
        # The data ends on 2026-12-31, so the last 12 months are 2026 and the 12 before are 2025.
        now, before = dict(group="Lighting", region="Asia", year="2026"), dict(group="Lighting", region="Asia", year="2025")
        self.assertGreater(self.total(**now), 1.10 * self.total(**before))
        self.assertLess(self.gross_margin(**now), self.gross_margin(**before) - 0.05)
        for other in ["Europe", "North America", "South America"]:
            with self.subTest(region=other):
                self.assertAlmostEqual(self.gross_margin(group="Lighting", region=other, year="2026"),
                                       self.gross_margin(group="Lighting", region=other, year="2025"), delta=0.01)

    def unit_index(self, field, asia):
        """This year's Lighting `field` (sales or cost) per unit against last year's, inside or outside Asia:
        2026 amounts over 2026 Volume at each cell's 2025 amount per unit (cell: Product Line, Customer, Channel)."""
        cells = {}
        for r in self.lines:
            if r["group"] == "Lighting" and (r["region"] == "Asia") == asia and r["year"] in ("2025", "2026"):
                c = cells.setdefault(r["cell"], {"2025": [0, 0], "2026": [0, 0]})[r["year"]]
                c[0] += r[field]
                c[1] += r["volume"]
        both = [c for c in cells.values() if c["2025"][1] and c["2026"][1]]
        return sum(c["2026"][0] for c in both) / sum(c["2026"][1] * c["2025"][0] / c["2025"][1] for c in both)

    def test_lighting_in_asia_loses_its_margin_to_price_erosion(self):
        # Net price per unit falls in Asia against Lighting elsewhere, cost per unit does not rise with it,
        # and the Sales Bridge shows a clearly negative Price Effect next to a larger positive Volume Effect.
        self.assertLess(self.unit_index("sales", asia=True), self.unit_index("sales", asia=False) - 0.05)
        self.assertLess(self.unit_index("cost", asia=True), self.unit_index("cost", asia=False) + 0.01)
        f = self.lighting_asia
        price, volume = f["Price Effect YTD vs Prior Year"].value, f["Volume Effect YTD vs Prior Year"].value
        self.assertLess(price, -Decimal("0.05") * f["Sales YTD Prior Year"].value)
        self.assertGreater(volume, -price)
        self.assertGreater(f["Sales YTD vs Prior Year"].value, 0)

    def propulsion_shares(self, year):
        propulsion = self.total(group="Propulsion", year=year)
        shares = {c: self.total(group="Propulsion", year=year, customer=c) / propulsion for c in self.customer}
        return sorted(shares.items(), key=lambda kv: -kv[1])

    def test_company_sales_grow_about_5_percent_a_year(self):
        for before, now in (("2024", "2025"), ("2025", "2026")):
            with self.subTest(year=now):
                growth = self.total(year=now) / self.total(year=before) - 1
                self.assertGreaterEqual(growth, 0.03)
                self.assertLessEqual(growth, 0.07)

    def test_budget_attainment_is_near_100_percent(self):
        for year in ["2024", "2025", "2026"]:
            with self.subTest(year=year):
                attainment = self.total(year=year) / self.total(rows=self.budget, field="budget", year=year)
                self.assertAlmostEqual(attainment, 1, delta=0.05)

    def test_kestova_motors_grows_from_about_15_to_about_30_percent_of_propulsion_sales(self):
        (leader, share), (_, runner_up) = self.propulsion_shares("2026")[:2]
        self.assertEqual(self.customer[leader], "Kestova Motors")
        self.assertGreaterEqual(share, 0.27)
        self.assertLessEqual(share, 0.33)
        self.assertGreaterEqual(share, 3 * runner_up)
        first_year = dict(self.propulsion_shares("2024"))[leader]
        self.assertGreaterEqual(first_year, 0.12)
        self.assertLessEqual(first_year, 0.18)

    def test_kestova_motors_takes_its_share_from_the_other_propulsion_customers(self):
        # The other Customers' Propulsion Sales shrink about 3% a year, so Kestova's growth is share taken
        # from them rather than an addition to the total; each Customer still moves at its own rate.
        leader = self.propulsion_shares("2026")[0][0]
        others = [c for c in self.customer if c != leader]
        propulsion = {y: sum(self.total(group="Propulsion", year=y, customer=c) for c in others)
                      for y in ("2024", "2025", "2026")}
        for before, now in (("2024", "2025"), ("2025", "2026")):
            with self.subTest(year=now):
                growth = propulsion[now] / propulsion[before] - 1
                self.assertGreaterEqual(growth, -0.045)
                self.assertLessEqual(growth, -0.015)
        growth = [self.total(year="2026", customer=c) / self.total(year="2025", customer=c) - 1 for c in others]
        self.assertGreater(max(growth) - min(growth), 0.04, "each Customer at its own rate")

    def test_aftermarket_is_small_has_twice_the_gross_margin_and_is_ahead_of_budget(self):
        self.assertLess(self.total(channel="AM"), 0.15 * self.total())
        self.assertAlmostEqual(self.gross_margin(channel="AM") / self.gross_margin(channel="OE"), 2, delta=0.2)
        for year in ["2024", "2025", "2026"]:
            with self.subTest(year=year):
                budget = dict(rows=self.budget, field="budget", year=year)
                self.assertGreater(self.total(channel="AM", year=year), 1.03 * self.total(channel="AM", **budget))
                self.assertLess(self.total(channel="OE", year=year), self.total(channel="OE", **budget))


if __name__ == "__main__":
    unittest.main()
