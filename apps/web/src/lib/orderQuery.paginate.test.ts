import { describe, expect, it } from 'vitest';
import { pageWindow, paginate } from './orderQuery';
import type { PageToken } from './orderQuery';

const items = Array.from({ length: 25 }, (_, i) => i + 1);

describe('paginate', () => {
  it.each([
    [1, 10, 1, 1, 10, 3],
    [2, 10, 2, 11, 20, 3],
    [3, 10, 3, 21, 25, 3],
    [4, 10, 3, 21, 25, 3],
    [0, 10, 1, 1, 10, 3],
    [-2, 10, 1, 1, 10, 3],
    [2.7, 10, 2, 11, 20, 3],
    [NaN, 10, 1, 1, 10, 3],
    [1, 25, 1, 1, 25, 1],
    [5, 5, 5, 21, 25, 5],
  ])('page %d size %d -> page %d items %d..%d of %d pages', (page, size, expectedPage, start, end, totalPages) => {
    const result = paginate(items, page, size);
    expect(result.page).toBe(expectedPage);
    expect(result.start).toBe(start);
    expect(result.end).toBe(end);
    expect(result.totalPages).toBe(totalPages);
    expect(result.totalItems).toBe(25);
    expect(result.items[0]).toBe(start);
    expect(result.items).toHaveLength(end - start + 1);
  });

  it('reports one empty page for an empty list', () => {
    expect(paginate([], 3, 10)).toEqual({ items: [], page: 1, pageSize: 10, totalItems: 0, totalPages: 1, start: 0, end: 0 });
  });

  it.each([0, -1, 1.5])('rejects page size %d', (size) => {
    expect(() => paginate(items, 1, size)).toThrow(RangeError);
  });
});

describe('pageWindow', () => {
  const E = 'ellipsis' as const;
  it.each<[number, number, number, PageToken[]]>([
    [1, 0, 1, []],
    [1, 1, 1, [1]],
    [1, 2, 1, [1, 2]],
    [1, 5, 1, [1, 2, E, 5]],
    [3, 5, 1, [1, 2, 3, 4, 5]],
    [3, 10, 1, [1, 2, 3, 4, E, 10]],
    [4, 10, 1, [1, 2, 3, 4, 5, E, 10]],
    [5, 10, 1, [1, E, 4, 5, 6, E, 10]],
    [10, 10, 1, [1, E, 9, 10]],
    [2, 10, 2, [1, 2, 3, 4, E, 10]],
    [50, 100, 0, [1, E, 50, E, 100]],
  ])('current %d of %d (siblings %d)', (current, total, siblings, expected) => {
    expect(pageWindow(current, total, siblings)).toEqual(expected);
  });
});
