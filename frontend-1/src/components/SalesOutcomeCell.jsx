export default function SalesOutcomeCell({ items = [] }) {
  if (!items?.length) return <span style={{ color: 'var(--muted)' }}>—</span>
  return (
    <div>
      {items.map((it, i) => (
        <div key={i} style={{ fontSize: '0.75rem', lineHeight: 1.6 }}>
          {it.product_name} × {it.qty}
          {it.eur_value > 0 && <span style={{ color: 'var(--muted)' }}> (€{it.eur_value.toFixed(2)})</span>}
        </div>
      ))}
    </div>
  )
}
