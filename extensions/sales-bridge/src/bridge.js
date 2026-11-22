// The Sales Bridge's content, apart from drawing: its bars and states from the hypercube row, and each bar's
// short label. Amounts come in the unit of the master measures the object uses, EUR bn ("€6.76 bn") or EUR m
// ("€6,760.4 m"); the unit is read from the YTD figure's text.

function num(cell) {
  return cell && typeof cell.qNum === 'number' && !Number.isNaN(cell.qNum) ? cell.qNum : null;
}

// In EUR m one decimal. In EUR bn two decimals, three when an effect would otherwise show as 0.00.
function decimalsFor(bars, unit) {
  if (unit === 'm') return 1;
  return bars.some((b) => !b.total && Math.abs(b.to - b.from) >= 0.0005 && Math.abs(b.to - b.from) < 0.005) ? 3 : 2;
}

// From the hypercube row [Prior Year, volume, price, mix, YTD, year]: { bars, decimals, unit }, or { state } when
// there is nothing to bridge: 'empty' when a figure is missing, 'no prior year' when there are no Prior Year
// Sales to start from (the whole of Sales would show as Volume).
export function bridge(row) {
  const [priorYear, volume, price, mix, ytd] = row.slice(0, 5).map(num);
  if (priorYear === null || ytd === null || [volume, price, mix].some((v) => v === null)) return { state: 'empty' };
  const year = num(row[5]);
  if (priorYear === 0) return { state: 'no prior year', year };
  const unit = / m$/.test(row[4].qText) ? 'm' : 'bn';
  const bars = [{ label: 'Prior Year', from: 0, to: priorYear, total: true, text: row[0].qText }];
  let level = priorYear;
  [['Volume', volume, row[1]], ['Price', price, row[2]], ['Mix', mix, row[3]]].forEach(([label, v, cell]) => {
    bars.push({ label, from: level, to: level + v, text: cell.qText });
    level += v;
  });
  bars.push({ label: year ? `${year} YTD` : 'YTD', from: 0, to: ytd, total: true, text: row[4].qText });
  return { bars, decimals: decimalsFor(bars, unit), unit };
}

// A number with `decimals` decimals and thousands separators: 5710.2 -> "5,710.2".
export function amount(value, decimals) {
  return value.toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

// A bar's short label and kind: 'total', or for an effect 'up' (▲, favourable), 'down' (▼) or 'flat' when it
// rounds to zero at the bridge's decimals (no arrow, "0.00" in EUR bn, "0.0" in EUR m).
export function label(bar, decimals) {
  if (bar.total) return { text: `€${amount(bar.to, decimals)}`, kind: 'total' };
  const change = bar.to - bar.from;
  const shown = amount(Math.abs(change), decimals);
  if (Number(shown.replace(/,/g, '')) === 0) return { text: decimals === 1 ? '0.0' : '0.00', kind: 'flat' };
  return change > 0 ? { text: `▲ +${shown}`, kind: 'up' } : { text: `▼ −${shown}`, kind: 'down' };
}
