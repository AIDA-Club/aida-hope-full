/** Python str.format() subset used by i18n/*.json: {name} and {name:.Nf}. */
export type Values = Record<string, string | number>;

const FIELD = /\{([a-z_]+)(?::\.(\d)f)?\}/gi;

export function formatValue(value: string | number, digits?: string): string {
  if (digits !== undefined && typeof value === "number") {
    // Python rounds half to even for floats; toFixed is close enough for display, but keep
    // the exact representation Python would produce for the common ".0f" percent case.
    return roundHalfEven(value, Number(digits));
  }
  return String(value);
}

export function roundHalfEven(value: number, digits: number): string {
  const factor = 10 ** digits;
  const scaled = value * factor;
  const floor = Math.floor(scaled);
  const diff = scaled - floor;
  let rounded: number;
  if (Math.abs(diff - 0.5) < 1e-9) rounded = floor % 2 === 0 ? floor : floor + 1;
  else rounded = Math.round(scaled);
  return (rounded / factor).toFixed(digits);
}

export function format(template: string, values: Values = {}): string {
  return template.replace(FIELD, (match, name: string, digits?: string) =>
    name in values ? formatValue(values[name], digits) : match);
}

/** Split a template around its fields, so a caller can style a value (e.g. bold the answer). */
export function splitTemplate(template: string): Array<{ text: string } | { field: string; digits?: string }> {
  const parts: Array<{ text: string } | { field: string; digits?: string }> = [];
  let last = 0;
  for (const match of template.matchAll(FIELD)) {
    if (match.index! > last) parts.push({ text: template.slice(last, match.index) });
    parts.push({ field: match[1], digits: match[2] });
    last = match.index! + match[0].length;
  }
  if (last < template.length) parts.push({ text: template.slice(last) });
  return parts;
}
