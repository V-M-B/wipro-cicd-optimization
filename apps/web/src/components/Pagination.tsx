import { pageWindow } from '../lib/orderQuery';

export interface PaginationProps {
  page: number;
  totalPages: number;
  onChange: (page: number) => void;
}

export function Pagination({ page, totalPages, onChange }: PaginationProps) {
  if (totalPages <= 1) return null;
  const tokens = pageWindow(page, totalPages);
  return (
    <nav aria-label="Pagination" className="pagination">
      <button type="button" onClick={() => onChange(page - 1)} disabled={page <= 1}>
        Previous
      </button>
      {tokens.map((token, i) =>
        token === 'ellipsis' ? (
          <span key={`e${i}`} className="ellipsis" aria-hidden="true">
            &hellip;
          </span>
        ) : (
          <button
            type="button"
            key={token}
            aria-label={`Page ${token}`}
            aria-current={token === page ? 'page' : undefined}
            className={token === page ? 'current' : undefined}
            onClick={() => onChange(token)}
          >
            {token}
          </button>
        ),
      )}
      <button type="button" onClick={() => onChange(page + 1)} disabled={page >= totalPages}>
        Next
      </button>
    </nav>
  );
}
