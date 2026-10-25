/**
 * Money helpers. All monetary values in the app are plain numbers in major units (e.g. dollars)
 * and are rounded to 2 decimal places with banker's rounding (round half to even), which is the
 * rounding mode used by the orders service.
 */

const HALF_EPSILON = 1e-9;

/** Round half to even ("banker's rounding") to `decimals` places. */
export function roundHalfEven(value: number, decimals = 2): number {
  if (!Number.isFinite(value)) {
    throw new RangeError(`Cannot round a non-finite value: ${value}`);
  }
  if (!Number.isInteger(decimals) || decimals < 0 || decimals > 10) {
    throw new RangeError(`Unsupported number of decimals: ${decimals}`);
  }
  const factor = 10 ** decimals;
  // toPrecision(15) removes binary artefacts such as 1.005 * 100 === 100.49999999999999.
  const scaled = Number((value * factor).toPrecision(15));
  const floor = Math.floor(scaled);
  const diff = scaled - floor;
  let rounded: number;
  if (Math.abs(diff - 0.5) < HALF_EPSILON) {
    rounded = floor % 2 === 0 ? floor : floor + 1;
  } else {
    rounded = Math.round(scaled);
  }
  // Adding 0 normalises -0 to 0.
  return rounded / factor + 0;
}

/** Convert an amount to integer cents (after banker's rounding). */
export function toCents(amount: number): number {
  return Math.round(roundHalfEven(amount, 2) * 100);
}

/** Convert integer cents back to an amount in major units. */
export function fromCents(cents: number): number {
  if (!Number.isInteger(cents)) {
    throw new RangeError(`Cents must be an integer: ${cents}`);
  }
  return cents / 100 + 0;
}

/** Sum monetary amounts exactly (in cents) and return the rounded total. */
export function sumMoney(amounts: readonly number[]): number {
  return fromCents(amounts.reduce((acc, amount) => acc + toCents(amount), 0));
}

/** Multiply an amount by a rate and round the result. */
export function applyRate(amount: number, rate: number): number {
  return roundHalfEven(amount * rate, 2);
}

/** Split an amount into `parts` near-equal shares whose sum equals the amount exactly. */
export function allocate(amount: number, parts: number): number[] {
  if (!Number.isInteger(parts) || parts < 1) {
    throw new RangeError(`parts must be a positive integer: ${parts}`);
  }
  const cents = toCents(amount);
  const base = Math.trunc(cents / parts);
  let remainder = cents - base * parts;
  const step = remainder >= 0 ? 1 : -1;
  return Array.from({ length: parts }, () => {
    let share = base;
    if (remainder !== 0) {
      share += step;
      remainder -= step;
    }
    return fromCents(share);
  });
}
