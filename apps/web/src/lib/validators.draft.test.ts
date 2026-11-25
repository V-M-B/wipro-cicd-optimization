import { describe, expect, it } from 'vitest';
import { MAX_ORDER_LINES, hasErrors, validateOrderDraft, validateQuantity } from './validators';
import type { OrderDraft } from './validators';

describe('validateQuantity', () => {
  it.each([
    [1, null],
    [999, null],
    ['5', null],
    [' 12 ', null],
    [0, 'Quantity must be at least 1'],
    ['-3', 'Quantity must be at least 1'],
    [1000, 'Quantity must be at most 999'],
    [1.5, 'Quantity must be a whole number'],
    ['2.5', 'Quantity must be a whole number'],
    ['', 'Quantity is required'],
    ['   ', 'Quantity is required'],
    ['abc', 'Quantity must be a number'],
    ['1e3', 'Quantity must be a number'],
    [NaN, 'Quantity must be a number'],
    [null, 'Quantity must be a number'],
    [undefined, 'Quantity must be a number'],
  ])('validateQuantity(%j) -> %j', (value, expected) => {
    expect(validateQuantity(value)).toBe(expected);
  });
});

const valid: OrderDraft = {
  customerId: 'C-0001',
  lines: [
    { sku: 'ELE-1001', quantity: 2 },
    { sku: 'GRO-2001', quantity: '3' },
  ],
  couponCode: 'SAVE10',
};

describe('validateOrderDraft', () => {
  it('accepts a valid draft', () => {
    const errors = validateOrderDraft(valid);
    expect(errors).toEqual({ lines: {} });
    expect(hasErrors(errors)).toBe(false);
  });

  it.each([
    ['', 'Select a customer'],
    ['   ', 'Select a customer'],
    ['X', 'Invalid customer id'],
  ])('customer %j -> %s', (customerId, message) => {
    expect(validateOrderDraft({ ...valid, customerId }).customerId).toBe(message);
  });

  it('ignores whitespace around the customer id', () => {
    expect(validateOrderDraft({ ...valid, customerId: ' C-0001 ' }).customerId).toBeUndefined();
  });

  it('requires at least one line', () => {
    expect(validateOrderDraft({ ...valid, lines: [] }).form).toBe('Add at least one line');
  });

  it('caps the number of lines', () => {
    const lines = Array.from({ length: MAX_ORDER_LINES + 1 }, (_, i) => ({
      sku: `ELE-${String(1000 + i)}`,
      quantity: 1,
    }));
    expect(validateOrderDraft({ ...valid, lines }).form).toBe(`An order can have at most ${MAX_ORDER_LINES} lines`);
  });

  it.each([
    ['', 'Select a product'],
    ['bad', 'Invalid SKU'],
    ['ZZZ-9999', 'Unknown product'],
  ])('sku %j -> %s', (sku, message) => {
    const errors = validateOrderDraft({ ...valid, lines: [{ sku, quantity: 1 }] }, new Set(['ELE-1001']));
    expect(errors.lines[0]?.sku).toBe(message);
  });

  it('flags duplicate SKUs against the first occurrence', () => {
    const errors = validateOrderDraft({
      ...valid,
      lines: [
        { sku: 'ELE-1001', quantity: 1 },
        { sku: 'GRO-2001', quantity: 1 },
        { sku: 'ELE-1001', quantity: 4 },
      ],
    });
    expect(errors.lines).toEqual({ 2: { sku: 'Duplicate of line 1' } });
  });

  it('trims SKUs before validating and de-duplicating them', () => {
    const errors = validateOrderDraft(
      {
        ...valid,
        lines: [
          { sku: ' ELE-1001', quantity: 1 },
          { sku: 'ELE-1001 ', quantity: 2 },
        ],
      },
      new Set(['ELE-1001']),
    );
    expect(errors.lines).toEqual({ 1: { sku: 'Duplicate of line 1' } });
  });

  it('reports quantity errors per line', () => {
    const errors = validateOrderDraft({ ...valid, lines: [{ sku: 'ELE-1001', quantity: '0' }] });
    expect(errors.lines[0]).toEqual({ quantity: 'Quantity must be at least 1' });
    expect(hasErrors(errors)).toBe(true);
  });

  it.each([
    ['ab', true],
    ['SAVE-10', true],
    ['', false],
    [' save10 ', false],
  ])('coupon %j invalid=%s', (couponCode, invalid) => {
    expect(validateOrderDraft({ ...valid, couponCode }).couponCode !== undefined).toBe(invalid);
  });
});
