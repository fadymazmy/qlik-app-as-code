# Tickets

_The thirteen tickets the spec was split into, in build order. Numbers are those of the original issue tracker; the spec was #1._

## #2 One-command build of a minimal App

### Parent

#1

### What to build

One command takes an empty space to a working, verified App. It generates a small Synthetic Data set (a sales fact with Business Group and a calendar), uploads it, uploads the dark theme, creates the app under a given name, builds it from files, reloads it and verifies it. The App has one master measure (Sales) shown on one Sheet (Executive Overview), with the theme applied and Qlik's toolbar, sheet header and sheet navigation hidden. This is the tracer bullet: every later ticket extends a layer this one puts in place, including the Reference calculator, the verify command and the clean-up command.

### Acceptance criteria

- [ ] Running the build command against an empty space produces the App with no manual step
- [ ] Running it a second time succeeds and leaves the App unchanged
- [ ] The app name is a parameter, so two branches can build side by side in the same space
- [ ] A deliberately broken load script makes the build exit non-zero and print Qlik's reload error
- [ ] Sales evaluated in the App equals the Reference calculator's figure from the CSV files, in total and by Business Group
- [ ] The Executive Overview is captured as an image and the check fails when an object is empty or in error
- [ ] The clean-up command removes what the build created for a given app name and nothing else
- [ ] No tenant URL or key is in the repository

## #3 Full Synthetic Data with Planted Stories

### Parent

#1

### What to build

The generator produces the complete Valtera data set described in the spec's data model: about 500k sales rows over three years at daily grain in EUR, a monthly Budget, Order Intake, cost and the price inputs needed for price/volume/mix, with every dimension (Product Line within Business Group, Customer, Country within Region, Production Site, Channel, calendar). The load script loads it into a star schema and the App reloads cleanly.

### Acceptance criteria

- [ ] The same seed produces byte-identical files
- [ ] Every fact row references existing dimension rows
- [ ] Each of the three Planted Stories is asserted by a test on the generated files
- [ ] All company and Customer names are fictional
- [ ] The reloaded data model has no synthetic keys and no circular references
- [ ] Row counts and total Sales in the App match the CSV files

## #4 Core master measures

### Parent

#1

### What to build

The App carries the core master dimensions and master measures: Sales, Gross Margin (amount and percentage), Order Intake, Budget and Budget Attainment, each for the year to date, for Prior Year and for rolling 12 months, with the variances against Prior Year and Budget. They are relative to the latest date in the current selection and respect other selections.

### Acceptance criteria

- [ ] Every master measure equals the Reference calculator's figure with no selection
- [ ] The same holds under at least a Year, a Business Group, a Region, a Channel and a combined selection
- [ ] Amounts in billions display as in '€17.62 bn'
- [ ] Measure names use the glossary's terms

## #5 Complete dark theme

### Parent

#1

### What to build

The theme reproduces mock-up variant A for every native object type the Sheets use: sheet and card surfaces, border, radius, shadow, padding, title typography, chart palette, filter panes and selection colours, tables and text. The known open points from discovery (straight table text colour on dark, text object, colour of the remaining Qlik bar if it can be set) are resolved or documented with the closest achievable result.

### Acceptance criteria

- [ ] A sample Sheet holding one of each native object type renders in the dark design with no light surface or unreadable text
- [ ] Filter drop-downs and selection states are dark and their selection colour is distinct from the accent green
- [ ] The theme uses theme JSON and a font declaration only, with no CSS that targets Qlik's page structure
- [ ] Each open point is either fixed or recorded with what was tried and the fallback chosen

## #6 Navigation Bar on five Sheets

### Parent

#1

### What to build

The five Sheets exist and each carries the Navigation Bar, the first Custom Extension, built with Qlik's nebula tooling and uploaded by the build command. It lists the five Sheets with the current one marked, switches Sheet on click, shows the current selections, clears them, and carries the Synthetic Data label. The filter strip (Year, Business Group, Region, Channel) sits in the same place on every Sheet.

### Acceptance criteria

- [ ] Clicking a Sheet name in the Navigation Bar opens that Sheet
- [ ] The current Sheet is marked
- [ ] A selection made in a filter appears in the Navigation Bar, and 'Clear all' removes it
- [ ] The Synthetic Data label is visible on every Sheet
- [ ] The extension bundle makes no external network request and is uploaded under a claude- name by the build
- [ ] All five Sheets pass the capture check

## #7 Hero KPI Strip

### Parent

#1

### What to build

The Hero KPI Strip Custom Extension shows Sales, Gross Margin, Order Intake and Budget Attainment for the year to date, each with a sparkline and its variances against Prior Year and Budget, as in mock-up variant A. It only draws: every figure comes from a master measure.

### Acceptance criteria

- [ ] The four figures shown equal the corresponding master measures under any selection
- [ ] Favourable and unfavourable variances are marked by an arrow as well as colour
- [ ] The strip follows the theme's colours and typography
- [ ] It renders correctly on a Sheet built by the build command and passes the capture check

## #8 Sales Bridge

### Parent

#1

### What to build

Price, volume and mix effects of the Sales change against Prior Year exist as master measures, computed at Product Line by Customer level, and the Sales Bridge Custom Extension draws them from Prior Year to the current period.

### Acceptance criteria

- [ ] Each effect equals the Reference calculator's figure, with no selection and under several selections
- [ ] The three effects sum exactly to the Sales change
- [ ] The bridge shows start, the three effects and end, with favourable and unfavourable effects distinguishable without colour
- [ ] It renders correctly on a Sheet built by the build command and passes the capture check

## #9 Executive Overview

### Parent

#1

### What to build

The Executive Overview Sheet as approved in mock-up variant A: filter strip, Hero KPI Strip, Sales against Budget and Prior Year by month (both lines solid, told apart by colour), the Sales Bridge, Sales by Business Group, Sales by Region and top Customers.

### Acceptance criteria

- [ ] The Sheet matches the layout of mock-up variant A, object for object
- [ ] Every figure on the Sheet comes from a verified master measure
- [ ] Selecting a Business Group, Region or Customer updates every object
- [ ] The Sheet passes the capture check

## #10 Sales Performance

### Parent

#1

### What to build

The Sales Performance Sheet: Sales trend against Budget and Prior Year, the rolling 12 month view, and variance against Budget and Prior Year by Business Group, Region and Channel. The Aftermarket Planted Story is discoverable here.

### Acceptance criteria

- [ ] Trend, rolling 12 month and variance views are present and respond to selections
- [ ] Aftermarket's higher Gross Margin and lead over Budget is visible without prior knowledge of where to look
- [ ] Every figure comes from a verified master measure
- [ ] The Sheet passes the capture check

## #11 Customer and Region

### Parent

#1

### What to build

The Customer and Region Sheet: Customer concentration with cumulative share and ABC classes, Sales and Gross Margin by Region and Country, and a side-by-side comparison of two independent selections using two alternate states. The Customer concentration Planted Story is discoverable here.

### Acceptance criteria

- [ ] ABC classes and cumulative share equal the Reference calculator's figures
- [ ] Two different selections can be made side by side and each side's figures equal the Reference calculator's for that selection
- [ ] The dominant Customer in Propulsion is visible when Propulsion is selected
- [ ] The Sheet passes the capture check

## #12 Product Line and Margin

### Parent

#1

### What to build

The Product Line and Margin Sheet: Gross Margin by Product Line and Channel, margin trend, and the Sales Bridge with drill-in by Business Group. The Lighting in Asia Planted Story is discoverable here.

### Acceptance criteria

- [ ] Gross Margin by Product Line and Channel equals the Reference calculator's figures
- [ ] Selecting Lighting and Asia shows Gross Margin falling over the last 12 months while Sales grows, with the bridge showing a negative price effect
- [ ] The Sheet passes the capture check

## #13 What-If Simulator

### Parent

#1

### What to build

The What-If Simulator Sheet: the What-If Controls Custom Extension with sliders for price, volume and EUR exchange rate change, simulated Sales and Gross Margin shown next to actuals, and a reset. The simulated measures are master measures driven by three variables.

### Acceptance criteria

- [ ] Moving a slider recalculates simulated Sales and Gross Margin immediately
- [ ] For several slider settings and selections, the simulated figures equal the Reference calculator's
- [ ] Reset returns all three sliders to zero change and simulated figures equal actuals
- [ ] The controls follow the theme, with no white native slider on the Sheet
- [ ] The Sheet passes the capture check

## #14 The repository as an example

### Parent

#1

### What to build

The repository reads as a worked example a teammate can follow. The README explains the method step by step with the exact commands and carries the Synthetic Data notice at the top. A full build into a fresh app passes every check. Final screenshots of the five Sheets are in the repository. The scratch artifacts left by discovery are removed from the tenant.

### Acceptance criteria

- [ ] The README starts with the Synthetic Data notice and takes a teammate from a fresh clone and their own key to a built, verified App
- [ ] A build under a new app name in the space passes the generator tests, the measure comparison and the capture check for all five Sheets
- [ ] A second run changes nothing
- [ ] Final screenshots of all five Sheets are committed
- [ ] CLAUDE.md reflects the rules actually followed during the build
- [ ] The discovery scratch app, test theme and test extension no longer exist on the tenant
- [ ] No secret or tenant URL is anywhere in the repository history
