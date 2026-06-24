export default function ChartCard({ title, sub, height = 'h300', children, monthColor }) {
  const isPx = typeof height === 'string' && /^\d/.test(height)
  return (
    <div className="chart-card" style={{ borderTop: `2px solid ${monthColor || 'rgba(124,58,237,0.45)'}` }}>
      <div className="chart-title">{title}</div>
      {sub && <div className="chart-sub">{sub}</div>}
      <div className={isPx ? '' : height} style={isPx ? { height } : undefined}>{children}</div>
    </div>
  )
}
