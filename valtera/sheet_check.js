// Runs inside a signed-in browser tab showing one Sheet in analysis mode.
// Given the Sheet's cells [{id, kpi}] (`kpi`: the cell is a KPI or a layout container holding one), returns one
// result per cell: {id, status: "ok" | "not rendered" | "empty" | "error", text}.
// Signals were read from the Sense client on the tenant (sense-client 8.811.0):
// each cell is `.qv-gridcell[tid=<object id>]` with `data-render-state="1"` once drawn;
// a cell whose object does not exist stays at "0"; a chart that crashed draws nothing;
// a KPI whose expression fails shows "-" as its value; Qlik's own messages appear as text in the content.
// A layout container's children draw inside its cell, so their text is part of the container's.
(cells) => {
  const ERROR_TEXT = /error|invalid|incomplete visualization|not displayed|no data to display/i;
  return cells.map(({ id, kpi }) => {
    const cell = document.querySelector(`.qv-gridcell[tid="${CSS.escape(id)}"]`);
    if (!cell || cell.getAttribute("data-render-state") !== "1") {
      return { id, status: "not rendered", text: "" };
    }
    const content = cell.querySelector(".qv-object-content");
    const text = content ? content.innerText.trim() : "";
    const drawn = content && content.querySelector("svg, canvas, img");
    if (!text && !drawn) return { id, status: "empty", text };
    // A table shows a null cell as "-" too, so only a KPI's "-" on a line of its own is a failed value.
    const failedValue = text === "-" || (kpi && text.split("\n").some((line) => line.trim() === "-"));
    if (failedValue || ERROR_TEXT.test(text)) return { id, status: "error", text: text.slice(0, 200) };
    return { id, status: "ok", text: text.slice(0, 200) };
  });
}
