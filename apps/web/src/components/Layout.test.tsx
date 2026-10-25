import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { Layout } from './Layout';

function renderAt(path: string) {
  render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route element={<Layout />}>
          <Route path="*" element={<p>page content</p>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

describe('Layout', () => {
  it('renders the main navigation and the routed page', () => {
    renderAt('/');
    const nav = screen.getByRole('navigation', { name: 'Main' });
    expect(within(nav).getAllByRole('link').map((a) => a.textContent)).toEqual([
      'Dashboard',
      'Orders',
      'New order',
      'Products',
      'Customers',
    ]);
    expect(screen.getByRole('main')).toHaveTextContent('page content');
  });

  it.each([
    ['/', 'Dashboard'],
    ['/orders', 'Orders'],
    ['/orders/new', 'New order'],
    ['/products', 'Products'],
  ])('marks the active link at %s', (path, label) => {
    renderAt(path);
    expect(screen.getByRole('link', { name: label })).toHaveClass('active');
    expect(screen.getAllByRole('link').filter((a) => a.classList.contains('active'))).toHaveLength(1);
  });

  it('navigates when a link is clicked', async () => {
    renderAt('/');
    await userEvent.setup().click(screen.getByRole('link', { name: 'Customers' }));
    expect(screen.getByRole('link', { name: 'Customers' })).toHaveAttribute('aria-current', 'page');
  });
});
