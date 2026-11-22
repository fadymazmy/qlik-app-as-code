// What-If Controls: one slider each for the price, volume and EUR exchange rate change, and a reset.
// The sliders write the App's What-If variables; their current values come back through the layout (the
// object's properties hold `$(vPriceChange)` and so on as value expressions), and so does the exchange rate
// assumption shown underneath. Colours and font come from the theme. No network requests.
import { useApp, useEffect, useElement, useLayout, useState, useTheme } from '@nebula.js/stardust';
import { esc, themeStyle } from '../../shared';
import { writer } from './writer';

// The three controls: layout key, the variable it writes, and what a change means (docs/measures.md).
const CONTROLS = [
  { key: 'price', variable: 'vPriceChange', label: 'Price', hint: 'Net prices; cost stays, so all of it reaches margin.' },
  { key: 'volume', variable: 'vVolumeChange', label: 'Volume', hint: 'Units sold; Sales and cost move together.' },
  { key: 'exchangeRate', variable: 'vExchangeRateChange', label: 'EUR exchange rate', hint: '+ is a stronger euro: foreign Sales is worth less.' },
];
const RANGE = { min: -20, max: 20, step: 1 };

const CSS = `
.wic { height: 100%; display: flex; flex-direction: column; gap: 12px; overflow: auto; font-family: var(--font);
  color: var(--text); -webkit-font-smoothing: antialiased; font-variant-numeric: tabular-nums; }
.wic .ctl { display: flex; flex-direction: column; gap: 4px; padding-bottom: 12px; border-bottom: 1px solid var(--border); }
.wic .head { display: flex; justify-content: space-between; align-items: baseline; }
.wic label { font-size: 12px; font-weight: 600; color: var(--text2); }
.wic output { font-size: 18px; font-weight: 600; line-height: 24px; color: var(--muted); }
.wic output.on { color: var(--text); }
.wic input[type=range] { -webkit-appearance: none; appearance: none; width: 100%; height: 22px; margin: 0;
  background: transparent; cursor: pointer; --fill: linear-gradient(90deg, transparent var(--from), var(--accent) var(--from),
  var(--accent) var(--to), transparent var(--to)); }
.wic input[type=range]:focus { outline: none; }
.wic input[type=range]::-webkit-slider-runnable-track { height: 4px; border-radius: 2px; background: var(--fill), var(--border2); }
.wic input[type=range]::-moz-range-track { height: 4px; border-radius: 2px; background: var(--fill), var(--border2); }
.wic input[type=range]::-webkit-slider-thumb { -webkit-appearance: none; appearance: none; width: 16px; height: 16px;
  margin-top: -6px; border-radius: 50%; background: var(--accent); border: 3px solid var(--raised);
  box-shadow: 0 0 0 1px var(--accent); }
.wic input[type=range]::-moz-range-thumb { width: 10px; height: 10px; border-radius: 50%; background: var(--accent);
  border: 3px solid var(--raised); box-shadow: 0 0 0 1px var(--accent); }
.wic input[type=range]:focus-visible::-webkit-slider-thumb { box-shadow: 0 0 0 1px var(--accent), 0 0 0 5px color-mix(in srgb, var(--accent) 30%, transparent); }
.wic input[type=range]:focus-visible::-moz-range-thumb { box-shadow: 0 0 0 1px var(--accent), 0 0 0 5px color-mix(in srgb, var(--accent) 30%, transparent); }
.wic .scale { display: flex; justify-content: space-between; font-size: 10.5px; color: var(--muted); margin-top: -2px; }
.wic .hint { margin: 0; font-size: 11px; line-height: 15px; color: var(--text2); }
.wic .reset { align-self: flex-start; font: inherit; font-size: 12px; font-weight: 600; color: var(--text); cursor: pointer;
  background: var(--raised); border: 1px solid var(--border2); border-radius: 6px; padding: 6px 12px; }
.wic .reset:hover { background: var(--hover); }
.wic .reset:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.wic .reset:disabled { color: var(--muted); cursor: default; background: transparent; }
.wic .error { margin: 0; font-size: 11px; line-height: 15px; color: var(--neg); }
.wic .error:empty { display: none; }
.wic .note { margin: auto 0 0; font-size: 10.5px; line-height: 15px; color: var(--muted); }
.wic .note b { font-weight: 600; color: var(--text2); }
`;

// "+5%", "0%", "−5%" (a true minus sign).
function percent(value) {
  if (!Number.isFinite(value)) return '–';
  return `${value > 0 ? '+' : value < 0 ? '−' : ''}${Math.abs(value)}%`;
}

function render(id, style) {
  const controls = CONTROLS.map(
    (c) => `<div class="ctl" data-key="${c.key}">
  <div class="head"><label for="${esc(id)}-${c.key}">${esc(c.label)}</label><output for="${esc(id)}-${c.key}"></output></div>
  <input type="range" id="${esc(id)}-${c.key}" min="${RANGE.min}" max="${RANGE.max}" step="${RANGE.step}" value="0">
  <div class="scale" aria-hidden="true"><span>${percent(RANGE.min)}</span><span>0</span><span>${percent(RANGE.max)}</span></div>
  <p class="hint">${esc(c.hint)}</p>
</div>`
  ).join('');
  return `<style>${CSS}</style>
<div class="wic" style="${esc(style)}" role="group" aria-label="What-If scenario">
  ${controls}
  <button class="reset" type="button">Reset to Actual</button>
  <p class="error" role="alert"></p>
  <p class="note"></p>
</div>`;
}

// Shows a value on its slider: the number, and the accent fill from zero to the thumb.
function show(ctl, value) {
  const input = ctl.querySelector('input');
  const output = ctl.querySelector('output');
  const v = Number.isFinite(value) ? value : 0;
  const at = (x) => `${((x - RANGE.min) / (RANGE.max - RANGE.min)) * 100}%`;
  input.value = String(v);
  input.style.setProperty('--from', at(Math.min(0, v)));
  input.style.setProperty('--to', at(Math.max(0, v)));
  input.setAttribute('aria-valuetext', percent(value));
  output.textContent = percent(value);
  output.classList.toggle('on', v !== 0);
}

export default function supernova() {
  return {
    qae: {
      properties: {
        initial: {
          showTitles: true,
          title: 'What-If scenario',
          price: { qValueExpression: { qExpr: '$(vPriceChange)' } },
          volume: { qValueExpression: { qExpr: '$(vVolumeChange)' } },
          exchangeRate: { qValueExpression: { qExpr: '$(vExchangeRateChange)' } },
          localCostShare: { qValueExpression: { qExpr: '$(vLocalCostShare)' } },
          euroArea: { qStringExpression: { qExpr: "='$(vEuroArea)'" } },
        },
      },
    },
    component() {
      const element = useElement();
      const layout = useLayout();
      const app = useApp();
      const theme = useTheme();
      const [writers, setWriters] = useState(null);
      const [, setIdle] = useState(0);

      // Draw once per object and theme; later layouts only update the values, so a drag is never interrupted.
      useEffect(() => {
        element.innerHTML = render(layout.qInfo.qId, themeStyle(theme));
        const w = {};
        const error = element.querySelector('.error');
        CONTROLS.forEach((c) => {
          // A write the App refused is said under the sliders; going idle redraws the slider from the App's value.
          w[c.key] = writer(app, c.variable, {
            onIdle: () => setIdle((n) => n + 1),
            onError: (e) => {
              error.textContent = `The App did not take the ${c.label} change (${(e && e.message) || e}), so the slider shows the App's value.`;
            },
          });
        });
        element.oninput = (e) => {
          const ctl = e.target.closest('.ctl');
          if (!ctl) return;
          const value = Number(e.target.value);
          error.textContent = '';
          show(ctl, value);
          w[ctl.dataset.key](value);
          element.querySelector('.reset').disabled = false;
        };
        element.onclick = (e) => {
          if (!e.target.closest('.reset')) return;
          error.textContent = '';
          CONTROLS.forEach((c) => {
            show(element.querySelector(`.ctl[data-key="${c.key}"]`), 0);
            w[c.key](0);
          });
        };
        setWriters(w);
      }, [element, app, theme, layout.qInfo.qId]);

      useEffect(() => {
        if (!writers) return;
        let changed = false;
        CONTROLS.forEach((c) => {
          const ctl = element.querySelector(`.ctl[data-key="${c.key}"]`);
          // A slider that is still writing shows its own value; the layout catches up when the write is done.
          if (!writers[c.key].busy()) show(ctl, layout[c.key]);
          changed = changed || Number(ctl.querySelector('input').value) !== 0;
        });
        element.querySelector('.reset').disabled = !changed;
        const share = layout.localCostShare;
        element.querySelector('.note').innerHTML = `<b>Exchange rate assumption.</b> Valtera reports in EUR; the euro area here is ${esc(
          layout.euroArea || '–'
        )}. Sales to any other Country is in its local currency, and ${Number.isFinite(share) ? Math.round(share * 100) : '–'}% of its cost is local; the rest is bought in EUR.`;
      });
    },
  };
}
