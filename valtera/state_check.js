// Runs inside a signed-in browser tab on the tenant. Opens its own engine session on the App (a separate
// identity, so the Sheet on screen is not disturbed), makes each side's selection in its alternate state,
// and evaluates the given master measures in a hypercube of that state, all sides in the one session.
// Input {appId, sides: {state: {field: value}}, measures: [library id]}; returns {state: [{qText, qNum}]}.
async ({ appId, sides, measures }) => {
  const csrf = (await fetch("/api/v1/csrf-token", { credentials: "include" })).headers.get("qlik-csrf-token");
  const url = `wss://${location.host}/app/${appId}/identity/valtera-verify-${Date.now()}` +
    `?qlik-csrf-token=${encodeURIComponent(csrf || "")}`;
  const ws = new WebSocket(url);
  const pending = new Map();
  let next = 1;
  ws.onmessage = (e) => {
    const msg = JSON.parse(e.data);
    const p = pending.get(msg.id);
    if (!p) return;
    pending.delete(msg.id);
    msg.error ? p.reject(new Error(JSON.stringify(msg.error))) : p.resolve(msg.result);
  };
  ws.onclose = (e) => pending.forEach((p) => p.reject(new Error(`engine session closed: ${e.code} ${e.reason}`)));
  await new Promise((resolve, reject) => { ws.onopen = resolve; ws.onerror = () => reject(new Error("websocket")); });
  const call = (handle, method, params) => new Promise((resolve, reject) => {
    const id = next++;
    pending.set(id, { resolve, reject });
    ws.send(JSON.stringify({ jsonrpc: "2.0", id, handle, method, params }));
  });
  try {
    const doc = (await call(-1, "OpenDoc", { qDocName: appId })).qReturn.qHandle;
    for (const [state, selection] of Object.entries(sides)) {
      for (const [field, value] of Object.entries(selection)) {
        const f = (await call(doc, "GetField", { qFieldName: field, qStateName: state })).qReturn.qHandle;
        const number = Number(value);
        const v = Number.isNaN(number) ? { qText: value } : { qText: value, qIsNumeric: true, qNumber: number };
        await call(f, "SelectValues", { qFieldValues: [v], qToggleMode: false, qSoftLock: false });
      }
    }
    const out = {};
    for (const state of Object.keys(sides)) {
      const cube = (await call(doc, "CreateSessionObject", { qProp: {
        qInfo: { qType: "valtera-verify" },
        qHyperCubeDef: { qStateName: state, qMeasures: measures.map((m) => ({ qLibraryId: m, qDef: {} })),
                         qInitialDataFetch: [{ qLeft: 0, qTop: 0, qWidth: measures.length, qHeight: 1 }] } } })).qReturn.qHandle;
      const layout = (await call(cube, "GetLayout", {})).qLayout;
      out[state] = layout.qHyperCube.qDataPages[0].qMatrix[0].map((c) => ({ qText: c.qText, qNum: c.qNum }));
    }
    return out;
  } finally {
    ws.close();
  }
}
