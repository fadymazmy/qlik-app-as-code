# Tenant discovery: Qlik Cloud facts checked on the real tenant

Run 2026-11-21 against the `valtera` context (Qlik Cloud EU tenant, trial edition, client `sense-client 8.811.0`, engine `12.3015.0`), with `qlik` CLI 4.0.0 (x86_64 binary under Rosetta) and Chrome. Everything was done inside the shared space `claude-dashboard-dev` (`6b01621fdd541bea7660d3c6`). This is the work list from `qlik-cloud-app-as-code.md`, each item marked **Verified**, **Not possible** or **Still unknown**.

Scratch inputs and outputs are under `docs/research/spike/`. Working object JSON is under `docs/research/object-examples/`. The app that shows the result is `claude-scratch-demo` (`596f83e5-419c-4610-84fd-12cd38a274c1`). It is built only by `spike/demo/gen.py` and `qlik app build`.

Three findings change how we work, and they come first:

- **A. Mixing browser editing and CLI builds on the same app loses edits.** After a `qlik app build` saved the app while a browser editing session had it open, later browser edits stayed visible in that browser but never reached storage. `qlik app object ls` and `unbuild` never saw them, and the app's `modifiedDate` stopped changing. In a fresh app with no CLI writes during UI editing, edits persisted within about 1–3 minutes of leaving edit mode or the app. Rule: never edit in the UI while code builds the app. Close the browser session and wait for the save before building.
- **B. A partial property tree can crash a native chart.** A bar chart with only `qHyperCubeDef` and a few keys failed with `Cannot read properties of undefined (reading 'auto')`. A combo chart failed with `(reading 'show')`. The client does not fill in missing sub-objects for these types. A KPI with only `qHyperCubeDef` did render. Rule: build each object as "the default tree the client writes, plus our overrides". `spike/demo/gen.py` (`with_defaults`) does this from `spike/refobjects/*.json`.
- **C. Sheet files must use the `GenericObjectEntry` form**: `{"qProperty": {...}, "qChildren": [{"qProperty": {...}, "qChildren": []}]}`. A plain properties file with a `qChildren` key is accepted silently. The engine stores `qChildren` as an ordinary property, creates no child, and the sheet renders empty.

---

## 1. `qlik app build` / `unbuild`: **Verified**

**On-disk layout** (`qlik app unbuild -a <app> --dir <dir>`, which prints `"unbuild" command is experimental`). See `spike/unbuild-empty/` and `spike/demo/ub/`:

```
config.yml            # script/connections/dimensions/measures/objects/variables/app-properties paths
script.qvs            # whole load script, sections as ///$tab <name>
connections.yml       # "connections:" (empty for DataFiles)
dimensions.json       # array of GenericDimensionProperties
measures.json         # array of GenericMeasureProperties
variables.json        # array of GenericVariableProperties
app-properties.json   # qTitle, description, qUsage, spaceId, published, hassectionaccess, ...
objects/<qType>--<slug(title)>-<qId>.json   e.g. objects/sheet--overview-sheet1.json, objects/appprops---<uuid>.json
```

`config.yml` contains `objects: objects/*.json`, so `qlik app build -c config.yml` round-trips the folder. A sheet without children is written in plain properties form. A sheet with children is written in `{qProperty, qChildren}` form (finding C).

**Merge or replace** (`spike/build1/`, checked by unbuilding after each step):

| Part | Behaviour on `qlik app build` |
|---|---|
| Measures, dimensions, variables | Upsert by `qInfo.qId`. Items missing from the file are **kept**. `m_budget`, missing from `measures-salesonly.json`, survived. `vOther`, missing from `variables.json`, survived. |
| Top-level objects (sheets, appprops) | Upsert by `qId`. Sheets missing from the glob are **kept** (`sheet2` survived). |
| One sheet's tree | **Replaced in full** (SetFullPropertyTree). A KPI added by hand to `sheet1` was removed when `sheet1.json` was rebuilt without it. Stray literal properties also disappeared. |
| Deleting a top-level object | Needs an explicit `qlik app object rm <id>`. A sheet's child cannot be removed that way (`could not remove generic object 'exec-text'`); rebuild the parent sheet instead. |
| Alternate states | Not handled by build or unbuild (see 4). |

**Idempotent**: two identical builds, then `diff -r u5 u6`, gives `IDENTICAL`.

**Exit code and `--no-save`**: a failing script makes `qlik app build` exit 1, printing `Script Error. Cannot open file: '...' (Connector error: File not found)` and `Error: reload was not successful`. **`--no-save` does not protect the app in Qlik Cloud**: after `qlik app build --script bad.qvs --no-save --no-reload`, `qlik app script get` returned the bad script. A failed build still leaves its new script in the app. The data from the last good reload stays (`Sum(Sales)` unchanged after a failed reload).

## 2. Data upload, `lib://` path, reload: **Verified**

- Each space gets a DataFiles connection: `qlik raw get v1/data-files/connections --query spaceId=<space>` returns `connectStatement: CUSTOM CONNECT TO "provider=qix-datafiles.exe;path=claude-dashboard-dev:datafiles;"`, id `62ff887f-…`.
- Upload: `qlik data-file create --file ./sales.csv --name sales.csv --connectionId 62ff887f-bfbe-4d74-ac4e-96bc154d7db5`. Re-upload with `qlik data-file update`. Qlik also created a `dataset` and a `dataasset` item for the file.
- Limits (`qlik data-file quotas`): `maxFileSize 524288000` (500 MB), `maxLargeFileSize 107374182400` (100 GB, resumable upload). Allowed extensions include csv, qvd, parquet, xlsx and json.
- Paths that work in the script: `lib://claude-dashboard-dev:DataFiles/sales.csv`, and `lib://:DataFiles/sales.csv` (blank space name means the app's own space; better for promotion between spaces). **`lib://DataFiles/sales.csv` fails** with `Cannot open file ... File not found`.
- Reload through the CLI: `qlik reload create --appId <app> --json` returns an `id`. Poll `qlik reload get <id> --json` for `status` (`QUEUED`, then `SUCCEEDED`/`FAILED`). On failure it carries `errorCode: "EngineConnectorError"`, `errorMessage: "failed to complete reload: Cannot open file: ..."`, and a `log` field holding the script errors. `qlik reload` has `cancel/create/get/ls` and no `log` subcommand. `qlik app build` also reloads and prints the progress (`Sales << sales 216 Lines fetched`).

## 3. Native object JSON: **Verified**, except sn-text (**Still unknown**)

The type names below were read from objects the client created (one reference sheet per batch, added by hand and then unbuilt). Every example built by code was rendered in Chrome.

| Mock-up need | `qInfo.qType` = `visualization` | Example file (verified rendering unless noted) |
|---|---|---|
| Sheet | `sheet`; `columns:24, rows:12` is the default "Wide" grid. Grid spacing values are `small` (Wide), `medium`, `large` (Narrow) and `customrows`. Custom grid saved as `columns:48, rows:24, gridResolution:"customrows", customRowBase:24`. Sheet size `RESPONSIVE`/`CUSTOM`. Cells: `{name,type,col,row,colspan,rowspan,bounds{x,y,width,height in %}}` | `sheet-24x12.json`, `sheet-custom-grid-as-saved-by-client.json` |
| KPI | `kpi` | `kpi.json` |
| Bar chart | `barchart` (`orientation:"horizontal"`, `dataPoint.showLabels:true`) | `barchart.json` |
| Line chart | `linechart` | `linechart.json` |
| Combo chart | `combochart`. Each measure takes `qDef.series:{type:"bar"|"line", axis:0}`. Per-measure colour comes from master-measure `coloring.baseColor` plus `color:{auto:false, mode:"primary", useBaseColors:"measure"}`. **Dashed lines**: `components:[{key:"line", style:{lineType:"dashed"}}]`. Also in the UI: thickness and curve (`Monotone`/linear). This is chart-level and dashes *every* line series; no per-series option exists in the styling panel. | `combochart-dashed-lines.json` |
| Straight table | `sn-table` (the "Straight table" in today's chart list). Legacy "Table" is under *Legacy*. Cell colour: measure `qAttributeExpressions:[{qExpression:"If(...,'#1aa865','#ff6b6b')", id:"cellForegroundColor"}]`. ▲/▼ via `Dual(If(..,'▲ ','▼ ')&Num(..,'0.0%'), value)`. | `straight-table-sn-table.json` |
| Pivot | `sn-pivot-table` ("Pivot", `qMode:"P"`, `qNoOfLeftDims`). Legacy "Pivot table" is `pivot-table`. | `pivot-sn-pivot-table.json`, `pivot-table-legacy-ui-default.json` (UI default only) |
| Filter pane | `filterpane` with child entries of `qType:"listbox"` (`qListObjectDef.qDef.qFieldDefs` or `qLibraryId`), `qChildListDef:{qData:{}}` | `filterpane-with-listboxes.json` |
| Button, go to sheet | `action-button`: `navigation:{action:"goToSheet", sheet:"<sheetId>"}`, `actions:[{actionType:"clearAll", ...}]`. Clicked in the UI: it cleared selections and changed sheet. | `action-button-goto-sheet.json` |
| Text & image | `text-image` (legacy, renders `markdown`). `$(=...)` inside `markdown` is **not** expanded. | `text-image-legacy.json` |
| Text (new) | `sn-text` (Dashboard bundle). **Still unknown**: a plain `text` string is stored but never rendered, and the reporting API reports a JS render error for it. The UI default is in `text-sn-text-ui-default.json`. | n/a |
| Layout container | **`sn-layout-container`** (Dashboard bundle, `extensionMeta.bundle.id: qlik-dashboard-bundle`, available on this tenant). Children are child entries with a `childRefId` property. The parent's `objects:[{childRefId,label,bounds{x,y,width,height in %},condition}]` positions them, and they can overlap. | `layout-container.json` |
| Tab container | `sn-tabbed-container` | `tab-container-ui-default.json` (UI default only) |
| Navigation menu | `sn-nav-menu` (shows published sheets only) | `navigation-menu-ui-default.json` |
| What-if input | `qlik-variable-input` (`variableName`, `render:"l"` gives a slider; `b` buttons, `s` dropdown, `f` input box; `min/max/step`). Dragging it changed `vGrowth` 0.05 → 0.12 and the KPI changed €5.60 bn → €5.97 bn. `sn-slider` is a field/variable range slider (UI default captured only). | `variable-input-slider.json`, `slider-ui-default.json` |

## 4. Alternate states and variables from files: **Verified**

- Variables: `qlik app build --variables variables.json` creates them (`[{qInfo:{qId,qType:"variable"}, qName, qDefinition, qComment}]`). `qlik app eval '$(vGrowth)*100'` returns `5`. Upsert semantics as in item 1.
- Alternate states: **build cannot create them.** Putting `qStateNames:["StateA","StateB"]` in `--app-properties` makes `qlik app state ls` list them, but `qlik app eval "Sum({StateB} Sales)"` returns `0`. They are listed but don't work. `qlik app state add StateA -a <app>` creates a working state (`Sum({StateA} Sales)` returns the total). `unbuild` does not export states. The build therefore needs a separate step: `qlik app state add <name>` for each state.

## 5. Theme: **Verified** (straight-table text colour fixed in ticket #5, see the end of this section)

Package `spike/theme/claude-dark/`: `claude-dark.qext` (`"type":"theme"`), `theme.json`, `theme.css`, two `.woff2` (Inter, OFL, renamed to the family `ClaudeTestFont` so the test can't be confused with a built-in font). Upload with `qlik theme create --file claude-dark.zip` (id `bxR5C7jElM-CkP_bRM7TQGOWUK5omKiH`; the server assigns the id, and `name`/`qextFilename` = `claude-dark`). Update with `qlik theme patch <id> --file`. A browser page loaded before the upload does not list the new theme until it is reloaded.

**Set the app theme from code**: an object `{"qInfo":{"qType":"appprops"}, "theme":"claude-dark"}` in `--objects`. The value is the qext name, not the id. Found by choosing the theme in the UI and diffing `unbuild`, then applied by code in `claude-scratch-demo` (`object-examples/appprops-theme-and-hidden-chrome.json`). The tenant's default for new apps is "Sense Horizon".

Properties seen to take effect (screenshots `spike/screenshots/ref-theme-card-styling.jpg`, `demo-exec-hidden-chrome.jpg`). No `?features=` flag was used:

| Theme JSON | Effect |
|---|---|
| `sheet.backgroundColor` | Applies (sheet #0b0f0d) |
| `object.backgroundColor` | Applies |
| `object.borderWidth` + `object.borderColor` | Applies (1px magenta test border visible inside the shadow) |
| `object.borderRadius` | Applies (14px) |
| `object.shadow.boxShadow` + `boxShadowColor` | Applies (`0 0 0 3px` blue ring) |
| `object.padding`, `_cards` | Card border, radius and shadow apply **with or without** `_cards:true`. Removing `_cards` changed padding and title spacing only. The `CLIENT_TLV_1804_LESS_CARDS` question is moot here. |
| `object.title.main` color, fontSize, fontFamily; `subTitle` | Applies (yellow 15px test titles; the styling panel shows the theme values as defaults) |
| `fontFamily` + `customStyles:[{cssRef:"theme.css"}]` with `@font-face` | **Custom font works**: `document.fonts` reports `ClaudeTestFont 400 loaded` and `600 loaded`, served from `/api/v1/themes/<id>/file/theme.css`. The first paint shows the fallback font (FOUT). |
| `object.listBox.backgroundColor`, `.title.main`, `.content` | Applies, including the popover of a collapsed listbox |
| `object.listBox.dataColors.selected / alternative / excluded / selectedExcluded / possible` | **Applies** (confirmed in the stardust listbox source and on screen) |
| Master-measure `coloring.baseColor` | Applies when the chart uses `useBaseColors:"measure"` |
| `_variables` (`@name`), custom top-level keys | Readable by an extension (see 7) |
| `object.straightTable.content/header`, `object.straightTableV2.dimension/measure` | **No visible effect** on `sn-table` cell text (it stays `rgb(64,64,64)` on the dark card). Still unknown which key sn-table reads. Per-object table styling (`components`) is the fallback; not yet tested. |
| KPI value colour | Default is blue unless the master measure has a colour. Not themed in this test. |
| `qlik-variable-input` slider track | Stays white on the dark sheet; not themable here. |

### Open points resolved by the theme (ticket #5)

Checked against `theme/`, `app/defaults/` and the fixture Sheet `tests/fixtures/theme-sample-sheet.json` (built with `build <app> --sheet <file>`), screenshots in `docs/screenshots/ticket-5/`. Theme keys were read from the object bundles Qlik serves (`@nebula.js/sn-table` 6.78.0, `sn-pivot-table` 7.78.0, `sn-filter-pane` 1.11.0, `sn-text` 1.20.0, `sn-action-button` 2.7.0, `sn-kpi` 2.7.0, the same versions the tenant writes into new objects).

| Open point | Result |
|---|---|
| Straight table text on dark | **Fixed in the theme.** `sn-table` reads full paths: `object.straightTableV2.dimension.label.name.color` (header) and `.backgroundColor` (header, white by default), `.dimension.label.value.color`, `.measure.label.value.color`, `.total/.subTotal/.null.label.value.*`, `.grid.borderColor`, `.grid.divider.borderColor`, `.grid.hover.*`, and `object.straightTableV2.backgroundColor` (also switches its dark-background mode). The keys tried in discovery were one level too short. The pivot (`sn-pivot-table`) is themed the same way under `object.pivotTableV2.*`. |
| Text object (`sn-text`) | **Fixed by content, fallback for colour.** `text` must be a serialised Lexical editor state (`{"root":{"children":[{"type":"paragraph","children":[{"type":"text","text":"…","style":"…"}]}]}}`), not a plain string. Its text colour is hard-coded `#404040` and no theme key reaches it, so every text run carries `style: "color: #e6eeea; font-size: 13px;"`. This lives in the content, so it cannot go in the default tree; each `sn-text` object must set it. |
| Remaining Qlik bar colour | **Not settable.** The client only reads show/hide keys under `presets[].navigationBar.components` (`logo`, `pendo`, `mainNavigation`, `notificationMenu`, `profile`, `appTitle`, `appSwitcher`, `tabsManagerAdvanced`); no colour key exists in the loaded code. `appTitle` and `appSwitcher` set to hidden had no visible effect and were not kept. Fallback: the bar and the trial banner stay light (ADR 0001). |
| Slider track (`qlik-variable-input`) | **Not themable; superseded.** The What-If Controls Custom Extension (GLOSSARY) draws the sliders, so no native variable input is used. |
| KPI value colour | No theme key. Per measure: `qDef.conditionalColoring.paletteSingleColor` (`{"index":-1,"color":"#e6eeea"}` as in the mock-up, or `null` for the theme's primary colour), or a master measure with a base colour. Measures are a list, so this cannot sit in the default tree. |
| Button | Colours come from object properties only; `app/defaults/action-button.json` sets a dark button (`#17211d`, text `#e6eeea`, 13 px, not bold). `clearAll` needs `"softLock": false`, otherwise the click fails with "Invalid method parameter(s)" and the button stays disabled (the example in `object-examples/action-button-goto-sheet.json` lacks it). |
| Filter pane | Popover, rows and selection states follow `object.listBox.*`. Listbox border is per object (`components:[{key:"theme",listboxBorder:{color}}]`, set in `app/defaults/filterpane.json`). **Fallback:** the 1 px line above the selection-state bar of a collapsed listbox is hard-coded `#cccccc` in `sn-filter-pane`. |
| Selection colour | `#5b4bd6` (violet) for `dataColors.selected` and `listBox.dataColors.selected`: distinct from the accent green and from the Budget blue, and white text on it has 5:1 contrast. |
| Title weight | Titles are drawn `bold` (700) and the theme cannot change the weight; the font declaration maps 600-700 to Inter SemiBold so titles render at the mock-up's 600. |
| **Remaining light pixels** | Qlik's chart selection toolbar (lasso/clear/cancel/confirm, shown only while selecting in a chart) is white, and native browser scrollbars inside tables are light where the OS always shows scrollbars. Neither is reachable without CSS that targets Qlik's page. Fallback: size tables so they do not scroll horizontally. |

## 6. Hiding Qlik chrome from code: **Verified**

The same `appprops` object holds the UI settings:

```json
"presets": [{ "id": "claude", "name": "claude",
  "navigationBar": { "components": { "logo": {"show": false}, "pendo": {"show": false},
     "mainNavigation": {"show": false}, "notificationMenu": {"show": false}, "profile": {"show": false} } },
  "toolbar": { "show": false }, "sheetHeader": { "show": false } }],
"activePreset": "claude"
```

Built from code into `claude-scratch-demo`. The toolbar (Assets/Sheets/Bookmarks/selections bar) and the sheet header (title and arrows) are gone. **Still visible** (`spike/screenshots/demo-exec-hidden-chrome.jpg`): the top Qlik bar, about 47 px tall, with the app launcher (9 dots), the label "Application", the space/app breadcrumb with the `…` menu, and the **Qlik Answers** button. On this trial tenant there is also the "Qlik Unlocked" banner and a "Support chat" button. The UI also offers navigation-bar background/foreground colours and a logo image (keys not captured). Side effect: with the toolbar hidden, edit mode has no Assets panel, which is another reason to keep all edits in code.

## 7. Extension (`claude-nav`): **Verified**

- Built by hand in exactly the shape `nebula sense` emits (read from `@nebula.js/cli-sense` 7.9.0): `claude-nav.qext` (`type:"visualization", supernova:true`), `claude-nav.js` = `define(['./dist/claude-nav'], s => s)`, `dist/claude-nav.js` = AMD module depending on `@nebula.js/stardust`, which the host supplies. Source: `spike/ext/claude-nav/`. The real CLI (`@nebula.js/cli` 7.9.0) refuses to run: `requires NodeJS >= 24.0.0` (the machine has 22.22.1).
- Upload: `qlik extension create --file claude-nav.zip`, giving id `UutFPtapnJwhqmO-j0hBHvr1Wi1g2pB5`, `qextFilename: claude-nav`, `supernova: true`.
- Placed by build: a child entry `{qInfo:{qType:"claude-nav"}, visualization:"claude-nav", qSelectionObjectDef:{}}` plus a sheet cell `type:"claude-nav"`. It renders on both sheets.
- **Navigation**: `useNavigation()` returns the Sense navigation API (`getUrlForSheet, goToSheet, nextSheet, prevSheet, goToStory, getCurrentSheetId, ...`). Clicking a tab called `goToSheet('perf')`, the sheet changed and `getCurrentSheetId()` showed `perf`. Sheet list via `app.createSessionObject({qAppObjectListDef:{qType:'sheet', qData:{title:'/qMetaDef/title', rank:'/rank'}}})`.
- **Selections**: with `qSelectionObjectDef:{}` in its properties, `layout.qSelectionObject.qSelections` showed `BusinessGroup=Lighting` after a listbox selection. `app.clearAll()` from the extension's button cleared it.
- **Theme**: `useTheme()` returned `name() = "claude-dark"`, `getStyle('object','title.main','color') = "#ffd34d"`, `getStyle('', '', 'fontFamily')`, `getStyle('object','', 'backgroundColor') = "#141b17"`, `getStyle('', '', '_variables.@accent') = "#1aa865"`, a custom key `getStyle('', '', 'claude.accent') = "#1aa865"`, and `getDataColorPalettes()[0].key = "claude-series"`.

## 8. "€17.62 bn" number format: **Verified**

- `Num(x/1e9,'€#,##0.00 bn')` gives `€5.33 bn` (`qlik app eval`, KPI, bar labels, axis ticks `€0.50 bn`).
- In charts: measure `qDef:"Sum(...)/1e9"` with `numFormatFromTemplate:false, isCustomFormatted:true, qNumFormat:{qType:"F", qFmt:"€#,##0.00 bn", qDec:".", qThou:","}`. The value is in billions, so tooltips and sorting stay numeric.
- `SET NumericalAbbreviation='3: k;6: M;9: bn;12: T';` changes Qlik's auto format to `5.33 bn` and axis ticks to `550 M`, but adds no `€`.
- A `Num(...)` string measure also shows `€5.33 bn` (but is text).
- On a **master measure** (ticket #4, KPI referencing it by `qLibraryId`): `qDef` `Num(Sum(Sales)/1e9, '€#,##0.00 bn;-€#,##0.00 bn')` with `qNumFormat {qType "F", qFmt <same>}`, `isCustomFormatted: true`, `numFormatFromTemplate: false` shows `€17.67 bn`. A `Dual(Num(x/1e9, '€… bn'), x)` keeping the value in EUR does **not** work in the KPI: with Auto (or `qType "U"`, `numFormatFromTemplate: false`) it shows `17.67 bn`, with `qType "R"` the raw `17671228876.240364`. The KPI formats `qNum` itself and ignores the expression's text.

## 9. Verification tooling: **Verified**

- `qlik app eval "Sum(Sales)" by BusinessGroup -a <app>`; two dimensions: `by Year Month` (space-separated; `by Year,Month` fails with code 7000); set analysis: `qlik app eval "Sum({<Year={2026}>} Sales)" "Sum({<Year={2025}>} Sales)" by Region`; filter: `... by "Region" where "Year" is "2026" --json`; `--rows N`.
- `where "<field>" is "<value>"` makes a real selection (`GetField` + `Select` in the websocket traffic, `-t`), not a set expression, so set modifiers in the measure (`Year=`) override it as they would in a chart. Several expressions in one call share one hypercube row, one round trip (about 3 s) for all of them.
- In `--json` output `qNum` is **left out when it is 0** (Go `omitempty`), and a null is `"qNum": "NaN"` with `"qIsNull": true`. Read a cell as `cell.get("qNum", 0)`.
- `qlik app unbuild -a <app> --dir <dir>` (about 4 s) is the quickest way to read every master measure and dimension of the App; `qlik app measure properties` takes one id per call.
- **The data/metadata endpoint does not list `$Syn` tables.** `qlik raw get v1/apps/<app>/data/metadata` returns the loaded tables and fields but never the synthetic key tables, so verify derives synthetic keys from the fields: two tables that share more than one field are joined by a synthetic key. Each field's `src_tables` lists the tables it links.
- Set searches on a date field: `Date={">=2026-01-01<=2026-12-31"}` (formatted as `DateFormat`) works. A numeric range `Date={">=46023<=46387"}` returns nothing, and an expression search `Date={"=Date>=46023 and Date<=46387"}` returns nothing for days excluded by the current selection (for example the Prior Year under a Year selection).
- Reporting API: `qlik raw post v1/reports --body-file spike/report/req-pdf.json` (`type:"sense-sheet-1.0"`, `output.type:"pdf"`) returns 202 with a `Location` status URL. Poll `qlik raw get v1/reports/<id>/status`; when `done`, `results[].location` gives `/api/v1/temp-contents/<id>`, fetched with `qlik raw get ... --output-file`. **Whole-sheet PNG is not possible**: `type:"png"` is rejected (allowed: `image pdf xlsx ... pptx ...`), and `type:"image"` gives `unsupported output type image ... for sense-sheet-1.0`. Convert the PDF locally (`sips -s format png` or `pdftoppm`).
- **Reports do not render custom extensions**: `REP-403002 "chart type not allowed"` for `claude-nav` (method `AllowVisualization`). They also dropped the sheet background and shadows, and A4 cropped the sheet (`spike/screenshots/report-api-sheet-pdf.png`). The report did render the native charts. A browser screenshot is therefore the only full-fidelity capture. Here that was Chrome with the user's session; a headless option needs its own auth (Still unknown).

## 10. Intel CLI under Rosetta: **Verified, no differences seen**

Every command used worked: build, unbuild, eval, state, data-file, reload, theme, extension and raw. `qlik version` takes 0.2 s, and an `app eval` takes about 2.8 s (mostly network). No architecture-specific failure. The one toolchain blocker is not Rosetta but Node: the nebula CLI needs Node ≥ 24.

---

## Consequences for the approved design (variant A)

| Mock-up element | Reproducible? | Closest achievable alternative |
|---|---|---|
| Sheet reaching the browser edge, no Qlik chrome | **No.** A ~47 px Qlik top bar stays (launcher, "Application", breadcrumb, Qlik Answers). Trial adds the "Qlik Unlocked" banner and Support chat. | Hide toolbar, sheet header and nav items through `appprops.presets`; the Navigation Bar extension sits directly below the Qlik bar. Possibly colour that bar dark through the navigation-bar colour option (keys not captured). |
| Navigation Bar (tabs with underline, current selections chip, Clear all, Synthetic Data label) | **Yes** | Extension via `useNavigation().goToSheet`, `qSelectionObjectDef`, `app.clearAll()`. Verified. |
| Card look (dark surface, 1px border, radius, shadow, padding, title style) | **Yes**, natively, no feature flag | Theme JSON keys listed in section 5. |
| Custom typography | **Yes** | `@font-face` in theme CSS plus `fontFamily`. Expect a brief fallback-font flash. |
| Filter strip of collapsed listboxes with green underline | **Mostly.** A collapsed listbox shows its title and a green bar showing the selected share, but at 1 grid row it shows no value text ("2026" / "All"). | Give the filter pane more height (untested), or rely on the Navigation Bar's selection chips for the values. |
| Selection green vs accent green collision | **Solvable** | `object.listBox.dataColors.*` and top-level `dataColors.selected` are themable. Pick a distinct selected colour if needed. |
| Light popovers on the dark sheet | **Not an issue.** The listbox popover takes `listBox.backgroundColor`. | n/a |
| Hero KPI Strip | Feasible as an extension (rendering, theme read and data access proven with `claude-nav`); the strip itself not built | n/a |
| Sales Bridge | Feasible as an extension; not built | n/a |
| Sales vs Budget vs Prior Year combo: bars plus two lines, colours per measure, **only Budget dashed** | **Partly.** Bars, lines and per-measure colours work. Dashing is chart-level (`components.line.style.lineType`), so Prior Year is dashed too. | Dash both lines and rely on colour plus legend; or draw Prior Year as markers only; or put it in the Sales Bridge extension. |
| Horizontal bars with `€7.48` labels | **Yes** | `barchart` horizontal with `/1e9` and format `€#,##0.00 bn` (or `€#,##0.00` for the mock-up's short form). |
| Top Customers table with coloured ▲/▼ | **Yes** for values, glyphs and colours. **Not yet** for the table's base text colour on dark (theme keys tried had no effect). | Per-object `sn-table` styling (`components`), still to test, or a light-text fix found later. |
| "€17.62 bn" values | **Yes** | Section 8. |
| 24 × 12 grid | **Yes** | Default sheet `columns:24, rows:12`; `sheet.margin` in the theme sets the gutter. |
| What-If slider | **Yes** functionally | `qlik-variable-input` with `render:"l"`. Its track stays white (not themed); an extension would be needed for a matching look. |
| Text blocks | `sn-text` **not usable from code yet** | Legacy `text-image` (markdown, no `$(=)` expansion) or text drawn inside an extension. |
| Automated visual checks of sheets with extensions | **Not via the reporting API** | Browser screenshots; reporting API PDF only for native-only sheets. |

## Artifacts left on the tenant

- Space `claude-dashboard-dev` (`6b01621fdd541bea7660d3c6`), containing data file `sales.csv` (`632bd53e-7111-4150-8a64-cba96a3f51f9`) and the `dataset`/`dataasset` items Qlik created for it.
- App `claude-scratch-demo` (`596f83e5-419c-4610-84fd-12cd38a274c1`): theme, extension, hidden chrome, all native types above.
- Theme `claude-dark` (`bxR5C7jElM-CkP_bRM7TQGOWUK5omKiH`, qext v0.0.4) and extension `claude-nav` (`UutFPtapnJwhqmO-j0hBHvr1Wi1g2pB5`).
- Deleted: `claude-scratch-build` (`432ef881-…`) and `claude-scratch-ref` (`ab8c2c92-…`).
