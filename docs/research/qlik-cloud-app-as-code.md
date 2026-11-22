# Building a Qlik Cloud app entirely from code

Researched 2026-11-21 from qlik.dev, help.qlik.com, community.qlik.com (Qlik staff posts only where marked) and GitHub. No tenant was called and nothing was installed. Claims are tagged **[Confirmed]** (read in a primary source) or **[Unconfirmed]**.

Source shorthand: `qlik.dev/X.md` means the markdown rendering of the qlik.dev page.

---

## 1. qlik-cli: build, unbuild, create app in a space, script, reload, status

**`qlik app build`** [Confirmed, https://qlik.dev/toolkits/qlik-cli/app/app-build.md]
- Description: "reloads and saves a Qlik app after updating its connections, dimensions, measures, objects, and script."
- Flags: `-a/--app` (name or ID), `--app-properties` (JSON file), `--bookmarks`, `--dimensions`, `--measures`, `--objects`, `--variables` (JSON glob paths), `--connections` (YAML), `--script` (.qvs), `--limit`, `--no-data`, `--no-reload`, `--no-save`, `--silent`, `-t/--traffic`, `--ttl`.
- Example: `qlik app build --connections ./myconnections.yml --script ./myscript.qvs`.
- It does not create the app. The app must already exist (`-a`). [Inference from flags; no create flag exists]

**`qlik app unbuild`** [Confirmed, https://qlik.dev/toolkits/qlik-cli/app/app-unbuild.md]
- Splits an app into separate JSON/YAML files: generic objects, dimensions, measures, variables, the reload script, connections, plus a `config.yml` that ties them together. Default output dir `./<app name>-unbuild` (`--dir` to change).
- Connection passwords cannot be exported; add them manually.
- Object trees (e.g. sheets) are exported as full property trees; children appear in the parent's JSON in a `qChildren` array.
- Use unbuild on a hand-made reference app to get the exact JSON for every object type, then template it. This is the practical answer to "authoritative property definitions" (see section 3).

**Exact on-disk file names/layout** produced by unbuild (e.g. `script.qvs`, `dimensions.json`, `app-properties.json`, `connections.yml`, per-object file naming) [Unconfirmed]: the doc pages list only the flags and `config.yml`. Run `qlik app unbuild` once against a scratch app to see the layout. `config.yml` presumably holds the flag values for `build`.

**Limits** [Confirmed from flags]: build handles script, connections, dimensions, measures, variables, bookmarks, objects, app properties. It has no flags for themes, extensions, data files, spaces, or publishing. Connection secrets are not round-tripped. Whether `--objects` replaces or merges with existing objects, and whether stale objects are deleted [Unconfirmed].

**Create an app in a space** [Confirmed, https://qlik.dev/toolkits/qlik-cli/app/app-create.md]: `qlik app create --attributes-name "X" --attributes-spaceId <spaceId>` (also `--attributes-usage ANALYTICS`, `--attributes-locale`; `-q` returns only the ID).

**Create a space** [Confirmed, https://qlik.dev/toolkits/qlik-cli/space/space-create.md]: `qlik space create --name "X" --type shared|managed|data`. Names must be unique.

**Set the load script** [Confirmed, https://qlik.dev/toolkits/qlik-cli/app/app-script-set.md]: `qlik app script set ./script.qvs -a <app>`. (Alternatively `--script` on `app build`.)

**Reload and read status/errors**
- CLI: `qlik reload create --appId <id>` (flags `--partial`, `--variables`, `--weight`, `--resourceType`) [Confirmed, https://qlik.dev/toolkits/qlik-cli/reload/reload-create.md]. `reload get` / `reload log` exist in the nav but their pages were not read [Unconfirmed flags].
- REST [Confirmed, https://qlik.dev/apis/rest/reloads.md]: `POST /api/v1/reloads` `{appId}` returns 201 with a record; `GET /api/v1/reloads/{id}`. Status values: `QUEUED`, `RELOADING`, `CANCELING`, `SUCCEEDED`, `FAILED`, `CANCELED`, `EXCEEDED_LIMIT`. On `FAILED`, `errorCode` and `errorMessage` are set (message truncated with "..."). `GET /reloads/{id}` includes a `log` field for the latest execution; list needs `log=true`. 429 means a reload is already pending for that app. Endpoint for the full script progress log download is not documented on that page [Unconfirmed].
- `qlik app build` itself also reloads over the engine websocket and prints reload output (`--silent` suppresses it) [Confirmed from flag description]. Its exit code on script failure [Unconfirmed].

---

## 2. Uploading CSVs to a shared space and reading them in script

**Upload** [Confirmed]
- REST: `POST /api/v1/data-files`, multipart with parts `File` (binary) and `Json` (`name`, `folderId`, `connectionId`, `appId`, `folder`, ...). Re-upload: `PUT /api/v1/data-files/{id}`. Source: https://qlik.dev/apis/rest/data-files/
- Target space is chosen by `connectionId` (a DataFiles connection that maps to a space); omitted means Personal Space. List connections with `GET /api/v1/data-files/connections` (items have `id`, `name`, `type`, `spaceId`, `connectStatement`).
- CLI: `qlik data-file create --file ./x.csv --name x.csv --connectionId <id>`; `--resumable` for large files; `--folderId`; `--appId` binds file lifecycle to an app. Source: https://qlik.dev/toolkits/qlik-cli/data-file/data-file-create.md
- A `/` in `name` is treated as a folder separator. Name must have a valid extension.

**Size limit**: not stated numerically on the REST page. A 413 is returned when the "user's quota for maximum file size" is exceeded, and `GET /api/v1/data-files/quotas` exists but its response was not read [Unconfirmed: the actual per-file number].

**Path in the load script** [Confirmed, https://help.qlik.com/en-US/cloud-services/Subsystems/Hub/Content/Sense_Hub/LoadData/connect-data-sources-data-load-editor.htm via search result]: `lib://<SpaceName>:DataFiles/<folder>/<file>`, e.g. `LOAD * FROM [lib://SalesSpace:DataFiles/Orders By Region/orders_Europe.csv] (txt, utf8, embedded labels, delimiter is ',');`. A blank space name means "current space" (the app's own space). The file and folders must exist before the reload.
- The `connectStatement` on the connections endpoint is the likely authoritative source for the exact string [Inference; not verified]. The `qlik app build --connections` YAML is for non-DataFiles connections; DataFiles spaces need no connection definition [Inference].
- The app and the CSVs must be in the same space, or the reloading identity needs access to the data space [Unconfirmed in a primary source].

---

## 3. Sheets and objects as JSON

**What is confirmed**
- `qlik app object set <glob>` creates or updates objects from JSON files in either `GenericObjectProperties` or `GenericObjectEntry` format [Confirmed, https://qlik.dev/toolkits/qlik-cli/app/app-object-set.md]. `app build --objects` takes the same JSON paths.
- Sheet property structure is "an artifact of how the client is implemented and is not part of the public API" (Qlik employee Oystein Kolsrud) and can be reverse engineered; the sheet's **`cells`** property tells the client where each object sits [Confirmed, https://community.qlik.com/t5/Integration-Extension-APIs/Adding-objects-to-sheet-with-JSON-API/m-p/2514608]. Cell shape shown there:
  ```json
  {"name":"<childObjectId>","type":"table","col":0,"row":0,"colspan":12,"rowspan":11,
   "bounds":{"x":0,"y":0,"width":50,"height":91.67}}
  ```
  (the grid is 24 columns wide in that example; `bounds` are percentages [Inference from values]). `col/row/colspan/rowspan` are also documented in `SheetCellPosition` (https://help.qlik.com/en-US/sense-developer/May2026/Subsystems/NetSDKAPIref/Content/Qlik.Sense.Client.SheetCellPosition.htm).
- Sheets are exported by unbuild as a full tree with children in `qChildren` [Confirmed, unbuild page].
- Per-chart property references exist for barchart, linechart, kpi and others in the Visualization API docs, but they cover only a subset and defer to `HyperCubeDef` for the rest [Confirmed, https://help.qlik.com/en-US/sense-developer/November2025/Subsystems/APIs/Content/Sense_ClientAPIs/QlikVisual/qlik-visual-barchart-properties.htm]. Engine `HyperCubeDef`, `ListObjectDef`, `GenericObjectProperties` are the base schema.

**Not confirmed (do not hard-code from memory)**
- Exact `qInfo.qType` strings and full property trees for `kpi`, `barchart`, `linechart`, `combochart`, `table`, `pivot-table`, `filterpane`, `action-button`, `text-image`, and the layout container. The qlik-oss repos `sn-action-button`, `sn-filter-pane`, `sn-table`, `sn-container` exist (https://api.github.com/search/repositories?q=org:qlik-oss+sn-) and typically carry an `api-specifications/properties.json` (seen for sn-table via a CodeClimate mirror), but I did not read these files.
- **Layout container**: the type name could not be confirmed. Help says it is part of the Dashboard bundle, edit-mode only, cannot nest layout/tab/trellis containers inside it, and shows/hides children by condition (https://help.qlik.com/en-us/cloud-services/Subsystems/Hub/Content/Sense_Hub/Visualizations/DashboardBundle/layout-container.htm). `qlik-oss/sn-container` is described as "container supernova for nebula.js" and is *not* confirmed to be the layout container (the legacy tabbed container is a different object). A Qlik employee said it launched in Cloud first, then Windows Feb 2024 (community post, https://community.qlik.com/t5/Design/Introducing-the-New-Layout-Container-Tips-Tricks-Nuances/bc-p/2144525). Whether it is formally "GA" is not stated in any page I read.
- Dashboard bundle objects may require the bundle to be present in the tenant [Unconfirmed].

**Recommended method (to make this verifiable)**: build one reference sheet containing one of each object type in the UI (once, by hand, or in a throwaway app), run `qlik app unbuild`, and treat the exported JSON as the golden templates. Alternative: `qlik app object properties` / Engine `GetProperties` against that app. A user-facing tool named by Qlik staff for this is "Qlik Explorer for Developers" (community post above).

---

## 4. Custom themes

- **Packaging** [Confirmed, https://help.qlik.com/en-US/cloud-services/Subsystems/Hub/Content/Sense_Hub/Admin/mc-themes.htm]: zip containing a `.qext` metadata file and the main theme JSON, plus optional CSS, fonts, images (PNG/JPEG/GIF/SVG), HTML. Limits: zip 30 MB, single file 30 MB, 500 files, 100 MB uncompressed. Disallowed MIME types (executables, zips, shell/PHP scripts) fail the upload. The qext filename must be unique. External resources need a CSP origin. Deleting a theme affects every app that uses it.
- **Theme JSON structure** (properties per chart type, palettes, fonts, `_inherit`, `object.*`, `sheet.*`): https://qlik.dev/extend/create-custom-themes.md only lists capabilities and links elsewhere. The schema was not read [Unconfirmed]. The built-in themes can be downloaded as zips from the tenant and used as templates (stated on that page).
- **Custom CSS**: supported as an optional asset, but "DOM selectors in custom CSS are not a supported pattern" because the DOM can change at any time [Confirmed, create-custom-themes page]. Custom theme fonts are not supported for cross-domain embedding unless `<qlik-embed iframe="true">`.
- **CSS change in force** [Confirmed, Qlik support update https://community.qlik.com/t5/Support-Updates/Upcoming-changes-to-how-CSS-for-custom-Qlik-Analytics-themes-is/bc-p/2550105]: Qlik Cloud applies the change on or after 2026-08-18 (so it is live now). Base card CSS overrides are removed, new default theme is Foundation (plus New Horizon), top-level selectors such as `qv-client` and `qv-card` must not be used. Use theme JSON instead: `sheet.backgroundColor`, `sheet.margin`, `object.padding`, `object.borderWidth`, `object.borderColor`, `object.borderRadius`, `object.shadow.boxShadow`, `object.shadow.boxShadowColor`. The article says these only take effect under the `CLIENT_TLV_1804_LESS_CARDS` flag; whether that flag is now default is not stated, and the article has a likely typo in the `borderRadius` example. Test with `?features=CLIENT_TLV_1804_LESS_CARDS,TLV_1804_NEW_DEFAULT_THEME`.
  - Consequence: design the "custom look" in theme JSON properties, not CSS.
- **Upload by API/CLI** [Confirmed]: `POST /api/v1/themes` multipart (`file` = zip; optional `data` JSON with name/type/version/tags). 409 on duplicate name, 415, 422. `PATCH /api/v1/themes/{id}` to update (file or data), `DELETE` soft-deletes. Rate limit 100/min. (https://qlik.dev/apis/rest/themes/, https://qlik.dev/manage/platform-operations/add-custom-themes-and-extensions.md). Example: `curl -X POST https://<tenant>/api/v1/themes -H "Authorization: Bearer <key>" -F 'file=@theme.zip'`. A `qlik theme create` CLI command is probable but I did not read its page [Unconfirmed].
- **Role** [Confirmed, mc-themes help]: Tenant admin, Analytics admin, or a custom role with "Manage themes" = Allowed. (The REST pages themselves state no roles; they only show 403.)
- **Set an app's theme programmatically** [Unconfirmed]. UI path is app Settings > Appearance > Application theme; custom themes appear under "Custom" (https://help.qlik.com/en-US/cloud-services/Subsystems/Hub/Content/Sense_Hub/Apps/style-app.htm). That page does not say where the choice is stored. For Qlik Sense on-premises, a community thread says it is the `theme` property on the app's `appprops` object, but that is not a Qlik Cloud primary source and the outcome was not confirmed. Likely route: `qlik app build --app-properties <json>` with a `theme` key, or edit the `appprops` generic object. Verify by unbuilding an app after picking a theme in the UI and diffing `app-properties`.

---

## 5. Custom extensions (nebula.js)

- **Workflow** [Confirmed, https://qlik.dev/extend/extensions/nebula-js/quickstart/first-extension.md]: `npx @nebula.js/cli create <name> --picasso none --pkgm npm` (needs Node.js 24+), `npm run start` (dev server on localhost:8000, connect with a web integration ID and the tenant wss URL), `npm run build` (bundle in `/dist`), `npm run sense` (creates `/<name>-ext` folder with `.qext` and bundled JS), then zip that folder and upload. The page does not document a `nebula serve` command (the extension guidelines page mentions it, https://qlik.dev/extend/extensions/extension-guidelines.md). `npm run sense` maps to `nebula sense` [Inference: script names come from the scaffold, not read].
- **Upload by API** [Confirmed, https://qlik.dev/apis/rest/extensions/]: `POST /api/v1/extensions` multipart (`file` = zip, optional `data` JSON); PATCH/DELETE/GET endpoints; 409 on duplicate qext filename. The Qlik Help page describes only the UI and does not mention the API [so the API is confirmed only from qlik.dev]. CLI: a `qlik extension create` command likely exists [Unconfirmed].
- **Role** [Confirmed]: Tenant admin, Analytics admin, or custom role with "Manage extensions" (`admin.extensions`) = Allowed (https://help.qlik.com/en-US/cloud-services/Subsystems/Hub/Content/Sense_Hub/Admin/mc-extensions.htm).
- **Zip constraints** [Confirmed, mc-extensions help]: needs a `.qext`, a `.js`; limits 30 MB zip, 30 MB per file, 500 files, 100 MB uncompressed; no nested zips; executables/zips/scripts rejected; help recommends hosting images externally. Extensions are not virus-scanned by Qlik. Help text mentions `.html` and `.css` as base files; nebula output has neither, and the quickstart shows it uploads fine [apparent inconsistency, flagged].
- **Guidelines** [Confirmed, extension-guidelines page]: qext filename, JS entry and folder name must match or import fails silently; minify; no source maps; don't touch host DOM; no global CSS; use `useTheme()` for theme values; request under 10,000 cells per page; use `useModel()` not `enigma.create()`.
- **CSP** [Confirmed]: Qlik Cloud enforces CSP; external origins (fonts, CDNs, APIs) must be allowlisted or are blocked silently. Manage with `POST /api/v1/csp-origins` (one origin per entry; directive booleans `scriptSrc`, `styleSrc`, `imgSrc`, `fontSrc`, `connectSrc`, `connectSrcWSS`, ...). https://qlik.dev/apis/rest/csp-origins.md. The required role for CSP endpoints was not stated [Unconfirmed]. A self-contained bundle needs no CSP entry.
- **Use in an app built by `qlik app build`** [Partly confirmed]: extensions are tenant-level resources independent of apps (assets appear in the app's Custom objects panel). An object JSON just references the extension's `qInfo.qType` = the extension's name/`qextFilename` id. That a built object of that type renders correctly is [Inference, unverified]. Upload the extension before the build.

---

## 6. Hiding or replacing the default navigation/toolbar (no mashup)

[Confirmed, https://help.qlik.com/en-US/cloud-services/Subsystems/Hub/Content/Sense_Hub/Apps/style-app.htm]
- App Settings > UI settings can turn off: the **Toolbar** (or only Assets / Sheets / Bookmarks), the **Sheet header** (or only the sheet title), and the **application navigation bar** items (Logo, Navigation, Ask Insight Advisor, Resource center, Notifications, Profile).
- Hiding the sheet header moves the sheet-navigation arrows to the toolbar. If both header and toolbar are hidden, sheets are reachable only by keyboard shortcuts or **button objects** (the button-navigation design in this project is supported).
- Applies to all sheets and all users; anyone with edit rights can toggle it back. It does not remove the features themselves.
- Not possible without a mashup or unsupported CSS: removing the outer Hub chrome, custom page frame, fully custom nav. A community answer says there is no native way to hide the sheet description tooltip in the Navigation Menu object (CSS workaround only), and DOM-selector CSS is explicitly unsupported (see section 4).
- How these UI settings are stored, and which keys to put in `--app-properties` [Unconfirmed]. Same approach: set them in the UI on a scratch app and unbuild.

---

## 7. Headless verification

- **Evaluate expressions** [Confirmed, https://qlik.dev/toolkits/qlik-cli/app/app-eval.md]: `qlik app eval "Count(Id)" by "Region" -a <app> --rows 20 --json`, with `where "Field" is "Value"`. Good for validating loaded data and measure expressions. It evaluates expressions, it does not confirm that a sheet or object renders. Engine API (enigma.js / `@qlik/api`) is the lower-level alternative; `GetLayout` on an object returns `qHyperCube` data and errors such as `qError`, which is a good render-free object validity check [Inference, not read in a primary source this session].
- **Image/PDF export** [Confirmed, https://qlik.dev/embed/reports/reporting-api-samples.md]: `POST /api/v1/reports` (10/min) returns 202 plus a `Location` header; poll status (`queued`, `visiting`, `processing`, `done`, `failed`); when `done`, `results[].location` is the file. Sheet export uses `"type":"sense-sheet-1.0"` with `senseSheetTemplate.appId`, `sheet.id`, optional `sheet.widthPx/heightPx`, and `output.type: "pdf"`. **PNG is shown only for a single visualization** (`sense-image-1.0`); the page has no sheet-to-PNG example, so for a full sheet the practical path is PDF (then convert locally) [Unconfirmed that sense-sheet-1.0 can output png]. Default sheet size 1920x1280; files expire after 1 hour; export deadline default 10 min. Required permissions/entitlement for the reporting API were not stated [Unconfirmed]. Custom extensions rendering correctly in server-side reports [Unconfirmed].
- Fallback: a headless browser with `qlik-embed` and an API key is not covered by Qlik docs I read [Unconfirmed].

---

## 8. API key prerequisites and roles

- **Conflict in sources**
  - Newer: Qlik's admin playbook says the **Manage API keys** permission is now the sole control, and the legacy Developer role and "Enable API keys" toggle were removed on 2026-01-26 (reported via search snippet of https://help.qlik.com/en-US/cloud-admin-playbook/Content/identity_and_access/review_api_keys.htm; the page itself was not opened). The Qlik Cloud help page agrees: need a custom role with "Manage API keys" Allowed, or have it allowed in default permissions (https://help.qlik.com/en-US/cloud-services/Subsystems/Hub/Content/Sense_Hub/Admin/mc-generate-api-keys.htm).
  - Older: qlik.dev REST page still says the owner needs the **Developer** role (https://qlik.dev/apis/rest/api-keys.md).
  - Treat Manage API keys as current; confirm in the tenant.
- Tenant settings (Administration > Settings > Security > API keys): maximum token expiry (applies to new keys; no upper limit stated) and max active keys per user (up to 1000). REST: `GET/PATCH /api/v1/api-keys/configs/{tenantId}`. If no expiry is requested, the tenant maximum applies. Revoking another user's key requires TenantAdmin.
- To create spaces, upload themes, upload extensions, and manage CSP origins with the key, the key's *user* needs the corresponding permissions. Themes: Tenant admin / Analytics admin / "Manage themes". Extensions: same with "Manage extensions". Space creation roles (who may create shared spaces), and the CSP permission, were not confirmed [Unconfirmed]. Simplest safe setup: the key is owned by a Tenant admin. Add the user to the target space with a role that can edit the app and manage data files (exact space role names not confirmed).
- API keys act as the owning user; key requests use `Authorization: Bearer <key>`.

---

## Unconfirmed list (also summarised in the hand-back)

1. Exact `unbuild`/`build` file names and whether `--objects` replaces vs merges; build exit code on reload failure.
2. Exact `qInfo.qType` and property trees for kpi, barchart, linechart, combochart, table, pivot-table, filterpane, action-button, text-image; the layout container type name and GA status.
3. Numeric data file size limit (and `data-files/quotas` fields).
4. Theme JSON schema (this session read only the overview); whether the `CLIENT_TLV_1804_LESS_CARDS` flag is now default; how to set an app's theme in app properties on SaaS; a `qlik theme` / `qlik extension` CLI command.
5. Where UI settings (hide toolbar, header, nav bar) are stored in app properties.
6. Sheet-to-PNG via the reporting API; reporting permission requirements; extension rendering in reports.
7. Roles for creating shared spaces and for CSP origin endpoints; whether the Developer role is still needed (docs conflict).
8. Whether a built object of an uploaded extension type works through `qlik app build` (inferred only).
