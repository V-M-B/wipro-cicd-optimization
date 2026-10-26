/** Input validation shared by the create-order form and the API client. */

/** Three upper-case letters, a dash, four digits, optional two-character variant: `ELE-1001`, `APP-2001-XL`. */
export const SKU_PATTERN = /^[A-Z]{3}-\d{4}(?:-[A-Z0-9]{2})?$/;
export const CUSTOMER_ID_PATTERN = /^C-\d{4}$/;
export const ORDER_ID_PATTERN = /^O-\d{5}$/;
export const COUPON_FORMAT = /^[A-Z0-9]{4,12}$/;
const EMAIL_PATTERN = /^[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}$/;

export const MIN_LINE_QUANTITY = 1;
export const MAX_LINE_QUANTITY = 999;
export const MAX_ORDER_LINES = 20;

export function isValidSku(value: string): boolean {
  return SKU_PATTERN.test(value);
}

export function isValidCustomerId(value: string): boolean {
  return CUSTOMER_ID_PATTERN.test(value);
}

export function isValidOrderId(value: string): boolean {
  return ORDER_ID_PATTERN.test(value);
}

export function isValidEmail(value: string): boolean {
  if (value.length > 254) return false;
  if (!EMAIL_PATTERN.test(value)) return false;
  const [local = '', domain = ''] = value.split('@');
  if (local.length > 64) return false;
  if (local.startsWith('.') || local.endsWith('.') || local.includes('..')) return false;
  return domain.split('.').every((label) => label.length > 0 && !label.startsWith('-') && !label.endsWith('-'));
}

export function isValidCouponFormat(value: string): boolean {
  return COUPON_FORMAT.test(value.trim().toUpperCase());
}

/** Returns an error message, or null when the quantity is acceptable. */
export function validateQuantity(value: unknown): string | null {
  if (typeof value === 'string') {
    if (value.trim() === '') return 'Quantity is required';
    if (!/^-?\d+(\.\d+)?$/.test(value.trim())) return 'Quantity must be a number';
    return validateQuantity(Number(value));
  }
  if (typeof value !== 'number' || Number.isNaN(value)) return 'Quantity must be a number';
  if (!Number.isInteger(value)) return 'Quantity must be a whole number';
  if (value < MIN_LINE_QUANTITY) return `Quantity must be at least ${MIN_LINE_QUANTITY}`;
  if (value > MAX_LINE_QUANTITY) return `Quantity must be at most ${MAX_LINE_QUANTITY}`;
  return null;
}

export interface OrderDraftLine {
  sku: string;
  quantity: number | string;
}

export interface OrderDraft {
  customerId: string;
  lines: OrderDraftLine[];
  couponCode?: string;
}

export interface LineErrors {
  sku?: string;
  quantity?: string;
}

export interface DraftErrors {
  customerId?: string;
  couponCode?: string;
  form?: string;
  lines: Record<number, LineErrors>;
}

export function validateOrderDraft(draft: OrderDraft, knownSkus?: ReadonlySet<string>): DraftErrors {
  const errors: DraftErrors = { lines: {} };
  const customerId = draft.customerId.trim();
  if (customerId === '') {
    errors.customerId = 'Select a customer';
  } else if (!isValidCustomerId(customerId)) {
    errors.customerId = 'Invalid customer id';
  }

  if (draft.lines.length === 0) {
    errors.form = 'Add at least one line';
  } else if (draft.lines.length > MAX_ORDER_LINES) {
    errors.form = `An order can have at most ${MAX_ORDER_LINES} lines`;
  }

  const seen = new Map<string, number>();
  draft.lines.forEach((line, index) => {
    const lineErrors: LineErrors = {};
    // Pasted SKUs often carry stray whitespace; validate the value the API will actually receive.
    const sku = line.sku.trim();
    if (sku === '') {
      lineErrors.sku = 'Select a product';
    } else if (!isValidSku(sku)) {
      lineErrors.sku = 'Invalid SKU';
    } else if (knownSkus && !knownSkus.has(sku)) {
      lineErrors.sku = 'Unknown product';
    } else if (seen.has(sku)) {
      lineErrors.sku = `Duplicate of line ${(seen.get(sku) ?? 0) + 1}`;
    } else {
      seen.set(sku, index);
    }
    const quantityError = validateQuantity(line.quantity);
    if (quantityError) lineErrors.quantity = quantityError;
    if (lineErrors.sku || lineErrors.quantity) errors.lines[index] = lineErrors;
  });

  const coupon = draft.couponCode?.trim() ?? '';
  if (coupon !== '' && !isValidCouponFormat(coupon)) {
    errors.couponCode = 'Coupon codes are 4-12 letters or digits';
  }
  return errors;
}

export function hasErrors(errors: DraftErrors): boolean {
  return (
    errors.customerId !== undefined ||
    errors.couponCode !== undefined ||
    errors.form !== undefined ||
    Object.keys(errors.lines).length > 0
  );
}
