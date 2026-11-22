# PROTOTYPE: Executive Overview Sheet (throwaway)

Question: what should the Executive Overview Sheet look like, so the developer can approve the visual direction before any Qlik work?

Open `index.html` by double-clicking it. It makes no network requests.

- `?variant=A|B|C` switches the layout. You can also use the floating bar or the left and right arrow keys.
- Press `T` or click "Object types" to outline every object as a Custom Extension or a native object.
- `?bar=0` hides the bar. `screenshot.png` shows variant A at 1440x900.

All numbers are invented Synthetic Data in EUR (Year 2026, actuals through October). The company and Business Group names are placeholders. Change them in the two constants at the top of the `<script>` (`COMPANY`, `BUSINESS_GROUPS`).

## Variants (same objects, different structure, 24 x 12 grid)

| | A "Trend-led" | B "Filter rail" | C "KPI column" |
|---|---|---|---|
| Filters | horizontal strip under the nav | vertical rail on the left, expanded listboxes | horizontal strip |
| Hero KPI strip | full-width row | row to the right of the rail | vertical column on the left |
| Main focus | monthly trend (16 cols), bridge beside it | bridge and trend at equal weight | bridge across the full width |
| Top Customers | 6 rows | 6 rows | 10 rows |

## Object by object

| Object | Build as | Notes |
|---|---|---|
| Navigation bar (brand, five Sheets, current selections, Synthetic Data label) | **Custom Extension** | Placeholder brand mark. Selection chip and "Clear all" read and write app selections. |
| Hero KPI strip (Sales, Gross Margin, Order Intake, Budget attainment; sparkline and variance colouring) | **Custom Extension** | Has a faint green radial glow and gradient sparklines, which only an extension can draw. Variance always uses a glyph (▲/▼) as well as colour. |
| Price/volume/mix bridge | **Custom Extension** | Rounded bars, totals with break marks, axis truncated at €16.80 bn (labelled). Header copies the theme's object-title style so it reads as native. |
| Filter pane (Year, Business Group, Region, Channel) | native object + theme JSON | Filter pane object, collapsed (A, C) or expanded (B). |
| Sales vs Budget vs prior year by month | native object + theme JSON | Combo chart on one axis: Sales as bars, Budget and prior year as lines. Series colours are set per measure in object properties, not CSS. |
| Sales by Business Group | native object + theme JSON | Horizontal bar chart, one measure, value labels. |
| Sales by Region | native object + theme JSON | Horizontal bar chart, one measure, value labels. Map not used. |
| Top Customers | native object + theme JSON | Straight table. vs prior year text colour comes from a measure colour expression, and the ▲/▼ glyph is part of the measure's string. |

Theme tokens are listed at the top of the `<style>` block, each mapped to its intended theme JSON property: `sheet.backgroundColor`, `object.backgroundColor`, `object.borderColor/borderWidth/borderRadius`, `object.padding`, `object.shadow.boxShadow`, title colour and size, and data colours. Native objects use only those properties. They have no uppercase titles, letter-spacing, gradients or rounded bars.

Chart palette (validated on the dark surface with the dataviz validator, all pairs): Sales `#1aa865`, Budget `#3987e5` (dashed), prior year `#d95926`. Result: lightness, chroma, contrast and normal-vision checks pass. Deutan separation of Sales and prior year is 7.0, in the warn band, so the chart relies on its secondary encoding: bars vs lines, a dashed line, and the legend.

## At risk under the theme constraints

1. **Card styling may not apply at all.** The research says `object.padding`, `object.border*`, `object.borderRadius` and `object.shadow` only take effect under the `CLIENT_TLV_1804_LESS_CARDS` feature flag, and it is not stated that this flag is the default. If they don't apply, the native cards revert to Qlik's default look and the design stops being uniform. Test this first with the `?features=` URL flag.
2. **Sheet navigation from a nebula.js extension is unconfirmed.** Button objects are the only confirmed way to navigate between Sheets once the toolbar and sheet header are hidden. If the nav extension can't navigate, the tabs must become native buttons, which loses the underline tab design.
3. **Qlik chrome cannot be fully removed.** The toolbar and sheet header can be hidden. The outer app navigation bar can only have its items removed, so a thin Qlik bar may still sit above our nav. The sheet will not reach the browser edge as it does in the mockup.
4. **The green accent collides with Qlik's selection green.** Accent, favourable variance and Qlik's built-in "selected" green are all green. It is unconfirmed whether listbox selection-state colours (selected, alternative, excluded) can be themed. Filter dropdown popovers and the selection toolbar may also stay light on a dark sheet.
5. **The collapsed filter pane's green underline is my invention.** Native collapsed listboxes show the selected values, but probably not that bar. Qlik also decides, based on space, whether listboxes are collapsed or expanded, so the B rail could end up partly collapsed.
6. **Typography is uncertain.** A custom font needs `@font-face` in the theme's CSS file and font files in the zip. That is not a DOM selector, but theme CSS is in flux. The mockup uses the system font. Title weight 600 and the subtitle style also depend on what the unread theme JSON schema allows.
7. **Combo chart details may not be available.** It is unconfirmed whether a dashed line style for the Budget measure is available natively. The legend position and colours are fine.
8. **Bar and table density.** Qlik sets bar thickness, the category-label column width and the table row height. Rows may be taller, so fewer Customers fit (6 in A and B, 10 in C). Row dividers and header styling depend on the table's theme properties.
9. **Number format.** Qlik abbreviates billions as "G" by default. To get "€17.62 bn", set `NumericalAbbreviation` in the script or use explicit format strings.
10. **The grid itself is assumed.** The mockup assumes a 24 x 12 grid at 8px gaps filling 900px. The real row count, gutter and sheet size are set by Qlik's sheet settings and could shift every object.
11. **The extensions are deliberately richer than the native objects.** They read theme colours through `useTheme()`. Only the extension headers copy the native title style, so a change of title style in the theme won't reach them unless they read it from `useTheme()` too.

## Glossary mismatches for the developer to settle

- Region, Gross Margin, Budget attainment and "prior year" are used as labels but are not defined in GLOSSARY.md.

## Not done

The prototype skill's capture step (commit the prototype to a throwaway branch) was skipped. The directory is not a git repository and the brief said not to run git.
