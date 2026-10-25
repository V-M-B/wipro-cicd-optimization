import { describe, expect, it } from 'vitest';
import { products } from '../test/fixtures';
import { escapeRegExp, matchesQuery, normalizeText, scoreProduct, searchProducts, sortProducts, tokenize } from './search';
import type { ProductSort } from './search';

const product = (sku: string) => {
  const found = products.find((p) => p.sku === sku);
  if (!found) throw new Error(sku);
  return found;
};

describe('text normalisation', () => {
  it.each([
    ['  Crème   Brûlée ', 'creme brulee'],
    ['ÅNGSTRÖM', 'angstrom'],
    ['tab\tand\nnewline', 'tab and newline'],
    ['', ''],
  ])('normalizeText(%j) = %j', (input, expected) => {
    expect(normalizeText(input)).toBe(expected);
  });

  it('tokenizes and de-duplicates', () => {
    expect(tokenize('Mouse  mouse WIRELESS')).toEqual(['mouse', 'wireless']);
    expect(tokenize('   ')).toEqual([]);
  });

  it('escapes regular expression metacharacters', () => {
    expect(escapeRegExp('a.b*c(d)[e]')).toBe('a\\.b\\*c\\(d\\)\\[e\\]');
    expect(new RegExp(escapeRegExp('1+1=2?')).test('is 1+1=2?')).toBe(true);
  });

  it.each([
    ['Wireless Mouse', 'mouse', true],
    ['Wireless Mouse', 'wire mou', true],
    ['Wireless Mouse', 'mouse pad', false],
    ['Café Latte', 'cafe', true],
    ['anything', '', true],
  ])('matchesQuery(%j, %j) = %s', (text, query, expected) => {
    expect(matchesQuery(text, query)).toBe(expected);
  });
});

describe('scoreProduct', () => {
  it.each([
    ['ELE-1001', 'ele-1001', 100],
    ['ELE-1001', 'ele', 50],
    ['ELE-1001', 'mouse', 20],
    ['ELE-1001', 'mou', 10],
    ['ELE-1001', 'ouse', 5],
    ['ELE-1001', 'electronics', 3],
    ['ELE-1001', 'wireless mouse', 40],
    ['ELE-1001', 'mouse keyboard', 0],
    ['ELE-1001', '', 1],
  ])('%s for %j scores %d', (sku, query, expected) => {
    expect(scoreProduct(product(sku), query)).toBe(expected);
  });
});

describe('searchProducts', () => {
  const names = (list: typeof products) => list.map((p) => p.name);

  it('hides inactive products unless asked', () => {
    expect(names(searchProducts(products, 'mouse'))).toEqual(['Wireless Mouse']);
    expect(names(searchProducts(products, 'mouse', { includeInactive: true }))).toEqual([
      'Legacy Wired Mouse',
      'Wireless Mouse',
    ]);
  });

  it('ranks an exact SKU first', () => {
    expect(searchProducts(products, 'ELE-1002')[0]?.sku).toBe('ELE-1002');
  });

  it('filters by category', () => {
    expect(names(searchProducts(products, '', { category: 'TOYS' }))).toEqual(['Puzzle Cube', 'Wooden Train Set']);
  });

  it('returns every active product sorted by name for an empty query', () => {
    const result = searchProducts(products, '');
    expect(result).toHaveLength(11);
    expect(names(result)).toEqual([...names(result)].sort((a, b) => a.localeCompare(b, 'en')));
  });

  it('returns nothing when no product matches', () => {
    expect(searchProducts(products, 'submarine')).toEqual([]);
  });
});

describe('sortProducts', () => {
  const sample = [product('TOY-5001'), product('ELE-1003'), product('GRO-2002'), product('HOM-4002')];
  it.each<[ProductSort, string[]]>([
    ['relevance', ['TOY-5001', 'ELE-1003', 'GRO-2002', 'HOM-4002']],
    ['name', ['HOM-4002', 'GRO-2002', 'ELE-1003', 'TOY-5001']],
    ['price-asc', ['GRO-2002', 'TOY-5001', 'HOM-4002', 'ELE-1003']],
    ['price-desc', ['ELE-1003', 'HOM-4002', 'TOY-5001', 'GRO-2002']],
  ])('%s', (sort, expected) => {
    expect(sortProducts(sample, sort).map((p) => p.sku)).toEqual(expected);
  });
});
