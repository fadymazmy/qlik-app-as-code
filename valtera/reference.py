"""Reference calculator: every master measure computed straight from the CSV files.

It is the independent source of truth for verification and shares no code with the load script
or the Qlik expressions. The rules it follows (the Latest Date, the windows, Budget spread over days)
are written down in docs/measures.md; this file implements them a second time, in Python.
"""
import calendar
import csv
from collections import namedtuple
from datetime import date, timedelta
from decimal import Decimal
from fractions import Fraction
from functools import lru_cache
from pathlib import Path

# A figure in the unit the App holds it in: "EUR bn" for amounts (17.62 = €17.62 bn) or "EUR m" (17,620.0 =
# €17,620.0 m) for the amounts that also exist in EUR m, "ratio" for percentages
# and relative changes (0.25 = 25%), "pp" for differences of percentages (-0.4 = -0.4 percentage points).
Figure = namedtuple("Figure", "value unit")
Totals = namedtuple("Totals", "sales cost orders budget")  # in EUR, for one window


def _rows(data_dir, name):
    with open(Path(data_dir) / name, newline="", encoding="utf-8") as f:
        yield from csv.DictReader(f)


def row_counts(data_dir):
    """The number of data rows in each CSV file: {file name: rows}."""
    return {p.name: sum(1 for _ in _rows(data_dir, p.name)) for p in sorted(Path(data_dir).glob("*.csv"))}


CALENDAR_FIELDS = ["Date", "Year", "Quarter", "Month", "Year Month"]
# Budget has no Customer and no Production Site: under a selection in either, every Budget figure is null.
NO_BUDGET_FIELDS = ["Customer", "Production Site"]


@lru_cache(maxsize=None)
def _calendar_values(d):
    """The calendar fields of a day, as the App's Calendar shows them."""
    return {"Date": d.isoformat(), "Year": str(d.year), "Quarter": f"Q{(d.month - 1) // 3 + 1}",
            "Month": d.strftime("%b"), "Year Month": d.strftime("%Y-%b")}


def _kept(rows, selection):
    """The fact rows (date, attributes, ...) with every value `selection` {field: value} selects outside the
    calendar fields; a row without a selected field (Budget has no Customer) is not kept."""
    return [r for r in rows if all(r[1].get(f) == v for f, v in selection.items() if f not in CALENDAR_FIELDS)]


def _on_selected_days(rows, selection):
    """The fact rows dated on a day with every value `selection` selects in the calendar fields."""
    calendar_part = {f: v for f, v in selection.items() if f in CALENDAR_FIELDS}
    return [r for r in rows if all(_calendar_values(r[0])[f] == v for f, v in calendar_part.items())]


def _eur(cents):
    return Decimal(sum(cents)) / 100


def _decimal(fraction):
    return Decimal(fraction.numerator) / fraction.denominator


def _ratio(a, b):
    """a / b, or None (a null in the App) when b is 0."""
    return a / b if b else None


def _growth(a, b):
    """The change from b to a as a ratio (0.05 = +5%), or None when b is 0."""
    r = _ratio(a, b)
    return None if r is None else r - 1


def _bn(eur):
    """An amount as the App holds it: in EUR billions."""
    return Figure(eur / 10**9, "EUR bn")


# Amounts that also exist in EUR m, as `<name> in EUR m` (docs/measures.md, Display).
IN_EUR_M = ["Sales",
            "Sales YTD",
            "Sales YTD Prior Year",
            "Gross Margin Amount YTD",
            "Volume Effect YTD vs Prior Year",
            "Price Effect YTD vs Prior Year",
            "Mix Effect YTD vs Prior Year"]


def _pp(a, b):
    """The difference of two ratios in percentage points (0.20 against 0.21 is -1), or None."""
    return Figure(None if a is None or b is None else (a - b) * 100, "pp")


def _a_year_earlier(d, years=1):
    """The same day `years` years earlier; 29 February becomes 28 February."""
    try:
        return d.replace(year=d.year - years)
    except ValueError:
        return d.replace(year=d.year - years, day=28)


class Reference:
    """The CSV files of one build, loaded once; `figures(selection)` gives every master measure."""

    def __init__(self, data_dir):
        def lookup(file, key):
            return {r[key]: r for r in _rows(data_dir, file)}
        product_lines = lookup("product_lines.csv", "Product Line ID")
        customers = lookup("customers.csv", "Customer ID")
        countries = lookup("countries.csv", "Country ID")
        sites = lookup("production_sites.csv", "Production Site ID")
        channels = lookup("channels.csv", "Channel ID")
        self.calendar = list(_rows(data_dir, "calendar.csv"))
        self.values = {"Product Line": {r["Product Line"] for r in product_lines.values()},
                       "Business Group": {r["Business Group"] for r in product_lines.values()},
                       "Customer": {r["Customer"] for r in customers.values()},
                       "Country": {r["Country"] for r in countries.values()},
                       "Region": {r["Region"] for r in countries.values()},
                       "Production Site": {r["Production Site"] for r in sites.values()},
                       "Channel": {r["Channel"] for r in channels.values()}}

        def attributes(r):
            """The dimension values a fact row is associated with (only those it has keys for)."""
            out = {}
            if r.get("Product Line ID"):
                pl = product_lines[r["Product Line ID"]]
                out.update({"Product Line": pl["Product Line"], "Business Group": pl["Business Group"]})
            if r.get("Customer ID"):
                out["Customer"] = customers[r["Customer ID"]]["Customer"]
            if r.get("Country ID"):
                c = countries[r["Country ID"]]
                out.update({"Country": c["Country"], "Region": c["Region"]})
            if r.get("Production Site ID"):
                out["Production Site"] = sites[r["Production Site ID"]]["Production Site"]
            if r.get("Channel ID"):
                out["Channel"] = channels[r["Channel ID"]]["Channel"]
            return out

        # (date, attributes, amounts in cents or exact decimals); the sales rows also carry their Volume.
        self.sales = [(date.fromisoformat(r["Date"]), attributes(r), int(r["Sales"].replace(".", "")),
                       int(r["Cost"].replace(".", "")), int(r["Volume"])) for r in _rows(data_dir, "sales.csv")]
        self.budget = [(date.fromisoformat(r["Date"]), attributes(r), Fraction(r["Budget"]))
                       for r in _rows(data_dir, "budget.csv")]
        self.orders = [(date.fromisoformat(r["Date"]), attributes(r), int(r["Order Intake"].replace(".", "")))
                       for r in _rows(data_dir, "order_intake.csv")]

    def dimension_counts(self):
        """{master dimension name: number of distinct values in the CSV files}."""
        days = [date.fromisoformat(r["Date"]) for r in self.calendar]
        counts = {field: len({_calendar_values(d)[field] for d in days}) for field in CALENDAR_FIELDS}
        counts.update({field: len(values) for field, values in self.values.items()})
        return counts

    def figures(self, selection, scenario=None, cell=None):
        """{master measure name: Figure} for a selection {field: value}, the simulated measures under a What-If
        `scenario` (no change when None), and optionally in one `cell` {field: value} of a chart.

        A fact row belongs to the selection when it has every selected value; a row without a selected field
        (Budget has no Customer) does not. The windowed measures replace the selection in the calendar fields
        by their own days and keep the rest. A chart cell narrows the rows like a selection, but its values
        outside the calendar fields do not move the Latest Date: every cell's window ends on the selection's."""
        narrowing, selection = selection, {**selection, **(cell or {})}
        sales, budget, orders = (_kept(rows, selection) for rows in (self.sales, self.budget, self.orders))
        selected_sales = _on_selected_days(sales, selection)
        # The Latest Date: the last day with Sales in the selection; the cell narrows the rows but not their days.
        latest = max((r[0] for r in _on_selected_days(_kept(self.sales, narrowing), selection)), default=None)

        def window(first, last):
            """Sales, cost, Order Intake and Budget in EUR for the days first..last (both included);
            each month's Budget spread evenly over the days of its month."""
            b = Fraction(0)
            for d, _, amount in budget:
                month_last = d.replace(day=calendar.monthrange(d.year, d.month)[1])
                days = (min(month_last, last) - max(d, first)).days + 1
                if days > 0:
                    b += amount * days / month_last.day
            return Totals(_eur(r[2] for r in sales if first <= r[0] <= last),
                          _eur(r[3] for r in sales if first <= r[0] <= last),
                          _eur(r[2] for r in orders if first <= r[0] <= last),
                          _decimal(b))

        # Without a window every selection applies, the calendar fields included, and Budget is in whole months.
        totals = {"": Totals(_eur(r[2] for r in selected_sales), _eur(r[3] for r in selected_sales),
                             _eur(r[2] for r in _on_selected_days(orders, selection)),
                             _decimal(sum((r[2] for r in _on_selected_days(budget, selection)), Fraction(0))))}
        if latest:
            year_earlier = _a_year_earlier(latest)
            totals[" YTD"] = window(date(latest.year, 1, 1), latest)
            totals[" YTD Prior Year"] = window(date(latest.year - 1, 1, 1), year_earlier)
            totals[" Rolling 12 Months"] = window(year_earlier + timedelta(days=1), latest)
            totals[" Rolling 12 Months Prior Year"] = window(_a_year_earlier(latest, 2) + timedelta(days=1),
                                                             year_earlier)

        out = {}
        for w, t in totals.items():
            out[f"Sales{w}"] = _bn(t.sales)
            out[f"Gross Margin Amount{w}"] = _bn(t.sales - t.cost)
            out[f"Gross Margin{w}"] = Figure(_ratio(t.sales - t.cost, t.sales), "ratio")
            out[f"Order Intake{w}"] = _bn(t.orders)
            out[f"Budget{w}"] = _bn(t.budget)
            out[f"Budget Attainment{w}"] = Figure(_ratio(t.sales, t.budget), "ratio")
        for w in [" YTD", " Rolling 12 Months"]:
            if w not in totals:
                continue
            now, before = totals[w], totals[w + " Prior Year"]
            margin_now, margin_before = now.sales - now.cost, before.sales - before.cost
            out[f"Sales{w} vs Prior Year"] = _bn(now.sales - before.sales)
            out[f"Sales{w} vs Prior Year %"] = Figure(_growth(now.sales, before.sales), "ratio")
            out[f"Sales{w} vs Budget"] = _bn(now.sales - now.budget)
            out[f"Sales{w} vs Budget %"] = Figure(_growth(now.sales, now.budget), "ratio")
            out[f"Gross Margin Amount{w} vs Prior Year"] = _bn(margin_now - margin_before)
            out[f"Gross Margin Amount{w} vs Prior Year %"] = Figure(_growth(margin_now, margin_before), "ratio")
            out[f"Gross Margin{w} vs Prior Year"] = _pp(_ratio(margin_now, now.sales), _ratio(margin_before, before.sales))
            out[f"Order Intake{w} vs Prior Year"] = _bn(now.orders - before.orders)
            out[f"Order Intake{w} vs Prior Year %"] = Figure(_growth(now.orders, before.orders), "ratio")
            out[f"Budget Attainment{w} vs Prior Year"] = _pp(_ratio(now.sales, now.budget),
                                                             _ratio(before.sales, before.budget))
        if any(f in selection for f in NO_BUDGET_FIELDS):  # Budget is not planned at that level: no figure
            out.update({n: Figure(None, f.unit) for n, f in out.items() if "Budget" in n})
        out.update(_concentration_totals(self.customers(selection)))
        if latest:
            out.update(_simulated([r for r in sales if date(latest.year, 1, 1) <= r[0] <= latest],
                                  scenario or Scenario(0, 0, 0)))
        if " YTD" in totals:  # Order Intake per euro of Sales invoiced in the same days
            out["Book-to-bill YTD"] = Figure(_ratio(totals[" YTD"].orders, totals[" YTD"].sales), "ratio")
        out.update(sales_bridge(sales, latest))
        for name in IN_EUR_M:  # the same amounts in EUR m, for Sheets where EUR bn reads €0.01 bn
            if name in out:
                value = out[name].value
                out[f"{name} in EUR m"] = Figure(None if value is None else value * 1000, "EUR m")
        return out

    def customers(self, selection):
        """Customer concentration in a selection: [Concentration], largest Sales YTD first, one per Customer
        with Sales YTD. YTD ends on the selection's Latest Date (the same day for every Customer); the cumulative
        share is the Customer's share plus that of every Customer above it, and sets its ABC class."""
        sales = _kept(self.sales, selection)
        latest = max((r[0] for r in _on_selected_days(sales, selection)), default=None)
        if not latest:
            return []
        cents = {}
        for d, attributes, amount, *_ in sales:
            if date(latest.year, 1, 1) <= d <= latest:
                cents[attributes["Customer"]] = cents.get(attributes["Customer"], 0) + amount
        total, running, out = Decimal(sum(cents.values())), 0, []
        for customer, amount in sorted(cents.items(), key=lambda kv: -kv[1]):
            running += amount
            cumulative = running / total
            abc = next(c for c, upper in ABC_CLASSES if upper is None or cumulative <= upper)
            out.append(Concentration(customer, amount / total, cumulative, abc))
        return out


# ABC classes by cumulative share of Sales YTD: A up to 80%, B up to 95%, C the rest (docs/measures.md).
ABC_CLASSES = [("A", Decimal("0.80")), ("B", Decimal("0.95")), ("C", None)]
Concentration = namedtuple("Concentration", "customer share cumulative abc")


def _concentration_totals(customers):
    """The Customer concentration measures outside a chart by Customer: the share of all Customers together
    is 100%; the cumulative share and the ABC class only exist in a chart (null)."""
    return {"Customer Share": Figure(Decimal(1) if customers else None, "ratio"),
            "Customer Cumulative Share": Figure(None, "ratio"),
            "Customer ABC Class": Figure(None, "count")}



def sales_bridge(rows, latest):
    """The Sales Bridge figures {name: Figure}: Sales YTD vs Prior Year split into volume, price and mix effects
    at Product Line by Customer level (docs/measures.md, Sales Bridge). `rows` are the selection's sales rows
    (date, attributes, Sales in cents, cost in cents, Volume) on any day; `latest` is the Latest Date or None."""
    if latest is None:
        return {}
    windows = [(date(latest.year, 1, 1), latest), (date(latest.year - 1, 1, 1), _a_year_earlier(latest))]
    # cells[(Product Line, Customer)] = [Sales YTD, Volume YTD, Sales YTD Prior Year, Volume YTD Prior Year]
    cells = {}
    for d, attrs, cents, _, volume in rows:
        for i, (first, last) in enumerate(windows):
            if first <= d <= last:
                cell = cells.setdefault((attrs["Product Line"], attrs["Customer"]), [0, 0, 0, 0])
                cell[2 * i] += cents
                cell[2 * i + 1] += volume
    s1, v1, s0, v0 = (sum(c[i] for c in cells.values()) for i in range(4))
    if v0:
        average_price = Fraction(s0, v0)  # Prior Year Sales per unit over all cells
        volume_effect = (v1 - v0) * average_price
        # A cell's Prior Year price; a cell new this year takes its own current price (no price effect).
        base_price = {k: Fraction(c[2], c[3]) if c[3] else Fraction(c[0], c[1]) for k, c in cells.items() if c[1]}
        price_effect = sum((c[0] - c[1] * base_price[k] for k, c in cells.items() if c[1] and c[3]), Fraction(0))
        mix_effect = sum((c[1] * base_price[k] for k, c in cells.items() if c[1]), Fraction(0)) - v1 * average_price
    else:  # no Prior Year Sales: the whole change is volume
        volume_effect, price_effect, mix_effect = Fraction(s1 - s0), Fraction(0), Fraction(0)
    if volume_effect + price_effect + mix_effect != s1 - s0:
        raise AssertionError("the Sales Bridge effects do not sum exactly to the Sales change")

    def bn(cents):
        return _bn(_decimal(cents / 100))
    return {"Volume Effect YTD vs Prior Year": bn(volume_effect), "Price Effect YTD vs Prior Year": bn(price_effect),
            "Mix Effect YTD vs Prior Year": bn(mix_effect)}


# What-If Simulator (docs/measures.md): a scenario's changes in percent. `exchange_rate` is the change of the
# euro against every other currency: +10 means the euro buys 10% more of each, so an amount in another
# currency is worth 1 / 1.10 of its EUR value.
Scenario = namedtuple("Scenario", "price volume exchange_rate")
# The exchange rate assumption: Sales to a Country outside the euro area is invoiced in its local currency,
# and this share of the cost of those Sales is local too (the rest is bought in EUR).
EURO_AREA = {"Germany", "France", "Spain", "Italy"}
LOCAL_COST_SHARE = Fraction(6, 10)


def _simulated(rows, scenario):
    """The simulated YTD figures for the YTD sales rows (date, attributes, sales cents, cost cents, Volume) of a
    selection. Each row is re-priced, re-sized and, outside the euro area, translated at the new rate; the
    rows are summed by currency first, which gives the same result."""
    price, volume = 1 + Fraction(scenario.price, 100), 1 + Fraction(scenario.volume, 100)
    foreign = 1 / (1 + Fraction(scenario.exchange_rate, 100))
    cents = {(abroad, kind): 0 for abroad in (False, True) for kind in ("sales", "cost")}
    for _, attributes, row_sales, row_cost, _ in rows:
        abroad = attributes.get("Country") not in EURO_AREA
        cents[abroad, "sales"] += row_sales
        cents[abroad, "cost"] += row_cost
    eur = {k: Fraction(v, 100) for k, v in cents.items()}
    sales = price * volume * (eur[False, "sales"] + eur[True, "sales"] * foreign)
    cost = volume * (eur[False, "cost"] + eur[True, "cost"] * (LOCAL_COST_SHARE * foreign + 1 - LOCAL_COST_SHARE))
    actual_sales, actual_cost = eur[False, "sales"] + eur[True, "sales"], eur[False, "cost"] + eur[True, "cost"]
    margin, actual_margin = sales - cost, actual_sales - actual_cost
    return {"Simulated Sales YTD": _bn(_decimal(sales)),
            "Simulated Sales YTD vs Actual": _bn(_decimal(sales - actual_sales)),
            "Simulated Sales YTD vs Actual %": Figure(_growth(_decimal(sales), _decimal(actual_sales)), "ratio"),
            "Simulated Gross Margin Amount YTD": _bn(_decimal(margin)),
            "Simulated Gross Margin Amount YTD vs Actual": _bn(_decimal(margin - actual_margin)),
            "Simulated Gross Margin YTD": Figure(_ratio(_decimal(margin), _decimal(sales)), "ratio"),
            "Simulated Gross Margin YTD vs Actual": _pp(_ratio(_decimal(margin), _decimal(sales)),
                                                        _ratio(_decimal(actual_margin), _decimal(actual_sales)))}
