// Sales Bridge: Sales YTD Prior Year, the volume, price and mix effects, and Sales YTD, as a bridge.
// It only draws: the five amounts come from master measures in its hypercube (in EUR bn, or EUR m on the
// Product Line and Margin Sheet; the labels are short, as the subtitle gives the unit, and the tooltips carry
// the measures' own text) and the year from
// the App's Latest Date; colours and font come from the theme. A favourable effect is marked by ▲ and an
// unfavourable one by ▼ as well as by colour. No network requests.
import { useEffect, useElement, useLayout, useRect, useTheme } from '@nebula.js/stardust';
import { esc, themeStyle } from '../../shared';
import { amount, bridge, label } from './bridge';

const CSS = `
.vsb { height: 100%; display: flex; flex-direction: column; font-family: var(--font); color: var(--text);
  -webkit-font-smoothing: antialiased; }
.vsb svg { flex: none; display: block; overflow: visible; }
.vsb text { font-family: var(--font); font-variant-numeric: tabular-nums; }
.vsb .val { font-size: 11.5px; font-weight: 600; fill: var(--text); }
.vsb .val.up { fill: var(--pos); }
.vsb .val.down { fill: var(--neg); }
.vsb .cat { font-size: 10.5px; fill: var(--text2); }
.vsb .bar.total { fill: color-mix(in srgb, var(--text2) 72%, var(--surface)); }
.vsb .bar.up { fill: var(--accent); }
.vsb .bar.down { fill: var(--neg); }
.vsb .bar.flat { fill: var(--muted); }
.vsb .break { stroke: var(--surface); stroke-width: 3; }
.vsb .link { stroke: var(--muted); stroke-dasharray: 2 3; }
.vsb .base { stroke: var(--border2); }
.vsb .foot { flex: none; font-size: 10.5px; color: var(--muted); padding-top: 4px; }
.vsb .empty { margin: auto; font-size: 12px; color: var(--muted); }
.vsb .state { margin: auto; max-width: 300px; text-align: center; font-size: 12px; line-height: 17px; color: var(--text2); }
.vsb .state strong { display: block; margin-bottom: 4px; font-size: 14px; font-weight: 600; color: var(--text); }
`;

// The axis starts below the lowest level so that the effects are visible; the totals then carry break marks.
function axisStart(bars) {
  const levels = bars.flatMap((b) => (b.total ? [b.to] : [b.from, b.to]));
  const lo = Math.min(...levels);
  const hi = Math.max(...levels);
  const span = hi - lo || Math.abs(hi) * 0.1 || 1;
  const step = 10 ** Math.floor(Math.log10(span));
  const start = Math.floor((lo - span * 0.8) / step) * step;
  return start > 0 ? start : 0;
}

function chart(bars, decimals, unit, width, height) {
  const top = 22;
  const bottom = 22;
  const lo = axisStart(bars);
  const hi = Math.max(...bars.flatMap((b) => [b.from, b.to]));
  const y = (v) => top + (height - top - bottom) * (1 - (v - lo) / (hi - lo || 1));
  const band = width / bars.length;
  const bw = Math.min(64, band * 0.58);
  let g = '';
  bars.forEach((b, i) => {
    const cx = band * i + band / 2;
    const { text: short, kind } = label(b, decimals);
    const y1 = b.total ? y(b.to) : y(Math.max(b.from, b.to));
    const y2 = b.total ? y(lo) : y(Math.min(b.from, b.to));
    const glyph = { up: '▲ ', down: '▼ ' }[kind] || '';
    const title = `${b.label}: ${glyph}${b.text}`;
    g += `<g role="listitem" aria-label="${esc(title)}"><title>${esc(title)}</title>`;
    g += `<rect class="bar ${kind}" x="${cx - bw / 2}" y="${y1}" width="${bw}" height="${Math.max(2, y2 - y1)}" rx="3"/>`;
    if (b.total && lo > 0) {
      g += `<path class="break" d="M${cx - bw / 2 - 3},${y2 - 9} l${bw + 6},-5 M${cx - bw / 2 - 3},${y2 - 4} l${bw + 6},-5"/>`;
    }
    g += `<text class="val ${kind}" x="${cx}" y="${y1 - 7}" text-anchor="middle">${esc(short)}</text>`;
    g += `<text class="cat" x="${cx}" y="${height - 6}" text-anchor="middle">${esc(b.label)}</text></g>`;
    if (i < bars.length - 1) {
      const next = band * (i + 1) + band / 2 - bw / 2;
      g += `<line class="link" x1="${cx + bw / 2}" x2="${next}" y1="${y(b.to)}" y2="${y(b.to)}"/>`;
    }
  });
  g += `<line class="base" x1="0" x2="${width}" y1="${y(lo)}" y2="${y(lo)}"/>`;
  const foot = lo > 0 ? `<div class="foot">Axis starts at €${amount(lo, decimals)} ${unit}</div>` : '';
  return { svg: `<svg role="list" aria-label="Sales Bridge" viewBox="0 0 ${width} ${height}" width="${width}" height="${height}">${g}</svg>`, foot };
}

export default function supernova() {
  return {
    qae: {
      properties: {
        initial: {
          showTitles: true,
          qHyperCubeDef: { qMeasures: [], qInitialDataFetch: [{ qLeft: 0, qTop: 0, qWidth: 6, qHeight: 1 }] },
        },
      },
      data: { targets: [{ path: '/qHyperCubeDef', dimensions: { min: 0, max: 0 }, measures: { min: 5, max: 6 } }] },
    },
    component() {
      const element = useElement();
      const layout = useLayout();
      const theme = useTheme();
      const rect = useRect();

      useEffect(() => {
        const page = layout.qHyperCube && layout.qHyperCube.qDataPages[0];
        const { bars, decimals, unit, state, year } = page && page.qMatrix.length ? bridge(page.qMatrix[0]) : { state: 'empty' };
        let body = '<div class="empty">No Sales in the current selection</div>';
        if (state === 'no prior year') {
          body = `<div class="state" role="status"><strong>No Prior Year</strong>There are no Sales in the Prior Year
            YTD${year ? ` (${year - 1})` : ''} for this selection, so the change cannot be split into volume, price and mix.</div>`;
        } else if (bars) {
          const svgHeight = Math.max(60, rect.height - (axisStart(bars) > 0 ? 20 : 0));
          const { svg, foot } = chart(bars, decimals, unit, Math.max(60, rect.width), svgHeight);
          body = svg + foot;
        }
        element.innerHTML = `<style>${CSS}</style><div class="vsb" style="${esc(themeStyle(theme))}">${body}</div>`;
      }, [element, layout, theme, rect.width, rect.height]);
    },
  };
}
