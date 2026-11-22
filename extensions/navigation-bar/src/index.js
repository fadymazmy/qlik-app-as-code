// Navigation Bar: the five Sheets with the current one marked, the current selections with
// "Clear all", and the Synthetic Data label. It only draws: sheets, selections and colours all come
// from the App (the sheet list, the selection object and the theme). No network requests.
import { useApp, useEffect, useElement, useLayout, useNavigation, usePromise, useRect, useTheme } from '@nebula.js/stardust';
import { esc, fullCard, themeStyle } from '../../shared';

const CSS = `
.vnb { height: 100%; display: flex; align-items: center; gap: 18px; overflow: hidden; font-family: var(--font);
  color: var(--text); -webkit-font-smoothing: antialiased; }
.vnb button { font: inherit; color: inherit; background: none; border: 0; padding: 0; cursor: pointer; }
.vnb .brand { display: flex; align-items: center; gap: 10px; flex: none; }
.vnb .brand-name { font-size: 16px; font-weight: 700; }
.vnb .brand-sub { font-size: 11px; color: var(--text2); border-left: 1px solid var(--border); padding-left: 10px; }
.vnb .tabs { display: flex; gap: 4px; margin: 0; padding: 0; list-style: none; height: 100%; flex: 0 1 auto; min-width: 0;
  overflow: hidden; }
.vnb .tabs li { display: flex; height: 100%; }
.vnb .tab { position: relative; padding: 0 11px; font-size: 13px; color: var(--text2); white-space: nowrap; }
.vnb .tab:hover { color: var(--text); }
.vnb .tab[aria-current="page"] { color: var(--text); font-weight: 600; }
.vnb .tab[aria-current="page"]::after { content: ""; position: absolute; left: 11px; right: 11px; bottom: 0;
  height: 2px; border-radius: 2px 2px 0 0; background: var(--accent); }
.vnb .right { flex: none; margin-left: auto; display: flex; align-items: center; gap: 12px; }
.vnb .right > * { flex: none; }
.vnb .sel-label { font-size: 11px; color: var(--muted); }
.vnb .chips { display: flex; gap: 6px; }
.vnb.no-sub .brand-sub, .vnb.no-caption .sel-label, .vnb.values-only .chip .field { display: none; }
.vnb .chip { flex: none; display: inline-flex; align-items: center; gap: 6px; font-size: 12px; padding: 4px 6px 4px 9px;
  border-radius: 6px; background: color-mix(in srgb, var(--accent) 12%, transparent);
  border: 1px solid color-mix(in srgb, var(--accent) 35%, transparent); white-space: nowrap; }
.vnb .chip b { font-weight: 600; }
.vnb .chip button { color: var(--text2); padding: 0 3px; }
.vnb .chip.more { padding-right: 9px; cursor: default; }
.vnb .chip[hidden] { display: none; }
.vnb .none { font-size: 12px; color: var(--muted); }
.vnb .clear { font-size: 12px; color: var(--text2); }
.vnb .clear:hover, .vnb .chip button:hover { color: var(--text); }
.vnb .clear:disabled { color: var(--muted); cursor: default; }
.vnb .synthetic { display: inline-flex; align-items: center; gap: 6px; font-size: 11.5px; font-weight: 600;
  color: var(--synthetic); padding: 4px 9px; border: 1px solid color-mix(in srgb, var(--synthetic) 45%, transparent);
  border-radius: 999px; white-space: nowrap; }
.vnb .synthetic::before { content: ""; width: 7px; height: 7px; border-radius: 50%; background: var(--synthetic); }
`;

const LOGO = `<svg width="26" height="26" viewBox="0 0 26 26" aria-hidden="true"><rect width="26" height="26" rx="7"
  style="fill: color-mix(in srgb, var(--accent) 12%, transparent)"/><path d="M6 8l7 11 7-11" style="fill: none;
  stroke: var(--accent); stroke-width: 2.6; stroke-linecap: round; stroke-linejoin: round"/></svg>`;

// The bar spans its whole card, up to the border: one grid row leaves too little height inside the
// theme's object padding, so the bar takes that padding back and pads itself.
function barStyle(theme) {
  return `${themeStyle(theme)}; ${fullCard(theme)}; padding: 0 16px`;
}

function fetchSheets(app) {
  return app
    .createSessionObject({
      qInfo: { qType: 'navigation-bar-sheets' },
      qAppObjectListDef: { qType: 'sheet', qData: { title: '/qMetaDef/title', rank: '/rank' } },
    })
    .then((list) =>
      list.getLayout().then((layout) => {
        app.destroySessionObject(list.id);
        return layout.qAppObjectList.qItems
          .map((i) => ({ id: i.qInfo.qId, title: i.qData.title, rank: i.qData.rank || 0 }))
          .sort((a, b) => a.rank - b.rank);
      })
    );
}

// When the bar is too narrow, it gives way one step at a time, least visible first, until it fits:
// drop the "Sales analytics" sub-label, show chips as value only (the field stays in each chip's
// tooltip), drop the "Current selections" caption, then fold the last chips into one "+N" chip whose
// tooltip lists them. Whatever a later step freed is then given back (field names first). "Clear all"
// and the Synthetic Data label always stay; only past all of that do the Sheet tabs get cut, rather
// than being overlapped.
const STEPS = ['no-sub', 'values-only', 'no-caption'];

function fit(nav) {
  const tabs = nav.querySelector('.tabs');
  const chips = [...nav.querySelectorAll('.chip:not(.more)')];
  const more = nav.querySelector('.chip.more');
  const fits = () => nav.scrollWidth <= nav.clientWidth && tabs.scrollWidth <= tabs.clientWidth;
  nav.classList.remove(...STEPS);
  chips.forEach((c) => (c.hidden = false));
  if (more) more.hidden = true;
  for (const step of STEPS) {
    if (fits()) break;
    nav.classList.add(step);
  }
  for (let hidden = 1; hidden <= chips.length && !fits(); hidden += 1) {
    const folded = chips.slice(-hidden);
    chips.forEach((c) => (c.hidden = folded.includes(c)));
    more.hidden = false;
    more.textContent = `+${hidden}`;
    more.title = folded.map((c) => c.title).join('\n');
    more.setAttribute('aria-label', `${hidden} more: ${more.title}`);
  }
  for (const step of ['values-only', 'no-caption', 'no-sub']) {
    nav.classList.remove(step);
    if (!fits()) nav.classList.add(step);
  }
}

function render({ sheets, current, selections, style }) {
  const tabs = sheets
    .map((s) => `<li><button class="tab" data-sheet="${esc(s.id)}"${s.id === current ? ' aria-current="page"' : ''}>${esc(s.title)}</button></li>`)
    .join('');
  const chips = selections.length
    ? `<span class="chips">${selections
        .map((s) => `<span class="chip" title="${esc(`${s.qField}: ${s.qSelected}`)}"><span class="field">${esc(s.qField)}</span> <b>${esc(s.qSelected)}</b><button data-clear-field="${esc(s.qField)}" aria-label="Clear ${esc(s.qField)}">&times;</button></span>`)
        .join('')}<span class="chip more" tabindex="0" hidden></span></span>`
    : '<span class="none">None</span>';
  return `<style>${CSS}</style>
<nav class="vnb" style="${esc(style)}" aria-label="Sheets">
  <div class="brand">${LOGO}<span class="brand-name">Valtera</span><span class="brand-sub">Sales analytics</span></div>
  <ul class="tabs">${tabs}</ul>
  <div class="right">
    <span class="sel-label">Current selections</span>${chips}
    <button class="clear" data-clear-all${selections.length ? '' : ' disabled'}>Clear all</button>
    <span class="synthetic" title="All figures are Synthetic Data">Synthetic Data</span>
  </div>
</nav>`;
}

export default function supernova() {
  return {
    qae: { properties: { initial: { showTitles: false, qSelectionObjectDef: {} } } },
    component() {
      const element = useElement();
      const layout = useLayout();
      const app = useApp();
      const theme = useTheme();
      const navigation = useNavigation();
      const [sheets] = usePromise(() => fetchSheets(app), [app]);
      const rect = useRect();

      useEffect(() => {
        element.onclick = (e) => {
          const target = e.target.closest('button');
          if (!target) return;
          if (target.dataset.sheet) navigation.goToSheet(target.dataset.sheet);
          else if (target.hasAttribute('data-clear-all')) app.clearAll();
          else if (target.dataset.clearField) app.getField(target.dataset.clearField).then((f) => f.clear());
        };
      }, [element, app, navigation]);

      useEffect(() => {
        element.innerHTML = render({
          sheets: sheets || [],
          current: navigation && navigation.getCurrentSheetId ? navigation.getCurrentSheetId() : null,
          selections: (layout.qSelectionObject && layout.qSelectionObject.qSelections) || [],
          style: barStyle(theme),
        });
        const nav = element.querySelector('.vnb');
        fit(nav);
        // Widths change once the theme's font has loaded.
        document.fonts.ready.then(() => nav.isConnected && fit(nav));
      }, [element, sheets, layout, theme, navigation, rect.width]);
    },
  };
}
