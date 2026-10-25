import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import { ApiProvider } from './api/ApiProvider';
import { useApi } from './api/context';
import { App } from './App';
import { createMockApi } from './test/utils';

function renderApp(path: string) {
  const api = createMockApi();
  render(
    <ApiProvider api={api}>
      <MemoryRouter initialEntries={[path]}>
        <App />
      </MemoryRouter>
    </ApiProvider>,
  );
  return { api, user: userEvent.setup() };
}

describe('App routing', () => {
  it.each([
    ['/', 'Dashboard'],
    ['/orders', 'Orders'],
    ['/orders/new', 'New order'],
    ['/orders/O-10003', 'Order O-10003'],
    ['/products', 'Product catalog'],
    ['/customers', 'Customers'],
    ['/does/not/exist', 'Page not found'],
  ])('%s renders the %s page', async (path, heading) => {
    renderApp(path);
    expect(await screen.findByRole('heading', { level: 1, name: heading })).toBeInTheDocument();
  });

  it('navigates between pages from the main navigation', async () => {
    const { user } = renderApp('/');
    await screen.findByRole('heading', { level: 1, name: 'Dashboard' });
    await user.click(screen.getByRole('link', { name: 'Products' }));
    expect(await screen.findByRole('heading', { level: 1, name: 'Product catalog' })).toBeInTheDocument();
    await user.click(screen.getByRole('link', { name: 'Orders' }));
    expect(await screen.findByRole('heading', { level: 1, name: 'Orders' })).toBeInTheDocument();
  });

  it('opens an order from the list', async () => {
    const { user } = renderApp('/orders');
    await user.click(await screen.findByRole('link', { name: 'O-10034' }));
    expect(await screen.findByRole('heading', { level: 1, name: 'Order O-10034' })).toBeInTheDocument();
  });

  it('requires an ApiProvider', () => {
    vi.spyOn(console, 'error').mockImplementation(() => undefined);
    function Probe() {
      useApi();
      return null;
    }
    expect(() => render(<Probe />)).toThrow('useApi must be used inside <ApiProvider>');
  });
});
