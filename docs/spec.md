# Spec

_Copied from the issue tracker of the repository where the App was first built. The deviations recorded during the build follow the spec._

> All data in this project is Synthetic Data. Valtera is a fictional company and its Customers are fictional carmakers.

Vocabulary follows `GLOSSARY.md`. Decisions already recorded: `docs/adr/0001-custom-ui-stays-inside-qlik.md`. Verified facts about the tenant and working object JSON: `docs/research/tenant-discovery.md` and `docs/research/object-examples/`. Approved design: `prototype/executive-overview/` (variant A).

## Problem Statement

Our BI team builds Qlik Sense apps by hand in the Qlik UI. The results look like every other Qlik app, the analytics stop at what is quick to click together, nothing can be reviewed or rebuilt from a repository, and nobody has shown the team what is possible when an AI agent does the development. The team needs a concrete, repeatable demonstration that goes beyond regular BI dashboard development, and a worked example to copy.

## Solution

One Qlik Sense App on Qlik Cloud, built entirely from code in this repository by Claude, and the repository itself as the example the team follows.

The App analyses Synthetic Data for Valtera across five Sheets (Executive Overview, Sales Performance, Customer and Region, Product Line and Margin, What-If Simulator). It proves three things at once:

1. **Built as code**: a single command generates the data, uploads it, builds the App, reloads it and verifies it, in an empty space, with no clicking in the Qlik UI.
2. **Analytical depth**: time intelligence against Budget and Prior Year, price/volume/mix decomposition, Customer concentration, side-by-side comparison of two selections, and live what-if simulation.
3. **Custom UI**: a dark, product-style look that does not resemble an out-of-the-box Qlik app, produced only with a custom theme, native objects and four Custom Extensions.

## User Stories

### Building and rebuilding

1. As a BI developer, I want one command that builds the whole App from the repository, so that I can reproduce the demo without clicking in the Qlik UI.
2. As a BI developer, I want the command to work in an empty space on any Qlik Cloud tenant I have a key for, so that I can run the example on my own tenant.
3. As a BI developer, I want running the command twice to leave the App in the same state, so that I can rebuild safely after any change.
4. As a BI developer, I want the build to stop with the reload error text when the load script fails, so that I can see what is wrong without opening Qlik.
5. As a BI developer, I want to build into an app named after my branch, so that my work does not overwrite a teammate's or the demo App.
6. As a BI developer, I want the API key to stay in my local `qlik-cli` context and never appear in the repository, so that sharing the repo leaks nothing.
7. As a tenant admin, I want everything the build creates to live in one named space and to carry a `claude-` name prefix where it is tenant-wide, so that I can tell it apart and remove it.
8. As a tenant admin, I want a command that removes what the build created, so that the tenant can be cleaned up after the demo.

### Synthetic Data

9. As a demo presenter, I want sales data that looks like an automotive supplier's business (Business Groups, Product Lines, Customers, Regions and Countries, Production Sites, Channels), so that the App tells a believable story.
10. As a demo presenter, I want three years of history at daily grain with seasonality, so that trends and year-on-year comparisons look real.
11. As a demo presenter, I want Budget and Order Intake alongside Sales, so that attainment and book-to-bill can be shown.
12. As a demo presenter, I want the data to contain the three Planted Stories, so that the demo has findings to uncover.
13. As a BI developer, I want the same seed to produce identical files, so that verified numbers stay valid on every rebuild.
14. As a viewer, I want every Sheet to state that the data is synthetic, so that nobody mistakes the figures for a real company's.
15. As a viewer, I want fictional company and Customer names, so that the App cannot be read as describing a real business.

### Analytics

16. As an executive, I want Sales, Gross Margin, Order Intake and Budget Attainment for the year to date, so that I see the state of the business at a glance.
17. As an executive, I want each headline figure compared with Prior Year and with Budget, so that I know whether it is good or bad.
18. As an analyst, I want rolling 12 month versions of the measures, so that seasonality does not distort the trend.
19. As an analyst, I want every time comparison to respect my current selections, so that I can ask the same question of any Business Group, Region or Customer.
20. As an analyst, I want the change in Sales against Prior Year split into volume, price and mix effects, so that I can explain why Sales moved.
21. As an analyst, I want the three effects to add up exactly to the total change, so that the explanation is trustworthy.
22. As an analyst, I want to see how much of Sales the largest Customers account for, with ABC classes, so that I can judge concentration risk.
23. As an analyst, I want to compare two independent selections side by side, so that I can set, for example, Propulsion in Europe against Lighting in Asia.
24. As an analyst, I want Gross Margin by Product Line and Channel, so that I can find where margin is made and lost.
25. As a planner, I want sliders for price, volume and EUR exchange rate that recalculate Sales and Gross Margin immediately, so that I can test scenarios in a meeting.
26. As a planner, I want the simulated figures shown next to the actual ones, so that I see the effect of my scenario.
27. As a planner, I want a way to reset the sliders, so that I can return to actuals.
28. As a demo presenter, I want each Planted Story to be discoverable on at least one Sheet, so that the demo can walk through them.

### Custom UI

29. As a viewer, I want a dark design with one consistent look across all Sheets, so that the App feels like a product and not a default Qlik app.
30. As a viewer, I want Qlik's own toolbar, sheet header and sheet navigation hidden, so that only the App's own interface shows below the Qlik bar that cannot be removed.
31. As a viewer, I want a Navigation Bar on every Sheet listing the five Sheets with the current one marked, so that I always know where I am and can move in one click.
32. As a viewer, I want the Navigation Bar to show my current selections and let me clear them, so that I never lose track of what I filtered.
33. As an executive, I want a Hero KPI Strip that shows the four headline figures with a trend line and variances, so that the first thing I see is the answer.
34. As a viewer, I want favourable and unfavourable variances marked by an arrow as well as by colour, so that I can read them without relying on colour.
35. As an analyst, I want a Sales Bridge that draws the volume, price and mix effects from Prior Year to the current period, so that the explanation is visual.
36. As a planner, I want What-If Controls that match the App's design, so that the simulator does not look like a different product.
37. As a viewer, I want filters for Year, Business Group, Region and Channel in the same place on every Sheet, so that filtering works the same everywhere.
38. As a viewer, I want large amounts shown as "€17.62 bn", so that figures are readable.
39. As a viewer, I want native charts and tables to follow the same colours and typography as the Custom Extensions, so that I cannot tell which is which.

### Verification

40. As a BI developer, I want every master measure checked against the same figure computed independently from the CSV files, so that I can trust the numbers on screen.
41. As a BI developer, I want those checks run across several selections, so that set analysis errors that only appear under a filter are caught.
42. As a BI developer, I want each Sheet captured as an image and the check to fail when any object is empty or in error, so that a broken Sheet cannot ship unnoticed.
43. As the project owner, I want to walk the five Sheets in the browser and accept the look, so that the final judgement on design is mine.

### The repository as an example

44. As a teammate, I want a README that explains the method step by step with the exact commands, so that I can repeat it on my own app.
45. As a teammate, I want the rules Claude followed written in `CLAUDE.md`, so that my own Claude session behaves the same way.
46. As a teammate, I want the spec, the tickets and the decision records kept with the repository, so that I can see how the work was specified, split and decided.
47. As a teammate, I want the research and tenant discovery notes kept, so that I do not have to rediscover Qlik's undocumented behaviour.

## Implementation Decisions

### Environment

- Qlik Cloud tenant, reached through `qlik-cli` using the active local context. The repository never stores the tenant URL or the key.
- Everything is created in one shared space, `claude-dashboard-dev`. The theme and extensions are tenant-wide and carry a `claude-` name prefix (Qlik assigns their ids).
- An app that the build writes to is never edited in the Qlik UI.
- The extension tooling needs Node 24. The data generator and the verification use Python 3.

### Modules

- **Data generator**: a seeded Python program that writes the CSV files. Interface: seed and size in, files out. It owns the Planted Stories as explicit, named parameters.
- **Reference calculator**: Python functions that compute every master measure straight from the CSV files for a given selection. It is the independent source of truth for verification and shares no code with the load script or the Qlik expressions.
- **App definition**: the load script, master dimensions, master measures, variables, alternate states, Sheets and objects, kept as files. Each object is the Qlik client's full default property tree with this project's overrides applied, because the client does not fill in missing defaults and a partial tree crashes bar and combo charts. Sheets are stored in the `{qProperty, qChildren}` form.
- **Theme**: one dark theme, expressed through theme JSON (and a font declaration). No CSS that targets Qlik's page structure.
- **Custom Extensions**: Navigation Bar, Hero KPI Strip, Sales Bridge, What-If Controls, built with nebula.js as self-contained bundles with no external network origin. They only draw: every number they show comes from a master measure or variable defined in the App.
- **Build command**: the single entry point. In order: generate data, ensure the space, upload the data files, upload the theme and extensions, create or find the app, build it from the App definition, add alternate states, reload, verify. It takes an app name so that each branch builds its own app, and it is idempotent.
- **Verify command**: runs the measure comparison and the Sheet capture, and exits non-zero on any failure.
- **Clean-up command**: removes what the build created for a given app name.

### Data model

- Star schema: one sales fact at daily grain (Sales, Volume, cost, list and net price inputs needed for price/volume/mix), one Budget fact at monthly grain, one Order Intake fact, and dimensions for Product Line (with Business Group), Customer, Country (with Region), Production Site, Channel and a master calendar.
- Facts at different grains are related through the shared dimensions without synthetic keys or circular references.
- About 500k sales rows over three years, in EUR.
- Planted Stories: Lighting loses Gross Margin in Asia over the last 12 months while Sales grows; one Customer grows to a dominant share of Propulsion Sales; Aftermarket is small, has about twice the Gross Margin of Original Equipment and is ahead of Budget.

### Analytics

- All time intelligence is master measures using set analysis, relative to the latest date in the current selection, and respects other selections.
- Price/volume/mix is computed at Product Line by Customer level against Prior Year, and the three effects sum exactly to the Sales change.
- Customer concentration uses cumulative share with ABC classes at fixed thresholds.
- Side-by-side comparison uses two alternate states. States are added with the CLI's state command; states declared only in app properties do not work.
- What-if uses three variables (price change, volume change, exchange rate change) applied in simulated versions of Sales and Gross Margin.
- No statistical forecast.

### Custom UI

- Design reference: mock-up variant A. The theme sets sheet and object background, border, radius, shadow, padding, title typography, palette and filter and selection colours.
- The app's theme and the hidden toolbar, sheet header and navigation are set through the app properties object, by theme name.
- A Qlik bar of about 47 px remains at the top and is accepted (ADR 0001).
- In the Sales against Budget and Prior Year chart, both lines are solid and told apart by colour, because Qlik dashes all lines of a combo chart or none.
- Amounts in billions use a number format that yields "€17.62 bn".
- The Navigation Bar is placed on every Sheet and uses the nebula navigation, selection and theme hooks verified in discovery.
- Where a native object cannot be themed to match (known open points: straight table text colour on dark, text object), the fix is searched in per-object styling first; the fallback is the closest result inside Qlik.

## Testing Decisions

A good test here checks what a viewer or a teammate can observe: the files the generator writes, the numbers the App shows, and whether a Sheet renders. It does not check how the load script, the expressions or the extensions are written, so they can be rewritten without breaking tests.

Three test points, agreed with the project owner, and no others:

1. **The generated CSV files.** The same seed gives identical files; every fact row references existing dimension rows; each Planted Story is measurably present.
2. **The reloaded App on the tenant.** Every master measure is evaluated through `qlik-cli` for several selections and compared, within a small tolerance, with the Reference calculator's result from the same CSV files. This is the main test and covers the load script, the data model and the set analysis together.
3. **The rendered Sheets.** Each Sheet is opened in a signed-in browser and captured; the check fails if any object is empty or shows an error. Qlik's reporting API cannot be used because it rejects Custom Extensions and exports PDF only.

The Custom Extensions get no separate test suite: their numbers are covered by test point 2 and their rendering by test point 3. The project owner's walk-through of the five Sheets is the final acceptance of the look.

There is no prior art in this repository. Working examples of expression evaluation and of each object type are in `docs/research/spike/` and `docs/research/object-examples/`.

## Out of Scope

- A separate web page or mashup embedding Qlik (ADR 0001).
- Statistical forecasting, AI-generated narrative or natural-language Q&A inside the App.
- Real company data, and any real company or carmaker name.
- Row-level security (section access), mobile layouts, subscriptions, alerts and reports.
- A reusable template or generator for other apps; this is one worked example.
- Continuous integration; the build and checks run from a developer's machine.
- Moving the App to a managed space or publishing it to a wider audience.

## Further Notes

- The tenant is a trial with about 30 days remaining at the time of writing. The App can be rebuilt on any tenant with the build command.
- The trial tenant adds a "Qlik Unlocked" banner and a Support chat button that cannot be removed.
- `qlik-cli` on this machine is the Intel binary running under Rosetta; discovery found no difference in behaviour.
- A failing load script makes the build exit non-zero but still leaves the new script in the app.
- The scratch app `claude-scratch-demo`, theme `claude-dark` and extension `claude-nav` left by discovery are replaced or removed by the final ticket.


# Recorded during the build

Deviation recorded during #3: the spec's data model lists three fact tables (sales, Budget, Order Intake). They are loaded as one concatenated Facts table, because separate fact tables sharing several dimensions create synthetic keys and circular references in Qlik. Budget rows sit at month grain (dated the 1st of the month) and carry only Product Line, Country and Channel; Order Intake rows carry no Production Site. The requirement itself (no synthetic keys, no circular references) is unchanged and is checked by the verify command.

## Deviation from the spec: tests beyond the three agreed test points

The spec agreed three test points (the generated CSV files, the reloaded App against the Reference calculator, the rendered Sheets) and no separate test suite for the Custom Extensions.

The branch carries more, each written to catch a bug that happened during the build: regression tests for the data upload, the Sheet capture's sign-in wait and the Budget rule, layout tests per Sheet, and a small suite for the Sales Bridge's drawing logic. They run in under a minute without the tenant.

Decision (developer, 2026-11-22): keep them.


## Deviations from the spec in the built App

Found by comparing this spec and the approved mock-up (variant A) with the App on `build/valtera-app`. The deviation on tests is recorded in an earlier comment and is not repeated here.

1. **Four Regions.** The data has Europe, Asia, North America and South America (17 Countries). The mock-up shows six (Europe, North America, China, Asia excl. China, South America, Africa & Middle East). China is a Country in Asia, and there is no Africa & Middle East.
2. **Budget is null by Customer and Production Site.** Budget is planned by Product Line, Country and Channel only. When a selection narrows Customer or Production Site, every Budget measure (Budget, Budget Attainment, every `vs Budget`) is null instead of a figure, so story 17's comparison with Budget is not available there. The Hero KPI Strip says "No Budget by Customer or Production Site", and the charts' subtitles say the same. Rule: `docs/measures.md`, Budget.
3. **EUR m on Product Line and Margin.** Story 38 asks for amounts such as `€17.62 bn`. A Product Line's amounts would read `€0.01 bn`, so this Sheet shows amounts in EUR m (`€184.3 m`), its Sales Bridge included. All other Sheets use EUR bn.
4. **Product Line and Margin layout.** The Sheet adds an object the spec does not name: Gross Margin change by Business Group and Region (a pivot, where the Lighting in Asia story shows as one red cell). The drill-in by Business Group is a Business Group filter beside the Sales Bridge: picking one narrows the Sheet, the bridge included, rather than drilling inside the bridge. The objects were re-arranged so nothing scrolls sideways: the margin change pivot sits under the Product Line and Channel pivot, and the filter and bridge sit above the trend on the right.
5. **Light scrollbars and selection toolbar.** Story 29 asks for one dark design. Tables that scroll show the browser's light scrollbars, and Qlik's toolbar while selecting in a chart is white. Neither can be themed without CSS that targets Qlik's page (ADR 0001); tables are sized to avoid scrolling where they can.
6. **Retuned growth and Kestova Motors.** The company grows about 5% a year (Sales YTD 2026 +5.3% against Prior Year). The "dominant share of Propulsion Sales" is Kestova Motors growing from about 15% of Propulsion Sales in 2024 to about 30% in 2026 (30.6% of Propulsion's Sales YTD): the largest Propulsion Customer by far, not a majority. It takes that share from the other Customers, whose Propulsion Sales shrink about 3% a year.
7. **Figures and period differ from the mock-up.** Sales YTD is €6.16 bn, against the mock-up's €17.62 bn. The data runs through 31 December 2026, so with no selection YTD is all of 2026 instead of the mock-up's "YTD Oct 2026"; selecting Month = Oct gives the mock-up's period.
8. **The comparison is checked outside qlik-cli.** Test point 2 evaluates measures through `qlik-cli`, but `qlik-cli` cannot select inside an alternate state. The side-by-side comparison's measures are therefore evaluated from the signed-in capture browser, in an engine session of their own (`valtera/state_check.js`), and compared with the Reference calculator as usual. That check runs only with the Sheet capture.


