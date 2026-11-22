"""Spike generator: writes the code-only demo app (claude-scratch-demo) as qlik app build inputs.

Run: python3 gen.py  (writes objects/, measures.json, dimensions.json, variables.json next to this file)
Throwaway: proves which minimal JSON renders. Not the build.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
os.makedirs(os.path.join(HERE, "objects"), exist_ok=True)


def dump(name, obj):
    with open(os.path.join(HERE, name), "w") as f:
        json.dump(obj, f, indent=1)


REF = os.path.join(HERE, "..", "refobjects")
DEFAULTS_FOR = {"barchart", "combochart", "linechart", "sn-table", "sn-pivot-table", "action-button",
                "sn-text", "text-image", "sn-layout-container", "qlik-variable-input", "filterpane"}


def merge(base, over):
    """Deep-merge dicts; lists and scalars from `over` replace those in `base`."""
    if isinstance(base, dict) and isinstance(over, dict):
        out = dict(base)
        for k, v in over.items():
            out[k] = merge(base[k], v) if k in base else v
        return out
    return over


def with_defaults(prop):
    """Overlay `prop` on the default property tree the client wrote for the same type (from an unbuild)."""
    t = prop["qInfo"]["qType"]
    if t not in DEFAULTS_FOR:
        return prop
    base = json.load(open(os.path.join(REF, t + ".json")))["qProperty"]
    base = {k: v for k, v in base.items() if k not in ("qInfo", "extensionMeta", "childRefId")}
    if t == "sn-layout-container":
        base["objects"] = []
    if "qHyperCubeDef" in base:
        base["qHyperCubeDef"]["qDimensions"] = []
        base["qHyperCubeDef"]["qMeasures"] = []
    return merge(base, prop)


def entry(prop, children=()):
    return {"qProperty": with_defaults(prop), "qChildren": list(children)}


def cell(qid, qtype, col, row, colspan, rowspan, cols=24, rows=12):
    return {"name": qid, "type": qtype, "col": col, "row": row, "colspan": colspan, "rowspan": rowspan,
            "bounds": {"x": col / cols * 100, "y": row / rows * 100,
                       "width": colspan / cols * 100, "height": rowspan / rows * 100}}


def hc(dims=(), measures=(), width=None, height=500):
    w = width or (len(dims) + len(measures))
    return {"qDimensions": list(dims), "qMeasures": list(measures),
            "qInitialDataFetch": [{"qWidth": w, "qHeight": height}]}


def dim_field(field, label=None):
    return {"qDef": {"qFieldDefs": [field], "qFieldLabels": [label or field]}}


def meas(expr, label, fmt=None, series=None, extra=None):
    d = {"qDef": expr, "qLabel": label}
    if fmt:
        d["numFormatFromTemplate"] = False
        d["isCustomFormatted"] = True
        d["qNumFormat"] = fmt
    if series:
        d["series"] = series
    if extra:
        d.update(extra)
    return {"qDef": d}


BN = {"qType": "F", "qFmt": "€#,##0.00 bn", "qDec": ".", "qThou": ","}

# ---------- master items ----------
dump("measures.json", [
    {"qInfo": {"qId": "m_sales", "qType": "measure"},
     "qMeasure": {"qLabel": "Sales", "qDef": "Sum({<Year={2026}>} Sales)", "coloring": {"baseColor": {"color": "#1aa865", "index": -1}}},
     "qMetaDef": {"title": "Sales", "description": "", "tags": []}},
    {"qInfo": {"qId": "m_budget", "qType": "measure"},
     "qMeasure": {"qLabel": "Budget", "qDef": "Sum({<Year={2026}>} Budget)", "coloring": {"baseColor": {"color": "#3987e5", "index": -1}}},
     "qMetaDef": {"title": "Budget", "description": "", "tags": []}},
    {"qInfo": {"qId": "m_py", "qType": "measure"},
     "qMeasure": {"qLabel": "Prior Year", "qDef": "Sum({<Year={2025}>} Sales)", "coloring": {"baseColor": {"color": "#d95926", "index": -1}}},
     "qMetaDef": {"title": "Prior Year", "description": "", "tags": []}},
])
dump("dimensions.json", [
    {"qInfo": {"qId": "d_bg", "qType": "dimension"},
     "qDim": {"qGrouping": "N", "qFieldDefs": ["BusinessGroup"], "qFieldLabels": ["Business Group"], "title": "Business Group"},
     "qMetaDef": {"title": "Business Group", "description": "", "tags": []}},
])
dump("variables.json", [
    {"qInfo": {"qId": "v_growth", "qType": "variable"}, "qName": "vGrowth", "qDefinition": "0.05", "qComment": "what-if growth"},
])

# ---------- app properties (theme + hidden chrome) ----------
dump("objects/appprops.json", {
    "qInfo": {"qId": "claude-appprops", "qType": "appprops"},
    "theme": "claude-dark",
    "presets": [{
        "id": "claude", "name": "claude",
        "navigationBar": {"components": {"logo": {"show": False}, "pendo": {"show": False},
                                         "mainNavigation": {"show": False}, "notificationMenu": {"show": False},
                                         "profile": {"show": False}}},
        "toolbar": {"show": False},
        "sheetHeader": {"show": False},
    }],
    "activePreset": "claude",
})

NAV = lambda qid: entry({"qInfo": {"qId": qid, "qType": "claude-nav"}, "visualization": "claude-nav",
                         "showTitles": False, "qSelectionObjectDef": {}})

# ---------- sheet 1: Executive Overview ----------
fp = entry({"qInfo": {"qId": "exec-filters", "qType": "filterpane"}, "visualization": "filterpane",
            "qChildListDef": {"qData": {}}},
           [entry({"qInfo": {"qId": f"exec-lb-{f.lower()}", "qType": "listbox"}, "visualization": "listbox",
                   "qListObjectDef": {"qDef": {"qFieldDefs": [f], "qFieldLabels": [lbl]},
                                      "qInitialDataFetch": [{"qWidth": 1, "qHeight": 100}], "qShowAlternatives": True},
                   "showTitles": True, "title": lbl})
            for f, lbl in [("Year", "Year"), ("BusinessGroup", "Business Group"), ("Region", "Region"), ("Customer", "Customer")]])

kpi = lambda qid, title, m: entry({"qInfo": {"qId": qid, "qType": "kpi"}, "visualization": "kpi", "showTitles": True,
                                   "title": title, "qHyperCubeDef": hc(measures=[m], height=1)})

combo = entry({"qInfo": {"qId": "exec-combo", "qType": "combochart"}, "visualization": "combochart",
               "showTitles": True, "title": "Sales vs Budget vs Prior Year", "subtitle": "By month, EUR",
               "color": {"auto": False, "mode": "primary", "useBaseColors": "measure"},
               "legend": {"show": True, "dock": "top"},
               "components": [{"key": "line", "style": {"lineType": "dashed"}}],
               "qHyperCubeDef": hc(dims=[dim_field("Month")], measures=[
                   {"qLibraryId": "m_sales", "qDef": {"series": {"type": "bar", "axis": 0}}},
                   {"qLibraryId": "m_budget", "qDef": {"series": {"type": "line", "axis": 0, "marker": "none"}}},
                   {"qLibraryId": "m_py", "qDef": {"series": {"type": "line", "axis": 0, "marker": "none"}}},
               ])})

bar = entry({"qInfo": {"qId": "exec-bar", "qType": "barchart"}, "visualization": "barchart", "showTitles": True,
             "title": "Sales by Business Group", "orientation": "horizontal",
             "dataPoint": {"showLabels": True},
             "qHyperCubeDef": hc(dims=[{"qLibraryId": "d_bg", "qDef": {}}],
                                 measures=[meas("Sum({<Year={2026}>} Sales)/1e9", "Sales", fmt=BN)])})

table = entry({"qInfo": {"qId": "exec-table", "qType": "sn-table"}, "visualization": "sn-table", "showTitles": True,
               "title": "Top Customers",
               "qHyperCubeDef": hc(dims=[dim_field("Customer")], measures=[
                   meas("Sum({<Year={2026}>} Sales)/1e9", "Sales", fmt=BN),
                   {"qDef": {"qDef": "Dual(If(Sum({<Year={2026}>} Sales)>=Sum({<Year={2025}>} Sales),'▲ ','▼ ')"
                                     "&Num(Sum({<Year={2026}>} Sales)/Sum({<Year={2025}>} Sales)-1,'0.0%'),"
                                     "Sum({<Year={2026}>} Sales)/Sum({<Year={2025}>} Sales)-1)",
                             "qLabel": "vs prior year"},
                    "qAttributeExpressions": [{"qExpression": "If(Sum({<Year={2026}>} Sales)>=Sum({<Year={2025}>} Sales),'#1aa865','#ff6b6b')",
                                               "id": "cellForegroundColor"}]},
               ])})

button = entry({"qInfo": {"qId": "exec-btn", "qType": "action-button"}, "visualization": "action-button",
                "style": {"label": "Go to Sales Performance"},
                "actions": [{"actionType": "clearAll", "cId": "a1"}],
                "navigation": {"action": "goToSheet", "sheet": "perf"}})

text = entry({"qInfo": {"qId": "exec-text", "qType": "sn-text"}, "visualization": "sn-text",
              "text": "Synthetic Data. Sales 2026: ", "components": []})

timage = entry({"qInfo": {"qId": "exec-textimage", "qType": "text-image"}, "visualization": "text-image",
                "markdown": "**Synthetic Data** (text-image, markdown)"})

exec_cells = [
    cell("exec-nav", "claude-nav", 0, 0, 24, 2),
    cell("exec-filters", "filterpane", 0, 2, 24, 1),
    cell("exec-kpi-auto", "kpi", 0, 3, 6, 2),
    cell("exec-kpi-bnfmt", "kpi", 6, 3, 6, 2),
    cell("exec-kpi-text", "kpi", 12, 3, 6, 2),
    cell("exec-btn", "action-button", 18, 3, 3, 2),
    cell("exec-textimage", "text-image", 21, 3, 3, 2),
    cell("exec-combo", "combochart", 0, 5, 16, 4),
    cell("exec-bar", "barchart", 16, 5, 8, 4),
    cell("exec-table", "sn-table", 0, 9, 24, 3),
]
dump("objects/sheet-exec.json", entry(
    {"qInfo": {"qId": "exec", "qType": "sheet"}, "qMetaDef": {"title": "Executive Overview", "description": ""},
     "rank": 0, "columns": 24, "rows": 12, "cells": exec_cells},
    [NAV("exec-nav"), fp,
     kpi("exec-kpi-auto", "Sales (auto format)", {"qLibraryId": "m_sales", "qDef": {}}),
     kpi("exec-kpi-bnfmt", "Sales (/1e9 + format)", meas("Sum({<Year={2026}>} Sales)/1e9", "Sales", fmt=BN)),
     kpi("exec-kpi-text", "Sales (Num() string)", meas("Num(Sum({<Year={2026}>} Sales)/1e9,'€#,##0.00 bn')", "Sales")),
     button, timage, combo, bar, table]))

# ---------- sheet 2: Sales Performance ----------
line = entry({"qInfo": {"qId": "perf-line", "qType": "linechart"}, "visualization": "linechart", "showTitles": True,
              "title": "Sales by month",
              "qHyperCubeDef": hc(dims=[dim_field("Month")], measures=[{"qLibraryId": "m_sales", "qDef": {}},
                                                                     {"qLibraryId": "m_py", "qDef": {}}])})
pivot = entry({"qInfo": {"qId": "perf-pivot", "qType": "sn-pivot-table"}, "visualization": "sn-pivot-table",
               "showTitles": True, "title": "Sales by Region and Business Group",
               "qHyperCubeDef": {"qDimensions": [dim_field("Region"), dim_field("BusinessGroup", "Business Group")],
                                 "qMeasures": [meas("Sum({<Year={2026}>} Sales)/1e9", "Sales", fmt=BN)],
                                 "qMode": "P", "qNoOfLeftDims": 1, "qAlwaysFullyExpanded": True,
                                 "qInitialDataFetch": [{"qWidth": 10, "qHeight": 50}]}})
container = entry({"qInfo": {"qId": "perf-container", "qType": "sn-layout-container"}, "visualization": "sn-layout-container",
                   "objects": [{"childRefId": "c-kpi", "label": "KPI", "bounds": {"x": 5, "y": 5, "width": 60, "height": 60},
                                "condition": {"qValueExpression": {}}},
                               {"childRefId": "c-btn", "label": "Button", "bounds": {"x": 50, "y": 50, "width": 45, "height": 40},
                                "condition": {"qValueExpression": {}}}],
                   "qChildListDef": {"qData": {"visualization": "/visualization", "qExtendsId": "/qExtendsId",
                                               "title": "/title", "childRefId": "/childRefId", "visible": "/visible"}}},
                  [entry({"qInfo": {"qId": "perf-container-kpi", "qType": "kpi"}, "visualization": "kpi", "childRefId": "c-kpi",
                          "showTitles": True, "title": "KPI inside container",
                          "qHyperCubeDef": hc(measures=[{"qLibraryId": "m_sales", "qDef": {}}], height=1)}),
                   entry({"qInfo": {"qId": "perf-container-btn", "qType": "action-button"}, "visualization": "action-button",
                          "childRefId": "c-btn", "style": {"label": "Back to Overview"},
                          "navigation": {"action": "goToSheet", "sheet": "exec"}})])
varinput = entry({"qInfo": {"qId": "perf-vinput", "qType": "qlik-variable-input"}, "visualization": "qlik-variable-input",
                  "showTitles": True, "title": "Growth (vGrowth)", "variableName": "vGrowth", "render": "l",
                  "min": 0, "max": 0.2, "step": 0.01, "rangelabel": True, "updateondrag": False, "style": "qlik",
                  "variableValue": {"qStringExpression": {"qExpr": "=vGrowth"}}})
whatif = kpi("perf-whatif", "Sales x (1+vGrowth)",
             meas("Num(Sum({<Year={2026}>} Sales)*(1+vGrowth)/1e9,'€#,##0.00 bn')", "What-if Sales"))
perf_cells = [
    cell("perf-nav", "claude-nav", 0, 0, 24, 2),
    cell("perf-line", "linechart", 0, 2, 12, 5),
    cell("perf-pivot", "sn-pivot-table", 12, 2, 12, 5),
    cell("perf-container", "sn-layout-container", 0, 7, 12, 5),
    cell("perf-vinput", "qlik-variable-input", 12, 7, 12, 2),
    cell("perf-whatif", "kpi", 12, 9, 12, 3),
]
dump("objects/sheet-perf.json", entry(
    {"qInfo": {"qId": "perf", "qType": "sheet"}, "qMetaDef": {"title": "Sales Performance", "description": ""},
     "rank": 1, "columns": 24, "rows": 12, "cells": perf_cells},
    [NAV("perf-nav"), line, pivot, container, varinput, whatif]))
print("written")
