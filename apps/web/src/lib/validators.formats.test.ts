import { describe, expect, it } from 'vitest';
import { isValidCouponFormat, isValidCustomerId, isValidEmail, isValidOrderId, isValidSku } from './validators';

describe('isValidSku', () => {
  it.each(['ELE-1001', 'APP-3001-XL', 'TOY-0000', 'HOM-9999-A1'])('accepts %s', (sku) => {
    expect(isValidSku(sku)).toBe(true);
  });

  it.each([
    'ele-1001',
    'EL-1001',
    'ELEC-1001',
    'ELE1001',
    'ELE-101',
    'ELE-1001-',
    'ELE-1001-X',
    'ELE-1001-XXX',
    'ELE-1001 ',
    '',
  ])('rejects %j', (sku) => {
    expect(isValidSku(sku)).toBe(false);
  });
});

describe('ids', () => {
  it.each([
    ['C-0001', true],
    ['C-123', false],
    ['c-0001', false],
  ])('customer id %s -> %s', (id, expected) => {
    expect(isValidCustomerId(id)).toBe(expected);
  });

  it.each([
    ['O-10001', true],
    ['O-1001', false],
  ])('order id %s -> %s', (id, expected) => {
    expect(isValidOrderId(id)).toBe(expected);
  });
});

describe('isValidEmail', () => {
  it.each([
    'a@b.co',
    'first.last@example.com',
    'user+tag@sub.example.org',
    'UPPER@EXAMPLE.COM',
  ])('accepts %s', (email) => {
    expect(isValidEmail(email)).toBe(true);
  });

  it.each([
    '',
    'plain',
    'user@example',
    'user@.com',
    'user@example..com',
    '.user@example.com',
    'user.@example.com',
    'us..er@example.com',
    'user@-example.com',
    'user@example.c',
    `${'a'.repeat(65)}@example.com`,
    `user@${'d'.repeat(250)}.com`,
  ])('rejects %j', (email) => {
    expect(isValidEmail(email)).toBe(false);
  });
});

describe('isValidCouponFormat', () => {
  it.each([
    ['SAVE10', true],
    [' save10 ', true],
    ['ABC', false],
    ['ABCDEFGHIJKLM', false],
    ['SAVE-10', false],
  ])('%j -> %s', (code, expected) => {
    expect(isValidCouponFormat(code)).toBe(expected);
  });
});
