import { NavLink, Outlet } from 'react-router-dom';

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', end: true },
  { to: '/orders', label: 'Orders', end: true },
  { to: '/orders/new', label: 'New order', end: true },
  { to: '/products', label: 'Products', end: false },
  { to: '/customers', label: 'Customers', end: false },
];

export function Layout() {
  return (
    <div className="app">
      <header className="app-header">
        <span className="brand">RetailOps</span>
        <nav aria-label="Main">
          <ul className="nav-list">
            {NAV_ITEMS.map((item) => (
              <li key={item.to}>
                <NavLink to={item.to} end={item.end} className={({ isActive }) => (isActive ? 'active' : undefined)}>
                  {item.label}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
      </header>
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}
