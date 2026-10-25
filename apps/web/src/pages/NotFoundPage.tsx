import { Link, useLocation } from 'react-router-dom';

export function NotFoundPage() {
  const location = useLocation();
  return (
    <div className="page">
      <h1>Page not found</h1>
      <p>
        Nothing lives at <code>{location.pathname}</code>. <Link to="/">Go to the dashboard</Link>
      </p>
    </div>
  );
}
