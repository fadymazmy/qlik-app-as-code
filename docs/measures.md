# Master measures and master dimensions

The rules every master measure follows, the names to reference them by, and how to add one. The App definition is `app/measures.json`, `app/dimensions.json` and `app/variables.json`; the independent second implementation is `valtera/reference.py`.

## Time rules

- **Latest Date**: the last Date that has Sales in the current selection (`vLatestDate` = `Max(If(Sales, Date))`). Budget and Order Intake rows do not move it, and neither does a calendar day without Sales.
- **YTD**: 1 January of the Latest Date's year through the Latest Date.
- **Rolling 12 Months**: the day after the Latest Date one year earlier, through the Latest Date.
- **Prior Year** of a window: the same window one year earlier. YTD Prior Year runs from 1 January of the year before through the Latest Date one year earlier; Rolling 12 Months Prior Year ends on that same day. One year earlier is the same day and month, and 29 February becomes 28 February (Qlik's `AddYears`).
- A windowed measure replaces any selection in the calendar fields (Date, Year, Quarter, Month, Year Month) by its own days and keeps every other selection. Selecting Year 2025 therefore gives YTD = all of 2025 and YTD Prior Year = all of 2024; selecting a Month or a Date moves the Latest Date back to the last day with Sales in it.
- What the generated data does: it runs from 2024-01-01 to 2026-12-31 (full years, `LAST_DAY` in `valtera/data.py`), unlike the mock-up's "YTD Oct 2026". With no selection the Latest Date is 2026-12-31, so YTD and Rolling 12 Months are both the whole of 2026. Selecting Month = Oct gives the mock-up's "YTD Oct 2026".

## Budget

Budget is at month grain (rows dated the 1st of the month, Product Line by Country by Channel). In a window, **each month's Budget is spread evenly over the calendar days of its month**, and the window gets the share of the days it covers (`vBudget(first, last)`). A window ending on 15 June gets 15/30 of June's Budget, against Sales through 15 June; a window ending on a month end gets whole months. This keeps Budget Attainment fair when the Latest Date falls mid-month, which is what happens when the data stops part-way through a month.

- The measures without a window (`Budget`, `Budget Attainment`) use the Budget rows in the selection as they are, in whole months, for charts by month.
- Budget has no Customer and no Production Site. Under a selection that narrows either, **every Budget measure is null** (Budget, Budget Attainment, `vs Budget`, in every window), so no Sheet shows a Budget comparison there: each wraps its expression in `If($(vBudgetDefined), …)`. `vBudgetDefined` compares the Customers (and Production Sites) the selection allows with those it would allow without its own selection in that field, inside the object's state, so it also holds on the alternate-state side of the comparison. The Hero KPI Strip says "No Budget by Customer or Production Site" instead of a figure.
- There is no Gross Margin Budget, so Gross Margin has no variance against Budget.

## Names

Measure names use `GLOSSARY.md` terms. The pattern is `<figure>[ <window>][ Prior Year][ vs <baseline>][ %]`:

- figure: `Sales`, `Gross Margin Amount` (EUR), `Gross Margin` (percentage of Sales, as in the glossary), `Order Intake`, `Budget`, `Budget Attainment`
- window: none (the selection as it is), `YTD`, `Rolling 12 Months`; then optionally `Prior Year`
- variance: `vs Prior Year` or `vs Budget` is a difference (EUR for amounts, percentage points for `Gross Margin` and `Budget Attainment`); a trailing `%` makes it a relative change

The id is `m_` plus the name in lower case with `%` as `pct` and every other run of non-alphanumerics as `_`: `Sales YTD vs Prior Year %` is `m_sales_ytd_vs_prior_year_pct`. Objects reference a master measure as `{"qLibraryId": "<id>", "qDef": {}}`.

| Figure | No window | YTD | Rolling 12 Months |
|---|---|---|---|
| Sales | `Sales` | `Sales YTD`, `Sales YTD Prior Year`, `Sales YTD vs Prior Year`, `Sales YTD vs Prior Year %`, `Sales YTD vs Budget`, `Sales YTD vs Budget %` | the same with `Rolling 12 Months` in place of `YTD` |
| Gross Margin Amount | `Gross Margin Amount` | `… YTD`, `… YTD Prior Year`, `… YTD vs Prior Year`, `… YTD vs Prior Year %` | likewise |
| Gross Margin | `Gross Margin` | `… YTD`, `… YTD Prior Year`, `… YTD vs Prior Year` (pp) | likewise |
| Order Intake | `Order Intake` | `… YTD`, `… YTD Prior Year`, `… YTD vs Prior Year`, `… YTD vs Prior Year %` | likewise |
| Budget | `Budget` | `… YTD`, `… YTD Prior Year` | likewise |
| Budget Attainment | `Budget Attainment` | `… YTD`, `… YTD Prior Year`, `… YTD vs Prior Year` (pp) | likewise |

The table holds the measures by figure and window; `app/measures.json` holds every master measure, those of the sections below included. Master dimensions (id `d_` plus the name the same way, each on the field of the same name): Date, Year, Quarter, Month, Year Month, Business Group, Product Line, Customer, Region, Country, Production Site, Channel.

## Display

Qlik's number formats cannot scale a value, and the KPI object ignores an expression's own text (a `Dual` in EUR showed `17.67 bn` with Auto formatting, and the raw number with `qType "R"`). So each measure returns its value in the unit it is shown in, and carries the same format twice: in the expression (`Num(x, '<format>')`, for tables, extensions and `qlik app eval`) and as the master measure's number format (`qNumFormat {qType "F", qFmt "<format>"}`, `isCustomFormatted: true`, `numFormatFromTemplate: false`, which objects that reference the measure use).

| Unit | Value | Format | Shows |
|---|---|---|---|
| EUR bn (amounts) | EUR / 1e9 | `€#,##0.00 bn;-€#,##0.00 bn`; variances `+€#,##0.00 bn;-€#,##0.00 bn` | `€17.62 bn`, `-€0.33 bn` |
| ratio (percentages, relative variances) | 0.25 = 25% | `0.0%`; variances `+0.0%;-0.0%` | `20.4%`, `+2.8%` |
| pp (difference of two percentages) | percentage points | `+0.0 pp;-0.0 pp` | `-0.8 pp` |
| EUR m (small amounts, the Product Line and Margin Sheet) | EUR / 1e6 | `€#,##0.0 m;-€#,##0.0 m`; variances `+€#,##0.0 m;-€#,##0.0 m` | `€184.3 m`, `-€41.3 m` |

A Custom Extension reads `qNum` in that unit and can show `qText` as it is.

**Amounts in EUR m.** A Product Line's amounts read `€0.01 bn` in EUR bn, so the Product Line and Margin Sheet shows EUR m. The amounts the Sheet needs exist a second time as `<name> in EUR m` (id `m_<name>_in_eur_m`), listed in `IN_EUR_M` in `valtera/reference.py`. Each is its EUR bn measure divided by 1e6 instead of 1e9, with the EUR m format; the Reference calculator gives each the EUR bn figure times 1,000 (checked to 1e-8 m), and verify checks that it reads `€x,xxx.x m`. The Sales Bridge shows whichever unit its measures carry (one decimal in EUR m).

## Variables for new expressions

| Variable | Use |
|---|---|
| `vYTD`, `vYTDPriorYear`, `vRolling12Months`, `vRolling12MonthsPriorYear` | set modifiers: `Sum({<$(vYTD)>} Sales)` |
| `vDays(first, last)` | set modifier for any days, as day numbers |
| `vBudget(first, last)` | Budget for any days, spread over days: `$(vBudget($(vYTDFirstDay), $(vLastDay)))` |
| `vLastDay`, `vPriorYearLastDay`, `vYTDFirstDay`, `vYTDPriorYearFirstDay`, `vRolling12MonthsFirstDay`, `vRolling12MonthsPriorYearFirstDay` | the window bounds as day numbers |
| `vLatestDate` | the Latest Date expression |

A set search on `Date` must use formatted dates (`">=2026-01-01<=2026-06-15"`, which `vDays` builds); a numeric range search and an `=Date>=…` expression search both return nothing for days outside the current selection.

## Adding a master measure

1. Add an entry to `app/measures.json` (id and name as above, `qDef` built from the variables and wrapped in `Num(…, '<format>')`, the same format in `qNumFormat`, see Display, and `qMetaDef.description` saying what it is).
2. Add its figure to `Reference.figures` in `valtera/reference.py`, computed from the CSV rows with Python and the rules above, never by translating the Qlik expression. Give it the App's unit: `_bn(eur)` (checked to the cent, and its text must read `€x.xx bn`), `Figure(x, "ratio")` (checked to 1e-9) or `_pp(a, b)`. An amount that a Sheet shows in EUR m also gets its `<name> in EUR m` measure in `app/measures.json` and its name in `IN_EUR_M` (see Display).
3. Run `.venv/bin/python -m valtera build <app-name>`. Verify compares every master measure in the App with the figure of the same name in each of its selections (`SELECTIONS` in `valtera/verify.py`), and fails on a measure that exists on one side only.

## Customer concentration

On the Customer and Region Sheet: a Pareto chart of the ten largest Customers (a dimension limit, so every name fits without a scrollbar; its line is still the cumulative share of all Customers) and a table of every Customer. The base is **Sales YTD**, so every Customer is measured over the same days, ending on the selection's Latest Date (with no selection, all of 2026).

- `Customer Share`: a Customer's Sales YTD as a share of the Sales YTD of all Customers in the selection (100% outside a chart).
- `Customer Cumulative Share`: in a chart by Customer, the Customer's share plus that of every Customer with larger Sales YTD. It does not depend on the order the chart shows: it runs `Above` inside an `Aggr` sorted by Sales YTD (`Aggr(…, (Customer, (=Sum({<$(vYTD)>} Sales), Descending)))`) and reads it back with `Sum(TOTAL <Customer> …)`, which lifts the chart row's restriction so the `Aggr` sees every Customer. A person re-sorting the table by a column therefore changes nothing; verify checks it in the engine's own (name) order as well. Null outside a chart.
- `Customer ABC Class`, at fixed thresholds of the cumulative share: **A up to 80%, B up to 95%, C the rest** (a Customer whose cumulative share is exactly 80% is A). It is a dual (`A` = 1, `B` = 2, `C` = 3), so it shows the letter and sorts by class. Null outside a chart.
- Sort such a chart by its Customer dimension (`qSortCriterias` by the expression `Sum({<$(vYTD)>} Sales)`, descending, and the dimension first in `qInterColumnSortOrder`). A sort by a measure column is silently ignored in a hypercube that contains `Above`, and the Customers then come in name order.
- An expression can reference a master measure by name: colour expressions use `[Customer Share]` and `[Customer ABC Class]` instead of repeating them. A column can show a shorter label than the master measure's name with `qDef.qLabelExpression` (`"='Share'"`).
- The Customer table marks a share above 25% of Sales YTD in amber: a single Customer that large is a concentration risk (with Propulsion selected, Kestova Motors holds about 30%).

Verify reads the Customer table on the Sheet (`cr-customers`) in each of `CONCENTRATION_SELECTIONS` (`valtera/verify.py`) and checks every Customer's place, share, cumulative share and ABC class against `Reference.customers`. `app eval` cannot sort, so verify makes the selection in a kept engine session (`--ttl`) and reads the table's layout in that session.

## Sales Bridge: volume, price and mix effects

`Sales YTD vs Prior Year` split into three effects, for the Sales Bridge. Three master measures, in EUR bn with the variance format (`+€0.17 bn`):

| Name | Id |
|---|---|
| `Volume Effect YTD vs Prior Year` | `m_volume_effect_ytd_vs_prior_year` |
| `Price Effect YTD vs Prior Year` | `m_price_effect_ytd_vs_prior_year` |
| `Mix Effect YTD vs Prior Year` | `m_mix_effect_ytd_vs_prior_year` |

The definition:

- **Windows**: YTD against YTD Prior Year, by the time rules above (a selection in the calendar fields is replaced, every other selection is kept).
- **Cells**: Product Line by Customer. For each cell, Sales `S` and Volume `V` in YTD (`S1`, `V1`) and in YTD Prior Year (`S0`, `V0`); a cell's price is `S / V`. Totals over all cells in the selection are `S1`, `V1`, `S0`, `V0`, and `P0 = S0 / V0` is the Prior Year average price.
- **Volume Effect** = `(V1 - V0) × P0`: the change in units, at last year's average price.
- **Price Effect** = the sum, over the cells with Volume in both windows, of `S1 - V1 × S0 / V0`: this year's units of each cell at this year's price against its Prior Year price.
- **Mix Effect** = the sum, over the cells with Volume this year, of `V1 × p0`, minus `V1 × P0`: this year's units at each cell's Prior Year price `p0`, against the same units at the Prior Year average price. It is what the change in the cells' shares of Volume is worth.
- **Cells in one window only**: a cell new this year has no Prior Year price, so it takes `p0` = its own price this year; it has no Price Effect, and its Sales count in Volume and Mix. A cell lost since Prior Year has `V1 = 0`; it has no Price Effect, and its Prior Year Sales count in Volume and Mix (through `V0` and `S0`).
- **They sum exactly**: Volume + Price + Mix = `S1 - S0` = `Sales YTD vs Prior Year`, as an identity. In the App, Mix is computed as `Sales YTD vs Prior Year` minus Volume minus Price, so any floating-point remainder lands in Mix and the three add up to the Sales change to the last digit the engine holds; verify checks that sum, and checks Mix itself against the Reference calculator, which computes it from the definition above in exact fractions.
- **No Prior Year Sales in the selection** (`V0 = 0`, for example Year 2024): the whole change is Volume Effect; Price and Mix are 0. The Sales Bridge does not draw that: it shows a "No Prior Year" state instead. An effect that rounds to zero at the bridge's decimals shows as `0.00` with no arrow.

The App computes the Price Effect with `Aggr()` over `[Product Line ID]` and `[Customer ID]` (the key fields in Facts, faster than the names in the dimension tables), with the YTD set both on the `Aggr()` and on the `Sum()` around it: without the set on the `Sum()`, a selection in the calendar fields (such as one Date) removes the cells that have no Sales in it, and the Price Effect comes out too small. The raw EUR expressions are the variables `vVolumeEffectYTD` and `vPriceEffectYTD`; the measures divide them by 1e9 and format them.

## What-If Simulator

A Scenario is three variables in whole percent, written by the What-If Controls (sliders from -20 to +20 in steps of 1; 0 is no change): `vPriceChange`, `vVolumeChange` and `vExchangeRateChange`. The simulated measures apply them to YTD and respond to every selection the way the YTD measures do. All three at 0 gives the Actual figures exactly.

### The model

- **Price change p**: net prices change by p; the units sold and the cost per unit do not. Sales × (1 + p), cost unchanged, so the whole change in Sales lands in Gross Margin Amount.
- **Volume change v**: units sold change by v at the same net prices and cost per unit. Sales and cost both × (1 + v): Gross Margin Amount scales by (1 + v) and Gross Margin (%) stays as it is. Cost here is the cost of goods sold, taken as wholly variable.
- **EUR exchange rate change e**: Valtera reports in EUR, so this is translation only (no change in local prices or volumes). e is the change in the value of the euro against every other currency at once: +10% means one euro buys 10% more of each, so an amount in another currency is worth 1 / 1.10 of its EUR value (-9.1%, not -10%).
- **The exchange rate assumption** (the data has no transaction currency; the What-If Controls state it on the Sheet): Sales to a Country in the euro area (Germany, France, Spain, Italy: `vEuroArea`, written without quotes so that the Sheet can show it) is in EUR. Sales to every other Country, the United Kingdom, the Czech Republic and Poland included, is invoiced in that Country's currency, and 60% of its cost (`vLocalCostShare`) is in that currency too (the plants serving each Region pay local wages, energy and suppliers); the other 40% is bought in EUR. A stronger euro therefore lowers Sales outside the euro area by the full translation and their cost by 60% of it, and Gross Margin falls.
- **All three together**, per sales row: Simulated Sales = Sales × (1 + p) × (1 + v) × t and simulated cost = cost × (1 + v) × (0.6 × t + 0.4), where t = 1 / (1 + e) outside the euro area; inside it t = 1 and cost is not translated. Prices are set in the invoice currency, then translated.

### Names

The pattern is `Simulated <figure> YTD[ vs Actual][ %]`, where `vs Actual` is the simulated figure minus the same figure without `Simulated` (EUR for amounts, percentage points for `Gross Margin`) and a trailing `%` makes it a relative change. Units and formats are those of Display.

| Master measure | Unit |
|---|---|
| `Simulated Sales YTD`, `Simulated Sales YTD vs Actual` | EUR bn |
| `Simulated Sales YTD vs Actual %` | ratio |
| `Simulated Gross Margin Amount YTD`, `Simulated Gross Margin Amount YTD vs Actual` | EUR bn |
| `Simulated Gross Margin YTD` | ratio |
| `Simulated Gross Margin YTD vs Actual` | pp |

New simulated measures are built from `$(vSimulatedSalesYTD)` and `$(vSimulatedCostYTD)` (in EUR). In the Reference calculator a scenario is `Reference.figures(selection, Scenario(price, volume, exchange_rate))`. Verify checks the simulated measures in each of `SCENARIOS` in `valtera/verify.py`, a selection with a value for each variable: it sets the variables with `qlik app variable set` (which saves the App), compares, and restores the definitions it found. The `SELECTIONS` run with the variables at 0, as the build leaves them.

### How the What-If Controls write a variable

The extension calls the Engine API through nebula's `useApp()`: `app.getVariableByName('vPriceChange')` gives the variable's handle and `setNumValue(5)` sets it; every object that uses the variable recalculates at once. It reads the current values back through its own layout: its properties hold `{"qValueExpression": {"qExpr": "$(vPriceChange)"}}`, which the engine re-evaluates whenever the variable changes, so a change from anywhere (another tab, verify, Reset) shows on the sliders.

A slider change lives in the viewer's engine session and is not saved in the App: a new `qlik` CLI session still reads 0. Qlik Cloud shares that session between every tab and browser of the same user on the same App, so a Scenario left in one tab also shows in another, and in the Sheet capture when it runs as that user (seen during ticket #13: after a full build, the capture still showed sliders left at +8% in a tab). Reset returns to 0.

## Book-to-bill

`Book-to-bill YTD` (`m_book_to_bill_ytd`): Order Intake YTD divided by Sales YTD, the same days for both, by the YTD rule above. Above 1 means more was ordered than invoiced. It is a plain ratio shown with two decimals (format `0.00`, `1.10`), not a percentage, so the Reference calculator gives it the `ratio` unit (checked to 1e-9). Null when Sales YTD is 0. It has no favourable direction and is shown without an arrow or colour, on the Order Intake tile of the Hero KPI Strip.

## Product Line and Margin

The Sheet shows the YTD Gross Margin measures and the Sales Bridge measures above, with its amounts in EUR m (see Display), by Business Group, Product Line, Channel, Region and Year Month.

- **Every cell is checked.** Verify reads the layout of each object on the Sheet (`MARGIN_OBJECTS` in `valtera/verify.py`: the Product Line by Channel pivot, the Business Group by Region change table, the monthly trend and the Sales Bridge) in each of `MARGIN_SELECTIONS`, and compares every cell with the Reference calculator's figure for the selection narrowed to the cell's own dimension values (a total cell adds none); a cell keeps the selection's Latest Date, as every window in a chart ends on it. With Lighting and Asia selected it also checks the Planted Story as the Sheet shows it: the trend's Gross Margin falls by more than 5 points across its last 12 months, Sales of those months exceed the 12 before, and the bridge shows a negative Price Effect beside a positive Volume Effect.
- **Colour thresholds.** A Gross Margin change of half a point or more is red (down) or green (up) in the Product Line by Channel table; smaller moves keep the text colour. The change table by Region shades a cell from one point (pale) and three points (strong), so the Lighting in Asia cell (about -7 pp) stands out with no selection.
- **The drill-in by Business Group** is a listbox on Business Group beside the bridge: one click selects that Business Group for the whole Sheet, and the bridge, whose title names the Business Group it shows, redraws for it.
- **The trend uses a continuous month axis.** On a discrete axis the combo chart scrolls after about 17 of the 36 months, which hides the last 12. On the continuous axis all months fit; the axis labels years (dates when one Year is selected), and the mini chart under it is switched off (`showMiniChartForContinuousAxis`).
