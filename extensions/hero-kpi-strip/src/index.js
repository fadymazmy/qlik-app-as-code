// Hero KPI Strip: Sales, Gross Margin, Order Intake and Budget Attainment for the year to date, each with a
// sparkline of its monthly trend and its variances. It only draws: every figure is a master measure in the
// object's hypercubes (app/sheets/executive-overview.json), shown with the text Qlik formats for it, and the
// colours and font come from the theme. No network requests.
import { useEffect, useElement, useLayout, useTheme } from '@nebula.js/stardust';
import { esc, fullCard, themeStyle } from '../../shared';

// Each tile: its value, its variance lines and its sparkline, by master measure id. The sparkline is the YTD
// measure by Year Month, so it has one point per month of YTD whatever the calendar selection. In every variance
// here a higher value is favourable. Gross Margin and Order Intake have no Budget, so they have no Budget line.
const TILES = [
  { label: 'Sales', value: 'm_sales_ytd', spark: 'm_sales_ytd',
    lines: [['m_sales_ytd_vs_prior_year_pct', 'vs Prior Year'], ['m_sales_ytd_vs_budget_pct', 'vs Budget']] },
  { label: 'Gross Margin', value: 'm_gross_margin_ytd', spark: 'm_gross_margin_ytd',
    lines: [['m_gross_margin_ytd_vs_prior_year', 'vs Prior Year']] },
  { label: 'Order Intake', value: 'm_order_intake_ytd', spark: 'm_order_intake_ytd',
    lines: [['m_order_intake_ytd_vs_prior_year_pct', 'vs Prior Year']], ratio: ['m_book_to_bill_ytd', 'Book-to-bill'] },
  { label: 'Budget Attainment', value: 'm_budget_attainment_ytd', spark: 'm_budget_attainment_ytd',
    shortfall: 'm_sales_ytd_vs_budget', bar: true },
];

// Two grid rows are about 115 px high at 1440 x 900 under Qlik's bar; below 106 px the variances share one line.
const CSS = `
.hks { height: 100%; container-type: size; overflow: hidden; border-radius: var(--radius);
  font-family: var(--font); color: var(--text); -webkit-font-smoothing: antialiased;
  background: radial-gradient(120% 140% at 0% 0%, color-mix(in srgb, var(--accent) 10%, transparent), transparent 55%), var(--surface); }
.hks .tiles { height: 100%; display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); }
.hks .kpi { min-width: 0; padding: 10px 16px; display: grid; grid-template-columns: minmax(0, 1fr) auto;
  grid-template-rows: auto auto 1fr; column-gap: 12px; }
.hks .kpi + .kpi { border-left: 1px solid var(--divider); }
.hks .label { grid-column: 1 / 3; display: flex; justify-content: space-between; gap: 8px; font-size: 12px;
  line-height: 15px; font-weight: 600; color: var(--text2); white-space: nowrap; }
.hks .label span { font-weight: 400; color: var(--muted); overflow: hidden; text-overflow: ellipsis; }
.hks .value { margin-top: 2px; font-size: 28px; font-weight: 700; line-height: 34px; letter-spacing: -.01em;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-variant-numeric: tabular-nums; }
.hks .value small { margin-left: 2px; font-size: 14px; font-weight: 600; color: var(--text2); }
.hks .spark { width: 112px; height: 34px; margin-top: 4px; }
.hks .spark svg { display: block; overflow: visible; }
.hks .vars { grid-column: 1 / 3; align-self: end; display: flex; flex-direction: column; gap: 2px; font-size: 12px;
  line-height: 15px; color: var(--text2); white-space: nowrap; overflow: hidden; font-variant-numeric: tabular-nums; }
.hks .pos { color: var(--pos); font-weight: 600; }
.hks .neg { color: var(--neg); font-weight: 600; }
.hks .neu { color: var(--text); font-weight: 600; }
.hks .note { color: var(--muted); overflow: hidden; text-overflow: ellipsis; }
.hks .bar { height: 4px; margin-top: 4px; border-radius: 2px; background: var(--divider); overflow: hidden; }
.hks .bar div { height: 100%; border-radius: 2px; background: var(--accent); }
@container (max-height: 105px) {
  .hks .kpi { padding: 6px 14px; }
  .hks .value { font-size: 22px; line-height: 30px; }
  .hks .spark { margin-top: 0; }
  .hks .vars { flex-direction: row; align-items: center; gap: 12px; }
  .hks .bar { flex: 1 1 40px; margin-top: 0; }
}
.hks-error { padding: 12px; color: var(--neg); font: 12px var(--font); }
`;

const YEAR_MONTH = /^(\d{4})-(\w{3})$/; // Year Month as the App shows it, e.g. "2026-Oct"

const isNumber = (cell) => cell && typeof cell.qNum === 'number' && !Number.isNaN(cell.qNum);

// {master measure id: column index} of a hypercube layout.
function columns(cube) {
  return Object.fromEntries((cube.qMeasureInfo || []).map((m, i) => [m.qLibraryId, i + (cube.qDimensionInfo || []).length]));
}

// The value as Qlik formats it, with its unit ("bn", "%") set smaller after the number: "€17.62 bn" -> €17.62 + bn.
function valueHtml(cell) {
  if (!isNumber(cell)) return '–';
  const [, number, unit] = /^(.*?)\s*(bn|%)?$/.exec(cell.qText);
  return `${esc(number)}${unit ? `<small>${esc(unit)}</small>` : ''}`;
}

// A variance with an arrow as well as a colour: ▲ favourable, ▼ unfavourable, no arrow for none.
function varianceHtml(cell, text) {
  if (!isNumber(cell)) return `<span><span class="neu">–</span> ${esc(text)}</span>`;
  const shown = esc(cell.qText.replace(/^[+-]/, ''));
  if (cell.qNum > 0) return `<span><span class="pos"><span aria-label="up">&#9650;</span> ${shown}</span> ${esc(text)}</span>`;
  if (cell.qNum < 0) return `<span><span class="neg"><span aria-label="down">&#9660;</span> ${shown}</span> ${esc(text)}</span>`;
  return `<span><span class="neu">${shown}</span> ${esc(text)}</span>`;
}

// Budget is planned by Product Line, Country and Channel only, so under a selection in Customer or Production
// Site every Budget measure is null: say so instead of showing a figure.
function shortfallHtml(cell) {
  if (!isNumber(cell)) return '<span class="note">No Budget by Customer or Production Site</span>';
  return varianceHtml(cell, cell.qNum < 0 ? 'short of Budget' : 'ahead of Budget');
}

// A ratio with no good or bad direction, such as "Book-to-bill 1.10": no arrow, no colour.
function ratioHtml(cell, text) {
  return `<span>${esc(text)} <span class="neu">${isNumber(cell) ? esc(cell.qText) : '–'}</span></span>`;
}

function sparkSvg(points, id) {
  const values = points.filter((v) => v != null);
  if (!values.length) return '';
  const w = 112, h = 34, p = 4;
  const min = Math.min(...values), max = Math.max(...values);
  const x = (i) => p + (points.length > 1 ? (i * (w - 2 * p)) / (points.length - 1) : (w - 2 * p) / 2);
  const y = (v) => h - p - ((v - min) / (max - min || 1)) * (h - 2 * p) - (max === min ? (h - 2 * p) / 2 : 0);
  const xy = points.map((v, i) => (v == null ? null : [x(i).toFixed(1), y(v).toFixed(1)])).filter(Boolean);
  const line = xy.map((q) => q.join(',')).join(' ');
  const [lx, ly] = xy[xy.length - 1];
  const area = `M${xy[0][0]},${h} L${line.split(' ').join(' L')} L${lx},${h} Z`;
  return `<svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" aria-hidden="true">
<defs><linearGradient id="${id}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" style="stop-color: var(--accent); stop-opacity: .28"/>
<stop offset="1" style="stop-color: var(--accent); stop-opacity: 0"/></linearGradient></defs>
<path d="${area}" fill="url(#${id})"/><polyline points="${line}" style="fill: none; stroke: var(--accent); stroke-width: 2;
stroke-linejoin: round; stroke-linecap: round"/><circle cx="${lx}" cy="${ly}" r="3.5" style="fill: var(--accent);
stroke: var(--surface); stroke-width: 2"/></svg>`;
}

// "YTD Oct 2026" from the last month of the sparkline, which ends at the Latest Date's month.
function period(rows) {
  const last = rows.length ? YEAR_MONTH.exec(rows[rows.length - 1][0].qText) : null;
  return last ? `YTD ${last[2]} ${last[1]}` : 'YTD';
}

// The strip fills its whole card, up to the border, with the card's rounded corners.
function stripStyle(theme) {
  return `${themeStyle(theme)}; --radius: ${theme.getStyle('object', '', 'borderRadius') || '0px'}; ${fullCard(theme)}`;
}

function render(layout, style) {
  const cube = layout.qHyperCube;
  const spark = layout.sparkline && layout.sparkline.qHyperCube;
  const row = (cube && cube.qDataPages[0] && cube.qDataPages[0].qMatrix[0]) || [];
  const rows = (spark && spark.qDataPages[0] && spark.qDataPages[0].qMatrix) || [];
  const col = cube ? columns(cube) : {};
  const sparkCol = spark ? columns(spark) : {};
  const ids = TILES.flatMap((t) => [t.value, ...(t.lines || []).map((l) => l[0]), ...(t.shortfall ? [t.shortfall] : []),
    ...(t.ratio ? [t.ratio[0]] : [])]);
  const missing = [...ids.filter((id) => !(id in col)), ...TILES.map((t) => t.spark).filter((id) => !(id in sparkCol))];
  if (missing.length) {
    return `<style>${CSS}</style><div class="hks-error" style="${esc(style)}">Hero KPI Strip error: master measures missing from the object: ${esc(missing.join(', '))}</div>`;
  }
  const tiles = TILES.map((t, i) => {
    const value = row[col[t.value]];
    const lines = (t.lines || []).map(([id, text]) => varianceHtml(row[col[id]], text));
    if (t.shortfall) lines.push(shortfallHtml(row[col[t.shortfall]]));
    if (t.ratio) lines.push(ratioHtml(row[col[t.ratio[0]]], t.ratio[1]));
    if (t.bar && isNumber(value)) {
      const pct = isNumber(value) ? Math.max(0, Math.min(1, value.qNum)) * 100 : 0;
      lines.push(`<div class="bar" aria-hidden="true"><div style="width: ${pct.toFixed(1)}%"></div></div>`);
    }
    const points = rows.map((r) => (isNumber(r[sparkCol[t.spark]]) ? r[sparkCol[t.spark]].qNum : null));
    return `<div class="kpi">
  <div class="label">${esc(t.label)}<span>${i === 0 ? esc(period(rows)) : 'YTD'}</span></div>
  <div class="value">${valueHtml(value)}</div>
  <div class="spark">${sparkSvg(points, `hks-${esc(layout.qInfo.qId)}-${i}`)}</div>
  <div class="vars">${lines.join('')}</div>
</div>`;
  });
  return `<style>${CSS}</style><section class="hks" style="${esc(style)}" aria-label="Year to date headline figures"><div class="tiles">${tiles.join('')}</div></section>`;
}

export default function supernova() {
  return {
    qae: { properties: { initial: { showTitles: false } } },
    component() {
      const element = useElement();
      const layout = useLayout();
      const theme = useTheme();
      useEffect(() => {
        element.innerHTML = render(layout, stripStyle(theme));
      }, [element, layout, theme]);
    },
  };
}
