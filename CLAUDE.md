# Valtera Sales Dashboard

A Qlik Sense app built entirely from code. Read `GLOSSARY.md` before naming anything, and `docs/adr/` before changing how the app is built.

## Rules for working on the Qlik tenant

- Work only inside the shared space `claude-dashboard-dev`. Never read, change or delete anything in another space.
- Every theme and extension uploaded to the tenant has a name prefixed `claude-` (Qlik assigns the ids). These are tenant-wide, so the prefix is how others tell them apart.
- Never edit an app in the Qlik UI that the build also writes to. A build that saves while an editing session is open causes that session's later edits to be lost without warning.
- Delete only what this repo's build created.
- Never print, read or commit the API key or the `qlik-cli` config file. Each person keeps their own key in their local `qlik-cli` context; the tenant URL comes from that context too.
- All data is Synthetic Data. Never load real company data into this app.

## Building the App

Python 3 with the standard library; the Sheet capture also needs Playwright and Google Chrome:
`python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`.
The Custom Extensions need Node 24 (`.nvmrc`), active in the shell that runs the build:
`nvm use && npm ci --prefix extensions`.

- `.venv/bin/python -m valtera build <app-name>`: generate data, ensure the space, upload data, theme and Custom Extensions, create or find the app, add its alternate states, build and reload it, verify. Exits non-zero with Qlik's reload error when the script fails. `--sheet FILE` (repeatable) also builds a Sheet that is not part of the App, such as the theme's proof Sheet `tests/fixtures/theme-sample-sheet.json`; use it only on a branch app.
- `.venv/bin/python -m valtera verify <app-name>`: the data model (row counts against the CSV files, no synthetic keys, no circular references), master dimensions against the CSV files, every master measure against the Reference calculator in each of `SELECTIONS` (and amounts shown as `€x.xx bn` or `€x,xxx.x m`), the Customer concentration per Customer, every cell of the Product Line and Margin Sheet, the Sales Bridge effects adding up to the Sales change, the simulated measures in each What-If scenario (`SCENARIOS`), the side-by-side comparison inside its alternate states (see `app/CLAUDE.md`), then each Sheet captured in Chrome, the objects inside a layout container included (first run: sign in once in the window it opens). The lists are in `valtera/verify.py`. `--no-capture` skips the alternate states and the capture, and prints that the capture was skipped.
- `.venv/bin/python -m valtera clean <app-name>`: removes the app, its theme, its extensions, `.build/<app-name>/` and its claims on the shared data folders; a folder itself goes with its last claim (see `valtera/CLAUDE.md`).
- `.venv/bin/python -m unittest discover tests`: every test in `tests/`, with no tenant or key: fake `qlik` CLIs and fake pages stand in. The Sheet capture's tests need Chrome, and `tests/test_extensions.py` runs the Custom Extensions' own tests `extensions/*/test/*.test.mjs` with Node's test runner (needs Node 24).

The app name must start with `claude-` (use `claude-valtera-<branch>` per branch). It also names the tenant-wide theme `<app-name>` and each tenant-wide extension `<app-name>-<folder>`, so branches never collide.

### Master measures

`docs/measures.md` holds the rules every master measure follows (the Latest Date, YTD, Rolling 12 Months, Prior Year, Budget spread over days), their names and ids, the variables to build new ones from, and the three steps to add one. Each master measure needs a figure of the same name in the Reference calculator, computed from the CSV rows and never translated from the Qlik expression; verify fails on a measure missing on either side.

## Agent skills

### Issue tracker

Issues, the spec and tickets live in this repo's GitHub Issues. See `docs/agents/issue-tracker.md`.

### Triage labels

The five default triage labels, each named after its role. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `GLOSSARY.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.
