import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { createMockApi, renderWithProviders } from '../test/utils';
import { ProductCatalogPage } from './ProductCatalogPage';

async function renderCatalog(api = createMockApi()) {
  const result = renderWithProviders(<ProductCatalogPage />, { api });
  await screen.findByRole('table', { name: 'Products' });
  return result;
}

const skus = () => screen.getAllByTestId('product-row').map((row) => (row as HTMLTableRowElement).cells[0]?.textContent);

describe('ProductCatalogPage', () => {
  it('lists active products by default', async () => {
    await renderCatalog();
    expect(screen.getAllByTestId('product-row')).toHaveLength(11);
    expect(screen.getByText('11 products')).toBeInTheDocument();
  });

  it('searches and highlights matches', async () => {
    const { user } = await renderCatalog();
    await user.type(screen.getByRole('searchbox', { name: 'Search products' }), 'mouse');
    expect(skus()).toEqual(['ELE-1001']);
    expect(screen.getByText('Mouse', { selector: 'mark' })).toBeInTheDocument();
  });

  it('can include inactive products', async () => {
    const { user } = await renderCatalog();
    await user.type(screen.getByRole('searchbox', { name: 'Search products' }), 'mouse');
    await user.click(screen.getByRole('checkbox', { name: 'Show inactive' }));
    expect(skus()).toEqual(['ELE-1004', 'ELE-1001']);
    expect(screen.getAllByTestId('product-row')[0]).toHaveTextContent('Inactive');
  });

  it('filters by category', async () => {
    const { user } = await renderCatalog();
    await user.selectOptions(screen.getByLabelText('Category'), 'GROCERY');
    expect(skus()).toEqual(['GRO-2002', 'GRO-2001']);
  });

  it('sorts by price', async () => {
    const { user } = await renderCatalog();
    await user.selectOptions(screen.getByLabelText('Sort by'), 'price-desc');
    expect(skus()[0]).toBe('ELE-1003');
    await user.selectOptions(screen.getByLabelText('Sort by'), 'price-asc');
    expect(skus()[0]).toBe('GRO-2002');
  });

  it('shows an empty state', async () => {
    const { user } = await renderCatalog();
    await user.type(screen.getByRole('searchbox', { name: 'Search products' }), 'submarine');
    expect(screen.getByText('No products found.')).toBeInTheDocument();
    expect(screen.getByText('0 products')).toBeInTheDocument();
  });

  it('retries after a failed load', async () => {
    const api = createMockApi();
    api.listProducts.mockRejectedValueOnce(new Error('Catalog unavailable'));
    const { user } = renderWithProviders(<ProductCatalogPage />, { api });
    expect(await screen.findByRole('alert')).toHaveTextContent('Catalog unavailable');
    await user.click(screen.getByRole('button', { name: 'Retry' }));
    expect(await screen.findByRole('table', { name: 'Products' })).toBeInTheDocument();
  });
});
