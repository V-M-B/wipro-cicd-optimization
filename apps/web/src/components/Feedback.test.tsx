import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { EmptyState, ErrorBanner, Loading } from './Feedback';
import { HighlightedText } from './HighlightedText';

describe('feedback components', () => {
  it('Loading announces a status', () => {
    render(<Loading label="Loading orders…" />);
    expect(screen.getByRole('status')).toHaveTextContent('Loading orders…');
  });

  it('ErrorBanner renders an alert with a retry action', async () => {
    const onRetry = vi.fn();
    render(<ErrorBanner message="Service down" onRetry={onRetry} />);
    expect(screen.getByRole('alert')).toHaveTextContent('Service down');
    await userEvent.setup().click(screen.getByRole('button', { name: 'Retry' }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it('ErrorBanner omits the retry button without a handler', () => {
    render(<ErrorBanner message="Nope" />);
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  it('EmptyState shows its title and children', () => {
    render(
      <EmptyState title="Nothing here">
        <a href="/x">Create one</a>
      </EmptyState>,
    );
    expect(screen.getByText('Nothing here')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Create one' })).toBeInTheDocument();
  });
});

describe('HighlightedText', () => {
  it('wraps matches in <mark>', () => {
    const { container } = render(<HighlightedText text="Wireless Mouse" query="mouse" />);
    expect([...container.querySelectorAll('mark')].map((m) => m.textContent)).toEqual(['Mouse']);
    expect(container).toHaveTextContent('Wireless Mouse');
  });

  it('renders plain text when nothing matches', () => {
    const { container } = render(<HighlightedText text="Desk Lamp" query="mug" />);
    expect(container.querySelector('mark')).toBeNull();
  });
});
