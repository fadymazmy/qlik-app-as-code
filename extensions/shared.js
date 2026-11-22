// What every Custom Extension shares: escaping text for HTML, and the theme's colours and font as CSS custom
// properties. Each theme variable `@name` becomes `--name`; the value in theme/theme.json is the fallback, used
// only where the App's theme defines no value.
import { _variables as THEME_VARIABLES } from '../theme/theme.json';

export function esc(text) {
  return String(text == null ? '' : text).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);
}

export function themeStyle(theme) {
  const vars = Object.keys(THEME_VARIABLES).map(
    (k) => `--${k.slice(1)}: ${theme.getStyle('', '', `_variables.${k}`) || THEME_VARIABLES[k]}`
  );
  vars.push(`--font: ${theme.getStyle('', '', 'fontFamily') || 'sans-serif'}`);
  return vars.join('; ');
}

// For an extension that spans its whole card, up to the border: it takes the theme's object padding back.
export function fullCard(theme) {
  const [t, r = t, b = t, l = r] = (theme.getStyle('object', '', 'padding') || '0px').trim().split(/\s+/);
  return `margin: -${t} -${r} -${b} -${l}; height: calc(100% + ${t} + ${b})`;
}
