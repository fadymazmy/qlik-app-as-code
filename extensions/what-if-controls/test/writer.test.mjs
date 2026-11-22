// How the What-If Controls write a variable, against a fake App (the Engine API's getVariableByName and
// setNumValue). Run with `node --test extensions/` (tests/test_extensions.py runs it with the Python tests).
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { writer } from '../src/writer.js';

const app = (setNumValue) => ({ getVariableByName: async () => ({ setNumValue }) });

// A writer for vPriceChange, and a promise of its first idle moment.
function priceWriter(setNumValue) {
  const errors = [];
  let idle;
  const idled = new Promise((resolve) => (idle = resolve));
  const send = writer(app(setNumValue), 'vPriceChange', { onIdle: idle, onError: (e) => errors.push(e.message) });
  return { send, errors, idled };
}

test('a write the App refuses is reported, and the writer goes idle so the slider shows the App value again', async () => {
  const { send, errors, idled } = priceWriter(async () => { throw new Error('access denied'); });
  send(5);
  await idled;
  assert.deepEqual(errors, ['access denied']);
  assert.equal(send.busy(), false);
});

test('while a write is under way, only the newest value waits for it', async () => {
  const written = [];
  const { send, errors, idled } = priceWriter(async (v) => { written.push(v); });
  send(1);
  send(2);
  send(3);
  await idled;
  assert.deepEqual(written, [1, 3]);
  assert.deepEqual(errors, []);
});
