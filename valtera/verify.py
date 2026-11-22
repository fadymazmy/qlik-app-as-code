"""Verify command: compares every master measure with the Reference calculator and captures each Sheet.

Exits non-zero on any failure.
"""
import json
import random
import re
import shutil
import tempfile
from collections import defaultdict
from decimal import Decimal
from itertools import combinations
from pathlib import Path

from valtera import capture as cap
from valtera import qlik, reference
from valtera.paths import workdir

# Allowed difference between the App and the Reference calculator, by unit: float sums in the engine
# against exact sums here.
TOLERANCE = {"EUR bn": Decimal("1e-11"), "EUR m": Decimal("1e-8"), "ratio": Decimal("1e-9"), "pp": Decimal("1e-7"), "count": Decimal(0)}

# The selections every master measure is checked in, as {field: value}, made as real selections in the App.
# The Date one makes the Latest Date fall mid-month, so the Budget spread over days is exercised.
SELECTIONS = [
    {},
    {"Year": "2025"},
    {"Business Group": "Lighting"},
    {"Region": "Asia"},
    {"Channel": "Aftermarket"},
    {"Year": "2025", "Business Group": "Propulsion", "Region": "Europe", "Channel": "Original Equipment"},
    {"Date": "2026-06-15"},
    {"Business Group": "Lighting", "Region": "Asia"},
    {"Customer": "Kestova Motors"},  # Budget has no Customer or Production Site: every Budget figure is null
    {"Production Site": "Brno", "Year": "2025"},
]
# How an amount in EUR displays: "€17.62 bn" or "€17,620.0 m" (variances carry a sign), and to what precision.
DISPLAY = {"EUR bn": (re.compile(r"^([+-]?)€(\d{1,3}(?:,\d{3})*\.\d\d) bn$"), Decimal("0.005"), "€{:,.2f} bn"),
           "EUR m": (re.compile(r"^([+-]?)€(\d{1,3}(?:,\d{3})*\.\d) m$"), Decimal("0.05"), "€{:,.1f} m")}

# App table -> the CSV files loaded into it
TABLES = {"Facts": ["sales.csv", "budget.csv", "order_intake.csv"], "Calendar": ["calendar.csv"],
          "Product Lines": ["product_lines.csv"], "Customers": ["customers.csv"], "Countries": ["countries.csv"],
          "Production Sites": ["production_sites.csv"], "Channels": ["channels.csv"]}
# Fact CSV file -> an App expression that counts its rows in the Facts table
FACT_COUNTS = {"sales.csv": "Count(Sales)", "budget.csv": "Count(Budget)",
               "order_intake.csv": "Count([Order Intake])"}


def where(selection):
    """A selection {field: value} as a label: "Year=2025, Region=Asia", or "no selection"."""
    return ", ".join(f"{f}={v}" for f, v in selection.items()) or "no selection"


def number(cell):
    """A hypercube cell's number as a Decimal, or None for null. qlik-cli leaves qNum out when it is 0."""
    value = cell.get("qNum", 0)
    return None if value == "NaN" else Decimal(repr(value))


def evaluate(app_id, *expressions, selection=None, ttl=0):
    """Evaluate expressions in one hypercube of the reloaded App, after selecting {field: value} in it.
    Returns one cell ({qText, qNum}) per expression."""
    args = ["app", "eval", *expressions]
    for field, value in (selection or {}).items():
        args += ["where", field, "is", value]
    pages = qlik.run_json(*args, "-a", app_id, "--ttl", ttl)  # hypercube data pages: [{"qMatrix": [[cell, ...]]}]
    return pages[0]["qMatrix"][0]


def evaluate_by(app_id, dimension, *expressions, selection=None):
    """Evaluate expressions by one dimension, after selecting {field: value}: {dimension value: [cell, ...]}.
    The hypercube comes in the engine's own order, not sorted by any measure."""
    args = ["app", "eval", *expressions, "by", dimension]
    for field, value in (selection or {}).items():
        args += ["where", field, "is", value]
    pages = qlik.run_json(*args, "-a", app_id, "--rows", 1000)
    return {row[0]["qText"]: row[1:] for page in pages for row in page["qMatrix"]}


def check(label, actual, expected, unit, failures, quiet=False):
    """Compare a number from the App with the expected one (None, a null, only matches None).
    With `quiet`, only a failure is printed."""
    if actual is None or expected is None:
        ok = actual is None and expected is None
    else:
        ok = abs(actual - expected) <= TOLERANCE[unit]
    if not ok or not quiet:
        print(f"  {'ok  ' if ok else 'FAIL'} {label}: app {actual} reference {expected}")
    if not ok:
        failures.append(label)
    return ok


def check_text(label, cell, expected, failures):
    """Compare a cell's text from the App with the expected text; only a failure is printed."""
    if cell.get("qText") != expected:
        print(f"  FAIL {label}: app {cell.get('qText')} reference {expected}")
        failures.append(label)


def check_data_model(app_id, data_dir):
    """Row counts per table and per fact against the CSV files; no synthetic keys, no circular references."""
    failures = []
    meta = json.loads(qlik.run("raw", "get", f"v1/apps/{app_id}/data/metadata"))
    tables = [t for t in meta["tables"] if not t["is_system"]]
    keys = [f for f in meta["fields"] if not f["is_system"] and len(f["src_tables"]) > 1]
    # The metadata leaves out the $Syn tables, but each key field still lists the tables it links.
    pairs = defaultdict(list)
    for f in keys:
        for a, b in combinations(sorted(f["src_tables"]), 2):
            pairs[(a, b)].append(f["name"])
    synthetic = [f"{a}+{b}: {'+'.join(names)}" for (a, b), names in pairs.items() if len(names) > 1]
    # A circular reference is a cycle among tables linked by key fields; the engine makes a table loose to break it.
    group = {t["name"]: t["name"] for t in tables}

    def root(t):
        while group[t] != t:
            t = group[t]
        return t
    loops = [t["name"] for t in tables if t["is_loose"]]
    for f in keys:
        first, *rest = f["src_tables"]
        for t in rest:
            if root(t) == root(first):
                loops.append(f"{f['name']} closes a loop")
            group[root(t)] = root(first)
    print(f"  {'FAIL' if synthetic else 'ok  '} synthetic keys: {synthetic or 'none'}")
    print(f"  {'FAIL' if loops else 'ok  '} circular references: {loops or 'none'}")
    failures += ["synthetic keys"] * bool(synthetic) + ["circular references"] * bool(loops)

    csv_rows = reference.row_counts(data_dir)
    app_rows = {t["name"]: t["no_of_rows"] for t in tables}
    if set(app_rows) != set(TABLES):
        failures.append("tables differ")
        print(f"  FAIL tables: app {sorted(app_rows)} expected {sorted(TABLES)}")
    for table, files in TABLES.items():
        check(f"rows {table}", Decimal(app_rows.get(table, 0)), Decimal(sum(csv_rows[f] for f in files)),
              "count", failures)
    for file, expression in FACT_COUNTS.items():
        check(f"rows {file} ({expression})", number(evaluate(app_id, expression)[0]), Decimal(csv_rows[file]),
              "count", failures)
    return failures


def library(app_id, out):
    """The App's master measures {name: expression}, their names {id: name} and master dimensions
    {name: field}, read with unbuild into `out`."""
    if out.exists():
        shutil.rmtree(out)
    qlik.run("app", "unbuild", "-a", app_id, "--dir", out)
    measures = json.loads((out / "measures.json").read_text())
    dimensions = json.loads((out / "dimensions.json").read_text())
    return ({m["qMetaDef"]["title"]: m["qMeasure"]["qDef"] for m in measures},
            {m["qInfo"]["qId"]: m["qMetaDef"]["title"] for m in measures},
            {d["qMetaDef"]["title"]: d["qDim"]["qFieldDefs"][0] for d in dimensions})


def check_dimensions(app_id, dimensions, ref):
    """Each master dimension exists and has as many values as the CSV files hold."""
    failures = []
    expected = ref.dimension_counts()
    for name in sorted(set(expected) ^ set(dimensions)):
        side = "the App" if name in expected else "the Reference calculator"
        print(f"  FAIL master dimension {name}: missing in {side}")
        failures.append(f"dimension {name} missing")
    names = sorted(set(dimensions) & set(expected))
    cells = evaluate(app_id, *(f"Count({{1}} DISTINCT [{dimensions[n]}])" for n in names)) if names else []
    for name, cell in zip(names, cells):
        check(f"{name}: values", number(cell), Decimal(expected[name]), "count", failures)
    return failures


def check_measures(app_id, measures, ref):
    """Every master measure against the Reference calculator in each selection, and amounts shown in their unit."""
    failures = []
    names = sorted(measures)
    for name in sorted(set(ref.figures({})) ^ set(measures)):
        side = "the App" if name not in measures else "the Reference calculator"
        print(f"  FAIL master measure {name}: missing in {side}")
        failures.append(f"{name} missing")
    for selection in SELECTIONS:
        label = where(selection)
        expected = ref.figures(selection)
        before = len(failures)
        cells = evaluate(app_id, *(measures[n] for n in names), selection=selection)
        for name, cell in zip(names, cells):
            if name not in expected:
                continue
            value, unit = expected[name]
            if not check(f"{label}: {name}", number(cell), value, unit, failures, quiet=True):
                continue
            if unit not in DISPLAY or value is None:
                continue
            pattern, precision, text = DISPLAY[unit]
            shown = pattern.match(cell["qText"])
            if not (shown and abs(Decimal(shown[1] + shown[2].replace(",", "")) - value) <= precision):
                print(f"  FAIL {label}: {name} shows {cell['qText']!r}, not {text.format(value)}")
                failures.append(f"{label}: {name} display")
        if len(failures) == before:
            print(f"  ok   {label}: {len(names)} master measures match")
    return failures


# Customer concentration is checked per Customer in these selections; the second holds the Planted Story
# (Kestova Motors with about 30% of Propulsion's Sales YTD).
CONCENTRATION_SELECTIONS = [{}, {"Business Group": "Propulsion"}, {"Year": "2025", "Region": "Asia"}]
CONCENTRATION_TABLE = "cr-customers"  # the Customer table on the Customer and Region Sheet
# The side-by-side comparison: one selection per alternate state, made in the same session together with
# a selection in the default state ($), so each must stay independent of the others.
COMPARISON = {"A": {"Business Group": "Propulsion", "Region": "Europe"},
              "B": {"Business Group": "Lighting", "Region": "Asia", "Year": "2025"},
              "$": {"Channel": "Aftermarket"}}


def check_concentration(app_id, measures, ref):
    """Per Customer: Sales YTD share, cumulative share and ABC class from the Sheet's Customer table (sorted
    by Sales YTD, largest first) against the Reference calculator; and the same measures by Customer in the
    engine's own order, as a person re-sorting the table would see them, which must not change them."""
    failures = []
    names = ["Customer Share", "Customer Cumulative Share", "Customer ABC Class"]
    for selection in CONCENTRATION_SELECTIONS:
        label = where(selection)
        expected = ref.customers(selection)
        before = len(failures)
        unsorted = evaluate_by(app_id, "Customer", *(measures[n] for n in names), selection=selection)
        for c in expected:
            _, cumulative, abc = unsorted.get(c.customer, [{}, {}, {}])
            check(f"{label}, any order: {c.customer} {names[1]}", number(cumulative), c.cumulative, "ratio",
                  failures, quiet=True)
            check_text(f"{label}, any order: {c.customer} {names[2]}", abc, c.abc, failures)
        rows = customer_rows(app_id, selection)
        if [r[0] for r in rows] != [c.customer for c in expected]:
            failures.append(f"{label}: Customer order")
            print(f"  FAIL {label}: Customers app {[r[0] for r in rows]} reference {[c.customer for c in expected]}")
            continue
        for (customer, share, cumulative, abc), c in zip(rows, expected):
            check(f"{label}: {customer} {names[0]}", number(share), c.share, "ratio", failures, quiet=True)
            check(f"{label}: {customer} {names[1]}", number(cumulative), c.cumulative, "ratio", failures, quiet=True)
            check_text(f"{label}: {customer} {names[2]}", abc, c.abc, failures)
        if len(failures) == before:
            top = expected[0]
            print(f"  ok   {label}: {len(rows)} Customers match; largest {top.customer} {top.share:.1%}, "
                  f"classes {''.join(c.abc for c in expected)}")
    return failures


def check_comparison(page, app_id, app_url, unbuild_dir, titles, ref):
    """Every master measure an object in an alternate state shows, evaluated inside that state after the
    state's own selection (COMPARISON), against the Reference calculator for that selection."""
    failures = []
    used, sheets = defaultdict(set), set()

    def walk(node, sheet, state=None):
        if isinstance(node, dict):
            state = node.get("qStateName") or state
            if "qLibraryId" in node and node["qLibraryId"] in titles and state:
                used[state].add(node["qLibraryId"])
                sheets.add(sheet)
            for v in node.values():
                walk(v, sheet, state)
        elif isinstance(node, list):
            for v in node:
                walk(v, sheet, state)
    for f in sorted((unbuild_dir / "objects").glob("sheet--*.json")):
        entry = json.loads(f.read_text())
        walk(entry, entry["qProperty"]["qInfo"]["qId"])
    for state in sorted(set(COMPARISON) - {"$"} - set(used)):
        print(f"  FAIL no object shows a master measure in state {state}")
        failures.append(f"state {state} unused")
    if not used:
        return failures
    ids = sorted(set().union(*used.values()))
    cells = cap.evaluate_in_states(page, app_id, f"{app_url}/sheet/{min(sheets)}/state/analysis", COMPARISON, ids)
    for state in ["$", *sorted(used)]:
        expected = ref.figures(COMPARISON[state])
        for mid, cell in zip(ids, cells[state]):
            check(f"state {state} ({where(COMPARISON[state])}): {titles[mid]}", number(cell), *expected[titles[mid]],
                  failures)
    return failures


def layouts_in_selection(app_id, object_ids, selection):
    """{object id: layout} of Sheet objects as they show under `selection`. `app eval` cannot sort or read
    an object, so the selection is made in a kept engine session (`--ttl`; calls with the same ttl share one
    session, and its selections add up) and each object's layout is read in that same session. A ttl whose
    session already holds selections is skipped."""
    for ttl in random.sample(range(300, 900), 20):
        if evaluate(app_id, "GetCurrentSelections() & '|'", ttl=ttl)[0]["qText"] == "|":
            break
    else:
        raise qlik.QlikError("no fresh engine session to read Sheet objects in")
    if selection:
        evaluate(app_id, "1", selection=selection, ttl=ttl)
    return {i: qlik.run_json("app", "object", "layout", i, "-a", app_id, "--ttl", ttl) for i in object_ids}


def customer_rows(app_id, selection):
    """[(Customer, share cell, cumulative share cell, ABC class cell)] as the Sheet's Customer table lists
    them under `selection`."""
    cube = layouts_in_selection(app_id, [CONCENTRATION_TABLE], selection)[CONCENTRATION_TABLE]["qHyperCube"]
    ids = [m.get("qLibraryId") for m in cube["qMeasureInfo"]]  # the columns carry short labels
    columns = [1 + ids.index(i) for i in ["m_customer_share", "m_customer_cumulative_share", "m_customer_abc_class"]]
    return [(row[0]["qText"], *(row[c] for c in columns)) for page in cube["qDataPages"] for row in page["qMatrix"]]


# The Product Line and Margin Sheet: every cell its objects show, against the Reference calculator in each of
# MARGIN_SELECTIONS. A cell's figure is its column's master measure in the selection, narrowed to the cell's own
# dimension values (a total cell adds none); the cell keeps the selection's Latest Date. The second selection is
# the Lighting in Asia Planted Story.
MARGIN_OBJECTS = ["plm-product-channel", "plm-margin-change", "plm-trend", "plm-bridge"]
MARGIN_SELECTIONS = [{}, {"Business Group": "Lighting", "Region": "Asia"}]


def object_cells(cube):
    """[({field: value}, master measure id, cell)] for every measure cell of a hypercube layout, straight or
    pivot (qMode "P"). A measure that is not a master measure has id None."""
    fields = [d["qFallbackTitle"] for d in cube["qDimensionInfo"]]
    ids = [m.get("qLibraryId") for m in cube["qMeasureInfo"]]
    if cube.get("qMode") != "P":
        return [({f: c["qText"] for f, c in zip(fields, row)}, i, c)
                for page in cube["qDataPages"] for row in page["qMatrix"] for i, c in zip(ids, row[len(fields):])]

    def leaves(nodes, names):
        """({field: value}, measure index or None) per leaf of a pivot header tree, in display order. A
        measure node ("P") names no field; a total node ("T") names its field but adds no value."""
        for n in nodes:
            values = {names[0]: n["qText"]} if n["qType"] == "N" else {}
            measure = n["qElemNo"] if n["qType"] == "P" else None
            if not n.get("qSubNodes"):
                yield values, measure
                continue
            for more, m in leaves(n["qSubNodes"], names if n["qType"] == "P" else names[1:]):
                yield {**values, **more}, measure if m is None else m
    page, left = cube["qPivotDataPages"][0], cube["qNoOfLeftDims"]
    return [({**row, **column}, ids[(c_m if c_m is not None else r_m) or 0], page["qData"][r][c])
            for r, (row, r_m) in enumerate(leaves(page["qLeft"], fields[:left]))
            for c, (column, c_m) in enumerate(leaves(page["qTop"], fields[left:]))]


def check_margin_sheet(app_id, titles, ref):
    """Every cell of the Product Line and Margin Sheet's objects against the Reference calculator, and the
    Lighting in Asia Planted Story as the Sheet shows it."""
    failures = []
    figures = {}
    for selection in MARGIN_SELECTIONS:
        label = where(selection)
        layouts = layouts_in_selection(app_id, MARGIN_OBJECTS, selection)
        before, count = len(failures), 0
        for object_id, layout in layouts.items():
            cells = [c for c in object_cells(layout["qHyperCube"]) if c[1] in titles]
            if not cells:
                print(f"  FAIL {label}: {object_id} shows no master measure")
                failures.append(f"{label}: {object_id} empty")
            for values, measure, cell in cells:
                key = (tuple(sorted(selection.items())), tuple(sorted(values.items())))
                if key not in figures:
                    figures[key] = ref.figures(selection, cell=values)
                check(f"{label}: {object_id} {', '.join(values.values()) or 'total'} {titles[measure]}", number(cell),
                      *figures[key][titles[measure]], failures, quiet=True)
                count += 1
        if len(failures) == before:
            print(f"  ok   {label}: {count} cells in {len(layouts)} objects match")
        if selection == MARGIN_SELECTIONS[1]:
            failures += check_lighting_in_asia(layouts, titles)
    return failures


def check_lighting_in_asia(layouts, titles):
    """With Lighting and Asia selected: the trend's Gross Margin falls over its last 12 months while their
    Sales grows on the 12 months before, and the bridge shows a negative Price Effect beside a positive
    Volume Effect."""
    def values(object_id):
        rows = defaultdict(dict)
        for dims, measure, cell in object_cells(layouts[object_id]["qHyperCube"]):
            rows[tuple(dims.values())][titles.get(measure)] = number(cell)
        return list(rows.values())
    months = values("plm-trend")
    bridge = values("plm-bridge")[0]
    last, before = months[-12:], months[-24:-12]
    facts = {
        "Gross Margin falls by over 5 pp across the last 12 months":
            last[-1]["Gross Margin"] < last[0]["Gross Margin"] - Decimal("0.05"),
        "Sales of the last 12 months exceed the 12 before":
            sum(m["Sales in EUR m"] for m in last) > sum(m["Sales in EUR m"] for m in before),
        "the bridge's Price Effect is negative": bridge["Price Effect YTD vs Prior Year in EUR m"] < 0,
        "the bridge's Volume Effect is positive": bridge["Volume Effect YTD vs Prior Year in EUR m"] > 0,
    }
    print(f"  Lighting in Asia: Gross Margin {last[0]['Gross Margin']:.1%} to {last[-1]['Gross Margin']:.1%} by "
          f"month; Price Effect {bridge['Price Effect YTD vs Prior Year in EUR m']:+.1f} m, "
          f"Volume Effect {bridge['Volume Effect YTD vs Prior Year in EUR m']:+.1f} m")
    for fact, ok in facts.items():
        print(f"  {'ok  ' if ok else 'FAIL'} Lighting in Asia: {fact}")
    return [f"Lighting in Asia: {fact}" for fact, ok in facts.items() if not ok]


BRIDGE = ["Volume Effect YTD vs Prior Year", "Price Effect YTD vs Prior Year", "Mix Effect YTD vs Prior Year"]


def check_sales_bridge(app_id, measures):
    """In the App itself, the volume, price and mix effects add up to Sales YTD vs Prior Year in each selection."""
    failures = []
    if not all(n in measures for n in BRIDGE):
        print("  FAIL the Sales Bridge measures are missing in the App")
        return ["sales bridge missing"]
    for selection in SELECTIONS:
        *effects, change = map(number, evaluate(app_id, *(measures[n] for n in [*BRIDGE, "Sales YTD vs Prior Year"]),
                                                selection=selection))
        check(f"{where(selection)}: volume + price + mix (difference {sum(effects) - change:.1e} bn)", sum(effects), change,
              "EUR bn", failures)
    return failures


# What-If scenarios: each sets the What-If variables in the App (which saves it) and compares the simulated
# master measures with the Reference calculator in a selection; the variables are restored afterwards. The
# SELECTIONS above run with the variables as the build leaves them: no change.
SCENARIOS = [
    ({}, {"vPriceChange": 5, "vVolumeChange": -10, "vExchangeRateChange": 10}),
    ({"Region": "Asia"}, {"vPriceChange": -3, "vVolumeChange": 8, "vExchangeRateChange": -15}),
    ({"Country": "Germany"}, {"vPriceChange": 0, "vVolumeChange": 0, "vExchangeRateChange": 20}),
    ({"Region": "Europe", "Business Group": "Lighting"},
     {"vPriceChange": 2, "vVolumeChange": 0, "vExchangeRateChange": 20}),
    ({"Year": "2025", "Channel": "Aftermarket"}, {"vPriceChange": 20, "vVolumeChange": -20, "vExchangeRateChange": -20}),
]


def set_variables(app_id, values):
    """Set App variables {name: value} and save the App; return their definitions before."""
    props = [json.loads(qlik.run("app", "variable", "properties", name, "-a", app_id)) for name in values]
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "variables.json"
        path.write_text(json.dumps([dict(p, qDefinition=str(values[p["qName"]])) for p in props]))
        qlik.run("app", "variable", "set", path, "-a", app_id)
    return {p["qName"]: p["qDefinition"] for p in props}


def check_scenarios(app_id, measures, ref):
    """The simulated master measures against the Reference calculator in each What-If scenario."""
    failures = []
    names = sorted(n for n in measures if n.startswith("Simulated "))
    before = None
    try:
        for selection, values in SCENARIOS:
            changed = set_variables(app_id, values)
            before = before or changed
            label = where({**selection, **values})
            expected = ref.figures(selection, reference.Scenario(
                values["vPriceChange"], values["vVolumeChange"], values["vExchangeRateChange"]))
            cells = evaluate(app_id, *(measures[n] for n in names), selection=selection)
            count = len(failures)
            for name, cell in zip(names, cells):
                check(f"{label}: {name}", number(cell), *expected[name], failures, quiet=True)
            if len(failures) == count:
                print(f"  ok   {label}: {len(names)} simulated master measures match")
    finally:
        if before:
            set_variables(app_id, before)
    return failures


def verify(app_name, capture=True):
    space_id = qlik.find_space()
    item = space_id and qlik.find_app(space_id, app_name)
    if not item:
        raise SystemExit(f"FAIL: no app called {app_name} in {qlik.SPACE}")
    app_id, url, work = item["resourceId"], item["links"]["open"]["href"], workdir(app_name)
    data_dir = work / "data"
    if not (data_dir / "sales.csv").exists():
        raise SystemExit(f"FAIL: no CSV files in {data_dir}; run the build first")

    print(f"data model: {app_name} ({app_id}) against the CSV files")
    failures = check_data_model(app_id, data_dir)
    ref = reference.Reference(data_dir)
    measures, titles, dimensions = library(app_id, work / "unbuild")
    print("master dimensions: against the CSV files")
    failures += check_dimensions(app_id, dimensions, ref)
    print(f"master measures: against the Reference calculator in {len(SELECTIONS)} selections")
    failures += check_measures(app_id, measures, ref)
    print(f"customer concentration: per Customer in {len(CONCENTRATION_SELECTIONS)} selections")
    failures += check_concentration(app_id, measures, ref)
    print(f"product line and margin: every cell of the Sheet's objects in {len(MARGIN_SELECTIONS)} selections")
    failures += check_margin_sheet(app_id, titles, ref)
    print(f"sales bridge: the three effects against the Sales change in {len(SELECTIONS)} selections")
    failures += check_sales_bridge(app_id, measures)
    print(f"What-If: simulated master measures in {len(SCENARIOS)} scenarios")
    failures += check_scenarios(app_id, measures, ref)

    if capture:
        with cap.browser_page() as page:
            print("alternate states: each side's master measures inside its state, after its own selection")
            failures += check_comparison(page, app_id, url, work / "unbuild", titles, ref)
            print("sheets: capture in a signed-in browser")
            failures += cap.capture_sheets(page, app_id, url, work / "captures")
    else:
        print("sheets: SKIPPED (--no-capture); the Sheet capture has not been checked")

    if failures:
        raise SystemExit(f"FAIL: {len(failures)} check(s) failed: {', '.join(failures)}")
    print("verify: all checks passed")
