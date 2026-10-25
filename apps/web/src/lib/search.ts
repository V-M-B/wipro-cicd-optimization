import type { Category, Product } from '../generated/schemas';

/** Lower-case, strip diacritics, collapse whitespace. */
export function normalizeText(value: string): string {
  return value
    .normalize('NFD')
    .replace(/\p{M}/gu, '')
    .toLowerCase()
    .replace(/\s+/g, ' ')
    .trim();
}

export function tokenize(query: string): string[] {
  const normalized = normalizeText(query);
  return normalized === '' ? [] : [...new Set(normalized.split(' '))];
}

export function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/** True when every query token occurs somewhere in the text. An empty query matches everything. */
export function matchesQuery(text: string, query: string): boolean {
  const haystack = normalizeText(text);
  return tokenize(query).every((token) => haystack.includes(token));
}

/**
 * Relevance of a product for a query (0 = no match). Exact SKU beats SKU prefix beats name
 * word-prefix beats substring anywhere.
 */
export function scoreProduct(product: Product, query: string): number {
  const tokens = tokenize(query);
  if (tokens.length === 0) return 1;
  const sku = product.sku.toLowerCase();
  const name = normalizeText(product.name);
  const words = name.split(' ');
  const category = product.category.toLowerCase();
  let score = 0;
  for (const token of tokens) {
    if (sku === token) score += 100;
    else if (sku.startsWith(token)) score += 50;
    else if (words.some((w) => w === token)) score += 20;
    else if (words.some((w) => w.startsWith(token))) score += 10;
    else if (name.includes(token) || sku.includes(token)) score += 5;
    else if (category === token) score += 3;
    else return 0;
  }
  return score;
}

export interface ProductSearchOptions {
  category?: Category | 'ALL';
  includeInactive?: boolean;
}

export function searchProducts(
  products: readonly Product[],
  query: string,
  options: ProductSearchOptions = {},
): Product[] {
  const { category = 'ALL', includeInactive = false } = options;
  return products
    .filter((p) => includeInactive || p.active)
    .filter((p) => category === 'ALL' || p.category === category)
    .map((p) => ({ p, score: scoreProduct(p, query) }))
    .filter(({ score }) => score > 0)
    .sort((a, b) => b.score - a.score || a.p.name.localeCompare(b.p.name, 'en') || a.p.sku.localeCompare(b.p.sku, 'en'))
    .map(({ p }) => p);
}

export interface HighlightSegment {
  text: string;
  match: boolean;
}

/**
 * Split `text` into segments marking case-insensitive occurrences of any query token.
 * Overlapping and adjacent matches are merged.
 */
export function highlight(text: string, query: string): HighlightSegment[] {
  if (text === '') return [];
  const tokens = query
    .toLowerCase()
    .split(/\s+/)
    .filter((t) => t !== '');
  if (tokens.length === 0) return [{ text, match: false }];
  const lower = text.toLowerCase();
  const ranges: Array<[number, number]> = [];
  for (const token of tokens) {
    let from = 0;
    for (;;) {
      const idx = lower.indexOf(token, from);
      if (idx === -1) break;
      ranges.push([idx, idx + token.length]);
      from = idx + 1;
    }
  }
  if (ranges.length === 0) return [{ text, match: false }];
  ranges.sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  const merged: Array<[number, number]> = [];
  for (const range of ranges) {
    const last = merged[merged.length - 1];
    if (last && range[0] <= last[1]) last[1] = Math.max(last[1], range[1]);
    else merged.push([range[0], range[1]]);
  }
  const segments: HighlightSegment[] = [];
  let cursor = 0;
  for (const [start, end] of merged) {
    if (start > cursor) segments.push({ text: text.slice(cursor, start), match: false });
    segments.push({ text: text.slice(start, end), match: true });
    cursor = end;
  }
  if (cursor < text.length) segments.push({ text: text.slice(cursor), match: false });
  return segments;
}

export type ProductSort = 'relevance' | 'name' | 'price-asc' | 'price-desc';

export function sortProducts(products: readonly Product[], sort: ProductSort): Product[] {
  const copy = [...products];
  switch (sort) {
    case 'relevance':
      return copy;
    case 'name':
      return copy.sort((a, b) => a.name.localeCompare(b.name, 'en'));
    case 'price-asc':
      return copy.sort((a, b) => a.unitPrice - b.unitPrice || a.name.localeCompare(b.name, 'en'));
    case 'price-desc':
      return copy.sort((a, b) => b.unitPrice - a.unitPrice || a.name.localeCompare(b.name, 'en'));
  }
}
