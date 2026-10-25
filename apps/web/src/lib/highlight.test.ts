import { describe, expect, it } from 'vitest';
import { highlight } from './search';

const render = (text: string, query: string) =>
  highlight(text, query)
    .map((s) => (s.match ? `[${s.text}]` : s.text))
    .join('');

describe('highlight', () => {
  it.each([
    ['Wireless Mouse', 'mouse', 'Wireless [Mouse]'],
    ['Wireless Mouse', '', 'Wireless Mouse'],
    ['Wireless Mouse', 'keyboard', 'Wireless Mouse'],
    ['Wireless Mouse', 'wire mouse', '[Wire]less [Mouse]'],
    ['banana', 'an', 'b[anan]a'],
    ['aaaa', 'aa', '[aaaa]'],
    ['abc', 'a b', '[ab]c'],
    ['USB-C Charger (fast)', '(fast)', 'USB-C Charger [(fast)]'],
    ['ELE-1001', 'ele-10', '[ELE-10]01'],
    ['Mug mug MUG', 'mug', '[Mug] [mug] [MUG]'],
  ])('highlight(%j, %j) renders %j', (text, query, expected) => {
    expect(render(text, query)).toBe(expected);
  });

  it('returns no segments for empty text', () => {
    expect(highlight('', 'x')).toEqual([]);
  });

  it('preserves the original text exactly', () => {
    const text = 'Noise Cancelling Headphones';
    expect(
      highlight(text, 'cell phone')
        .map((s) => s.text)
        .join(''),
    ).toBe(text);
  });

  it('marks segments with a boolean flag', () => {
    expect(highlight('Desk Lamp', 'lamp')).toEqual([
      { text: 'Desk ', match: false },
      { text: 'Lamp', match: true },
    ]);
  });
});
