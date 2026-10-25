import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { Pagination } from './Pagination';

describe('Pagination', () => {
  it('renders nothing for a single page', () => {
    const { container } = render(<Pagination page={1} totalPages={1} onChange={vi.fn()} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('renders page buttons with an ellipsis for gaps', () => {
    render(<Pagination page={5} totalPages={10} onChange={vi.fn()} />);
    const nav = screen.getByRole('navigation', { name: 'Pagination' });
    expect(nav).toHaveTextContent('Previous1…456…10Next');
    expect(screen.getByRole('button', { name: 'Page 5' })).toHaveAttribute('aria-current', 'page');
    expect(screen.getByRole('button', { name: 'Page 4' })).not.toHaveAttribute('aria-current');
  });

  it('disables Previous on the first page and Next on the last', () => {
    const { rerender } = render(<Pagination page={1} totalPages={3} onChange={vi.fn()} />);
    expect(screen.getByRole('button', { name: 'Previous' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Next' })).toBeEnabled();
    rerender(<Pagination page={3} totalPages={3} onChange={vi.fn()} />);
    expect(screen.getByRole('button', { name: 'Next' })).toBeDisabled();
  });

  it('reports the requested page', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<Pagination page={2} totalPages={3} onChange={onChange} />);
    await user.click(screen.getByRole('button', { name: 'Page 3' }));
    await user.click(screen.getByRole('button', { name: 'Previous' }));
    await user.click(screen.getByRole('button', { name: 'Next' }));
    expect(onChange.mock.calls).toEqual([[3], [1], [3]]);
  });
});
