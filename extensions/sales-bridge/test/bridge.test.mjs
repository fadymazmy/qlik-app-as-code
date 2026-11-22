// The Sales Bridge's labels and states, from hypercube rows as Qlik returns them (amounts in EUR bn).
// Run with `node --test extensions/` (tests/test_extensions.priorYear runs it with the Python tests).
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { bridge, label } from '../src/bridge.js';

const cell = (qNum, qText = String(qNum)) => ({ qNum, qText });
// [Prior Year, Volume, Price, Mix, YTD, year]
const row = (priorYear, volume, price, mix) => [cell(priorYear), cell(volume), cell(price), cell(mix), cell(priorYear + volume + price + mix), cell(2026)];

test('an effect that rounds to zero shows 0.00 with no arrow', () => {
  const { bars, decimals } = bridge(row(0.635, 0.402, -0.0000004, 0.165));
  assert.deepEqual(label(bars[2], decimals), { text: '0.00', kind: 'flat' });
});

test('a small effect gets a third decimal and keeps its arrow', () => {
  const { bars, decimals } = bridge(row(0.635, 0.402, -0.003, 0.165));
  assert.equal(decimals, 3);
  assert.deepEqual(label(bars[2], decimals), { text: '▼ −0.003', kind: 'down' });
  assert.deepEqual(label(bars[1], decimals), { text: '▲ +0.402', kind: 'up' });
});

test('effects and totals with two decimals', () => {
  const { bars, decimals } = bridge(row(5.7, 0.4, -0.2, 0.1));
  assert.equal(decimals, 2);
  assert.deepEqual(label(bars[0], decimals), { text: '€5.70', kind: 'total' });
  assert.deepEqual(label(bars[1], decimals), { text: '▲ +0.40', kind: 'up' });
  assert.deepEqual(label(bars[2], decimals), { text: '▼ −0.20', kind: 'down' });
});

test('no Prior Year Sales gives the No Prior Year state, not a bridge from zero', () => {
  assert.deepEqual(bridge(row(0, 5.7, 0, 0)), { state: 'no prior year', year: 2026 });
});

test('a missing figure gives no bridge', () => {
  const r = row(1, 1, 1, 1);
  r[2] = { qNum: 'NaN', qText: '-' };
  assert.deepEqual(bridge(r), { state: 'empty' });
});

// On the Product Line and Margin Sheet the bridge reads the EUR m measures ("€5,710.2 m"): one decimal.
const rowM = (priorYear, volume, price, mix) => {
  const r = row(priorYear, volume, price, mix);
  r[4] = cell(priorYear + volume + price + mix, `€${(priorYear + volume + price + mix).toFixed(1)} m`);
  return r;
};

test('amounts in EUR m get one decimal and thousands separators', () => {
  const { bars, decimals, unit } = bridge(rowM(5710.2, 690.4, -41.3, 389.9));
  assert.equal(unit, 'm');
  assert.equal(decimals, 1);
  assert.deepEqual(label(bars[0], decimals), { text: '€5,710.2', kind: 'total' });
  assert.deepEqual(label(bars[2], decimals), { text: '▼ −41.3', kind: 'down' });
});

test('an effect that rounds to zero in EUR m shows 0.0 with no arrow', () => {
  const { bars, decimals } = bridge(rowM(57.2, 6.9, -0.02, 3.9));
  assert.deepEqual(label(bars[2], decimals), { text: '0.0', kind: 'flat' });
});
