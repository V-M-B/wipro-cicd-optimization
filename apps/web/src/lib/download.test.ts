import { afterEach, describe, expect, it, vi } from 'vitest';
import { downloadText, exportFilename } from './download';

describe('exportFilename', () => {
  it.each([
    ['orders', new Date('2024-03-05T23:59:00Z'), undefined, 'orders-2024-03-05.csv'],
    ['customers', new Date('2024-12-31T00:00:00Z'), 'json', 'customers-2024-12-31.json'],
  ])('%s', (prefix, date, ext, expected) => {
    expect(exportFilename(prefix, date, ext)).toBe(expected);
  });
});

describe('downloadText', () => {
  const originalCreate = URL.createObjectURL;
  const originalRevoke = URL.revokeObjectURL;

  afterEach(() => {
    URL.createObjectURL = originalCreate;
    URL.revokeObjectURL = originalRevoke;
  });

  it('clicks a temporary link pointing at a blob URL and cleans up', () => {
    let blob: Blob | undefined;
    URL.createObjectURL = vi.fn((b: Blob | MediaSource) => {
      blob = b as Blob;
      return 'blob:mock-1';
    });
    URL.revokeObjectURL = vi.fn();
    const clicked: HTMLAnchorElement[] = [];
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (this: HTMLAnchorElement) {
      clicked.push(this);
    });

    downloadText('orders.csv', 'a,b\r\n');

    expect(click).toHaveBeenCalledTimes(1);
    expect(clicked[0]?.download).toBe('orders.csv');
    expect(clicked[0]?.href).toBe('blob:mock-1');
    expect(document.querySelector('a[download]')).toBeNull();
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:mock-1');
    expect(blob?.type).toBe('text/csv;charset=utf-8');
    expect(blob?.size).toBe('a,b\r\n'.length);
  });
});
