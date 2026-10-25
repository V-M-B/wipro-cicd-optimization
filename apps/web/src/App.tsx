import { Route, Routes } from 'react-router-dom';
import { Layout } from './components/Layout';
import { CreateOrderPage } from './pages/CreateOrderPage';
import { CustomerListPage } from './pages/CustomerListPage';
import { DashboardPage } from './pages/DashboardPage';
import { NotFoundPage } from './pages/NotFoundPage';
import { OrderDetailPage } from './pages/OrderDetailPage';
import { OrderListPage } from './pages/OrderListPage';
import { ProductCatalogPage } from './pages/ProductCatalogPage';

export function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<DashboardPage />} />
        <Route path="orders" element={<OrderListPage />} />
        <Route path="orders/new" element={<CreateOrderPage />} />
        <Route path="orders/:orderId" element={<OrderDetailPage />} />
        <Route path="products" element={<ProductCatalogPage />} />
        <Route path="customers" element={<CustomerListPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
