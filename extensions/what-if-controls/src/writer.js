// Writes one What-If variable, latest value wins: while one write is under way, only the newest value waits for it.
// `onIdle` runs once no write is left, so the sliders can show the App's values again; `onError(error)` runs for a
// write the App refused, whose value the App therefore does not hold.
export function writer(app, name, { onIdle, onError }) {
  let variable = null;
  let busy = false;
  let next = null;
  const send = (value) => {
    if (busy) {
      next = value;
      return;
    }
    busy = true;
    variable = variable || app.getVariableByName(name);
    variable
      .then((v) => v.setNumValue(value))
      .catch((error) => {
        variable = null; // look the variable up again on the next write
        onError(error);
      })
      .then(() => {
        busy = false;
        if (next !== null) {
          const n = next;
          next = null;
          send(n);
        } else onIdle();
      });
  };
  send.busy = () => busy;
  return send;
}
