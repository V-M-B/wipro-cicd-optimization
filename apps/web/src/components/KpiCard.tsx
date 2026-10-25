export interface KpiCardProps {
  label: string;
  value: string;
  hint?: string;
  tone?: 'neutral' | 'good' | 'warning';
}

export function KpiCard({ label, value, hint, tone = 'neutral' }: KpiCardProps) {
  const id = `kpi-${label.toLowerCase().replace(/[^a-z0-9]+/g, '-')}`;
  return (
    <section className={`kpi-card kpi-${tone}`} aria-labelledby={id}>
      <h3 id={id} className="kpi-label">
        {label}
      </h3>
      <p className="kpi-value">{value}</p>
      {hint && <p className="kpi-hint">{hint}</p>}
    </section>
  );
}
