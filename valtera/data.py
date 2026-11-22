"""Data generator: writes the Synthetic Data CSV files from a seed and a size.

Valtera is a fictional automotive supplier and its Customers are fictional carmaker groups.
`size` is the number of sales rows; Order Intake has a tenth of that, Budget one row per month,
Product Line, Country and Channel that had Sales. The same seed gives byte-identical files.
"""
import csv
import math
import random
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

FIRST_DAY = date(2024, 1, 1)
LAST_DAY = date(2026, 12, 31)

# Product Line ID: (Product Line, Business Group, share of rows, list price per unit in EUR in 2024)
PRODUCT_LINES = {
    "PL01": ("Electric Motors", "Propulsion", 14, 420),
    "PL02": ("Power Electronics", "Propulsion", 12, 310),
    "PL03": ("Thermal Systems", "Propulsion", 11, 260),
    "PL04": ("Transmission Components", "Propulsion", 8, 140),
    "PL05": ("ADAS Sensors", "Driving Intelligence", 10, 95),
    "PL06": ("Driving Cameras", "Driving Intelligence", 8, 75),
    "PL07": ("Domain Controllers", "Driving Intelligence", 7, 380),
    "PL08": ("Parking Systems", "Driving Intelligence", 5, 55),
    "PL09": ("Headlamps", "Lighting", 11, 210),
    "PL10": ("Rear Lamps", "Lighting", 7, 85),
    "PL11": ("Interior Lighting", "Lighting", 3, 30),
    "PL12": ("Lighting Electronics", "Lighting", 4, 45),
}
# Gross Margin on Original Equipment by Business Group, before noise and Planted Stories.
OE_GROSS_MARGIN = {"Propulsion": 0.17, "Driving Intelligence": 0.22, "Lighting": 0.20}

# Customer ID: (Customer, share of rows). All names are invented.
CUSTOMERS = {
    "C01": ("Aurelion Motors", 9), "C02": ("Brevane Automotive", 8), "C03": ("Caldon Motor Group", 8),
    "C04": ("Dravena Motors", 7), "C05": ("Elvaro Automobile", 6), "C06": ("Fenmark Motors", 6),
    "C07": ("Gorvath Auto Group", 5), "C08": ("Halvette Motors", 5), "C09": ("Istran Motor Works", 4),
    "C10": ("Jorlund Automotive", 4), "C11": ("Kestova Motors", 4), "C12": ("Lumera Auto Group", 4),
    "C13": ("Marveth Motors", 3), "C14": ("Norvane Automotive", 3), "C15": ("Ostrel Motors", 3),
    "C16": ("Pellavi Auto", 3), "C17": ("Quorvik Motor Group", 2), "C18": ("Selvane Motors", 2),
    "C19": ("Tarvos Automotive", 2), "C20": ("Ulmeric Motors", 2), "C21": ("Varendt Auto", 2),
    "C22": ("Wexmoor Motors", 1), "C23": ("Yaskari Motor Group", 1), "C24": ("Zenvora Automotive", 1),
}

# Country ID: (Country, Region, share of rows)
COUNTRIES = {
    "DE": ("Germany", "Europe", 14), "FR": ("France", "Europe", 9), "ES": ("Spain", "Europe", 6),
    "IT": ("Italy", "Europe", 5), "CZ": ("Czech Republic", "Europe", 4), "PL": ("Poland", "Europe", 3),
    "GB": ("United Kingdom", "Europe", 4),
    "US": ("United States", "North America", 16), "MX": ("Mexico", "North America", 7),
    "CA": ("Canada", "North America", 2),
    "CN": ("China", "Asia", 13), "JP": ("Japan", "Asia", 5), "KR": ("South Korea", "Asia", 4),
    "IN": ("India", "Asia", 3), "TH": ("Thailand", "Asia", 1),
    "BR": ("Brazil", "South America", 3), "AR": ("Argentina", "South America", 1),
}

# Production Site ID: (Production Site, Region it serves)
PRODUCTION_SITES = {
    "S01": ("Brno", "Europe"), "S02": ("Zaragoza", "Europe"), "S03": ("Wroclaw", "Europe"),
    "S04": ("Monterrey", "North America"), "S05": ("Greenville", "North America"),
    "S06": ("Wuhan", "Asia"), "S07": ("Pune", "Asia"), "S08": ("Rayong", "Asia"),
    "S09": ("Curitiba", "South America"),
}

CHANNELS = {"OE": "Original Equipment", "AM": "Aftermarket"}

ANNUAL_GROWTH = 0.04                 # Sales growth per year
CUSTOMER_TREND = (-0.04, 0.03)       # each Customer's own yearly growth on top of ANNUAL_GROWTH, drawn in this range
MONTH_SEASON = [0.95, 1.0, 1.1, 1.0, 1.0, 1.05, 0.95, 0.7, 1.05, 1.1, 1.05, 0.85]
WEEKDAY_SEASON = [1, 1, 1, 1, 1, 0.15, 0.05]
ROW_VALUE_MEDIAN = 23_500            # EUR; with the spread below the mean row is about 35k
ROW_VALUE_SPREAD = 0.9
OE_PRICE_DOWN = 0.02                 # Original Equipment net price falls each year
AM_PRICE_UP = 0.03                   # Aftermarket net price rises each year
LIST_PRICE_UP = 0.02
ORDER_INTAKE_ROWS = 10               # one Order Intake row per this many sales rows
BOOK_TO_BILL = (0.96, 1.12)
BUDGET_PLAN = {"OE": 1.03, "AM": 0.94}  # Budget as a multiple of actual Sales by Channel, before noise (AM: Planted Story 3)
BUDGET_NOISE = (0.96, 1.04)

# Planted Stories
# 1. Lighting loses Gross Margin in Asia over the last 12 months while its Sales there keep growing
#    (price erosion: its net price falls against List Price, its cost per unit stays, its Volume grows).
LIGHTING_ASIA_GROWTH = 0.25          # extra yearly growth of Lighting's row share in Asia
LIGHTING_ASIA_PRICE_EROSION = 0.16   # share of the net price lost by the last day, falling evenly over 12 months
# 2. One Customer takes a dominant share of Propulsion Sales from the other Customers, whose Propulsion
#    Sales shrink: about 15% of Propulsion Sales in the first year, 30% in the last.
PROPULSION_CUSTOMER = "C11"          # Kestova Motors
PROPULSION_CUSTOMER_TAKE = (0.075, 0.31)  # share of Propulsion rows it has on top of its usual share,
                                          # on the first and the last day, rising evenly in between
PROPULSION_OTHERS_GROWTH = -0.025    # yearly growth of the other Customers' Propulsion rows, instead of ANNUAL_GROWTH
# 3. Aftermarket is small, has about twice the Gross Margin of Original Equipment and is ahead of Budget.
AFTERMARKET_ROW_SHARE = 0.10
AFTERMARKET_MARGIN_FACTOR = 2.0      # Aftermarket Gross Margin as a multiple of Original Equipment's


def _days():
    d = FIRST_DAY
    while d <= LAST_DAY:
        yield d
        d += timedelta(days=1)


def _years_in(d):
    """Years since FIRST_DAY, as a fraction: 0 on the first day, 3 at the end."""
    return (d - FIRST_DAY).days / 365.25


def _write(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)


def _picker(rng, table, weight):
    keys = list(table)
    cum, total = [], 0
    for k in keys:
        total += weight(table[k])
        cum.append(total)
    return lambda: rng.choices(keys, cum_weights=cum)[0]


def _propulsion_take(day):
    """The share of Propulsion rows the Planted Story gives PROPULSION_CUSTOMER on `day`."""
    start, end = PROPULSION_CUSTOMER_TAKE
    return start + (end - start) * _years_in(day) / _years_in(LAST_DAY)


def _propulsion_rows(day):
    """Propulsion's rows on `day` per row it would have at ANNUAL_GROWTH: the other Customers' rows grow at
    PROPULSION_OTHERS_GROWTH, and PROPULSION_CUSTOMER's take comes on top of theirs."""
    return ((1 + PROPULSION_OTHERS_GROWTH) / (1 + ANNUAL_GROWTH)) ** _years_in(day) / (1 - _propulsion_take(day))


PROPULSION_ROW_SHARE = (sum(v[2] for v in PRODUCT_LINES.values() if v[1] == "Propulsion")
                        / sum(v[2] for v in PRODUCT_LINES.values()))


class _Lines:
    """Draws one sales line: its dimensions and amounts."""

    def __init__(self, rng):
        self.rng = rng
        self.other_line = _picker(rng, {k: v for k, v in PRODUCT_LINES.items() if v[1] != "Propulsion"},
                                  lambda v: v[2])
        trend = {c: (share, 1 + random.Random(c).uniform(*CUSTOMER_TREND)) for c, (_, share) in CUSTOMERS.items()}
        self.customers = {}  # per month: a picker weighted by each Customer's share and its own growth
        for year in range(FIRST_DAY.year, LAST_DAY.year + 1):
            for month in range(1, 13):
                years = _years_in(date(year, month, 15))
                self.customers[year, month] = _picker(rng, trend, lambda v, y=years: v[0] * v[1] ** y)
        self.propulsion_line = _picker(rng, {k: v for k, v in PRODUCT_LINES.items() if v[1] == "Propulsion"},
                                       lambda v: v[2])
        self.country = _picker(rng, COUNTRIES, lambda v: v[2])
        self.countries = list(COUNTRIES)
        self.discount = {c: 0.10 + 0.10 * random.Random(c).random() for c in CUSTOMERS}
        self.sites = defaultdict(list)
        for site, (_, region) in PRODUCTION_SITES.items():
            self.sites[region].append(site)

    def dimensions(self, day):
        rng = self.rng
        propulsion = PROPULSION_ROW_SHARE * _propulsion_rows(day)
        if rng.random() < propulsion / (1 - PROPULSION_ROW_SHARE + propulsion):
            pl = self.propulsion_line()
            customer = (PROPULSION_CUSTOMER if rng.random() < _propulsion_take(day)
                        else self.customers[day.year, day.month]())
        else:
            pl, customer = self.other_line(), self.customers[day.year, day.month]()
        if PRODUCT_LINES[pl][1] == "Lighting":
            asia = (1 + LIGHTING_ASIA_GROWTH) ** _years_in(day)
            country = rng.choices(self.countries, [v[2] * (asia if v[1] == "Asia" else 1)
                                                   for v in COUNTRIES.values()])[0]
        else:
            country = self.country()
        channel = "AM" if rng.random() < AFTERMARKET_ROW_SHARE else "OE"
        site = rng.choice(self.sites[COUNTRIES[country][1]])
        return pl, customer, country, site, channel

    def value(self):
        return self.rng.lognormvariate(math.log(ROW_VALUE_MEDIAN), ROW_VALUE_SPREAD)

    def amounts(self, day, pl, customer, country, channel):
        rng = self.rng
        year = day.year - FIRST_DAY.year
        list_price = PRODUCT_LINES[pl][3] * (1 + LIST_PRICE_UP) ** year
        if channel == "OE":
            net_price = list_price * (1 - self.discount[customer]) * (1 - OE_PRICE_DOWN) ** year
        else:
            net_price = PRODUCT_LINES[pl][3] * 1.10 * (1 + AM_PRICE_UP) ** year
        list_price, net_price = round(list_price, 2), round(net_price, 2)
        group = PRODUCT_LINES[pl][1]
        margin = OE_GROSS_MARGIN[group] * (AFTERMARKET_MARGIN_FACTOR if channel == "AM" else 1)
        margin += rng.uniform(-0.03, 0.03)
        last_12_months = (day - (LAST_DAY - timedelta(days=365))).days / 365
        erosion = 0
        if group == "Lighting" and COUNTRIES[country][1] == "Asia" and last_12_months > 0:
            erosion = LIGHTING_ASIA_PRICE_EROSION * last_12_months
        # Price erosion sells more units for the same order value, each unit at the cost it had before.
        unit_cost = net_price * (1 - margin)
        net_price = round(net_price * (1 - erosion), 2)
        volume = max(1, round(self.value() / net_price))
        sales = round(volume * net_price, 2)
        cost = round(volume * unit_cost, 2)
        return volume, list_price, net_price, sales, cost


def generate(seed, size, out_dir):
    """Write the dimension and fact CSV files (`size` sales rows) into `out_dir`."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    days = list(_days())

    _write(out / "calendar.csv", ["Date", "Year", "Quarter", "Month"],
           ([d.isoformat(), d.year, f"Q{(d.month - 1) // 3 + 1}", d.strftime("%b")] for d in days))
    _write(out / "product_lines.csv", ["Product Line ID", "Product Line", "Business Group"],
           ([k, v[0], v[1]] for k, v in PRODUCT_LINES.items()))
    _write(out / "customers.csv", ["Customer ID", "Customer"], ([k, v[0]] for k, v in CUSTOMERS.items()))
    _write(out / "countries.csv", ["Country ID", "Country", "Region"],
           ([k, v[0], v[1]] for k, v in COUNTRIES.items()))
    _write(out / "production_sites.csv", ["Production Site ID", "Production Site"],
           ([k, v[0]] for k, v in PRODUCTION_SITES.items()))
    _write(out / "channels.csv", ["Channel ID", "Channel"], CHANNELS.items())

    # Propulsion's rows follow the Planted Story, so the days carry it too.
    day_weights = [(1 + ANNUAL_GROWTH) ** _years_in(d) * MONTH_SEASON[d.month - 1] * WEEKDAY_SEASON[d.weekday()]
                   * (1 - PROPULSION_ROW_SHARE + PROPULSION_ROW_SHARE * _propulsion_rows(d)) for d in days]
    lines = _Lines(rng)

    sales_rows, budget_base = [], defaultdict(float)
    for day in sorted(rng.choices(days, weights=day_weights, k=size)):
        pl, customer, country, site, channel = lines.dimensions(day)
        volume, list_price, net_price, sales, cost = lines.amounts(day, pl, customer, country, channel)
        sales_rows.append([day.isoformat(), pl, customer, country, site, channel,
                           volume, f"{list_price:.2f}", f"{net_price:.2f}", f"{sales:.2f}", f"{cost:.2f}"])
        budget_base[(day.replace(day=1).isoformat(), pl, country, channel)] += sales
    _write(out / "sales.csv", ["Date", "Product Line ID", "Customer ID", "Country ID", "Production Site ID",
                               "Channel ID", "Volume", "List Price", "Net Price", "Sales", "Cost"], sales_rows)

    _write(out / "budget.csv", ["Date", "Product Line ID", "Country ID", "Channel ID", "Budget"],
           ([*key, f"{amount * BUDGET_PLAN[key[3]] * rng.uniform(*BUDGET_NOISE):.2f}"]
            for key, amount in sorted(budget_base.items())))

    orders = []
    for day in sorted(rng.choices(days, weights=day_weights, k=size // ORDER_INTAKE_ROWS)):
        pl, customer, country, _, channel = lines.dimensions(day)
        amount = lines.value() * ORDER_INTAKE_ROWS * rng.uniform(*BOOK_TO_BILL)
        orders.append([day.isoformat(), pl, customer, country, channel, f"{amount:.2f}"])
    _write(out / "order_intake.csv",
           ["Date", "Product Line ID", "Customer ID", "Country ID", "Channel ID", "Order Intake"], orders)
