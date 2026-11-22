# Valtera Sales Dashboard

A Qlik Sense app over synthetic sales data for Valtera, a fictional automotive supplier, built entirely from code to show the team what goes beyond regular BI dashboard development.

## Language

### The demo

**App**:
The single Qlik Sense app the team opens in the Qlik Cloud hub; the whole deliverable alongside the repo.
_Avoid_: Dashboard (as a name for the whole thing), mashup, report

**Sheet**:
One page of the App. There are five: Executive Overview, Sales Performance, Customer and Region, Product Line and Margin, What-If Simulator.
_Avoid_: Page, tab, dashboard

**Custom UI**:
The App's look and layout where it departs from Qlik's defaults, produced only by a custom theme, native objects and Custom Extensions. Never a separate web page.
_Avoid_: Mashup, front end

**Custom Extension**:
A visualization written for this project and uploaded to the tenant, used where no native Qlik object can produce the design. There are four: the Navigation Bar, the Hero KPI Strip, the Sales Bridge and the What-If Controls.
_Avoid_: Plugin, widget

**Navigation Bar**:
The Custom Extension at the top of every Sheet that shows the five Sheets, the current selections and the Synthetic Data label, replacing Qlik's own sheet navigation.
_Avoid_: Menu, header, toolbar

**Hero KPI Strip**:
The Custom Extension that shows Sales, Gross Margin, Order Intake and Budget Attainment together, each with its trend and variances.
_Avoid_: KPI cards, scorecard

**Sales Bridge**:
The Custom Extension that explains the change in Sales against Prior Year as volume, price and mix effects.
_Avoid_: Waterfall, PVM chart

**What-If Controls**:
The Custom Extension on the What-If Simulator that holds the sliders for price, volume and exchange rate.
_Avoid_: Sliders, variable input, inputs

**Synthetic Data**:
Generated sales data that imitates an automotive supplier's business but describes no real company or transaction. Every Sheet labels it as such.
_Avoid_: Sample data, dummy data, test data

**Planted Story**:
A pattern deliberately built into the Synthetic Data for the demo to uncover, such as one Business Group losing margin in one Region.
_Avoid_: Insight, anomaly

### The business

**Valtera**:
The fictional automotive supplier whose sales the App analyses.
_Avoid_: The company, the client

**Business Group**:
One of Valtera's three top-level divisions: Propulsion, Driving Intelligence, Lighting.
_Avoid_: Division, business unit, segment

**Product Line**:
A family of products inside one Business Group.
_Avoid_: Category, product group

**Customer**:
A fictional carmaker group that buys from Valtera. Never a consumer, and never a real carmaker's name.
_Avoid_: Client, account, OEM (as a synonym for Customer)

**Region**:
The part of the world where the Customer takes delivery, such as Europe or North America. Each Region contains Countries.
_Avoid_: Market, geography, territory

**Channel**:
How a sale reaches the market: Original Equipment (parts fitted in new vehicles) or Aftermarket (replacement parts).
_Avoid_: Segment, market

**Production Site**:
The Valtera plant that made the goods sold.
_Avoid_: Plant, factory, location

**Sales**:
Invoiced revenue in EUR.
_Avoid_: Revenue, turnover

**Gross Margin**:
Sales minus the cost of the goods sold, shown as a percentage of Sales unless stated as an amount.
_Avoid_: Margin (unqualified), profit, GM

**Order Intake**:
The value of new orders booked in a period, whether or not yet invoiced.
_Avoid_: Bookings, orders

**Book-to-bill**:
Order Intake divided by Sales for the same period. Above 1 means more was ordered than invoiced.
_Avoid_: Book-to-bill ratio, BTB, order coverage

**Budget**:
The planned Sales for a period, against which actual Sales is compared.
_Avoid_: Target, plan, forecast

**Budget Attainment**:
Actual Sales as a percentage of Budget for the same period.
_Avoid_: Achievement, performance vs plan

**Prior Year**:
The same period one year earlier, used as the baseline for year-on-year comparison.
_Avoid_: Last year, PY, previous year

**Latest Date**:
The last day with Sales in the current selection. Every YTD and Rolling 12 Months figure ends on it.
_Avoid_: Today, as-of date, reporting date

**YTD**:
Year to date: from 1 January of the Latest Date's year through the Latest Date.
_Avoid_: CY, current year

**ABC class**:
A Customer's rank in the Customer concentration: A while the cumulative share of Sales YTD (the Customer's plus that of every larger Customer) is up to 80%, B up to 95%, C the rest.
_Avoid_: Tier, segment, Pareto class

**Rolling 12 Months**:
The twelve months ending on the Latest Date.
_Avoid_: R12, LTM, TTM, moving annual total

**Volume**:
The number of units sold.
_Avoid_: Quantity, units

**Volume Effect**, **Price Effect**, **Mix Effect**:
The three parts of the change in Sales against Prior Year: more or fewer units at last year's average price, a different price for the same Product Line and Customer, and a shift of Volume between Product Lines and Customers. They add up exactly to the change; `docs/measures.md` has the definition.
_Avoid_: PVM, variance (for an effect)

**Scenario**:
A price change, a volume change and an EUR exchange rate change, set together on the What-If Simulator. Zero on all three is no change.
_Avoid_: Simulation, case, what-if (as a noun)

**Simulated**:
A figure recalculated under the current Scenario, such as Simulated Sales YTD. See `docs/measures.md` for the model.
_Avoid_: Projected, forecast, adjusted

**Actual**:
A figure as the Synthetic Data records it, as opposed to Simulated or Budget.
_Avoid_: Real, baseline, as-is

**EUR exchange rate change**:
The change in the value of the euro against every other currency at once: +10% means one euro buys 10% more of each, so an amount in another currency is worth 1/1.10 of its EUR value.
_Avoid_: FX change, currency effect
