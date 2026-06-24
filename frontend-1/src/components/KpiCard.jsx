const ICONS = [
  { match: /sales|revenue/i, icon: '◆', color: '#7c3aed' },
  { match: /target|achievement|annual/i, icon: '◎', color: '#14b8a6' },
  { match: /growth|mom/i, icon: '↗', color: '#22c55e' },
  { match: /visit/i, icon: '◇', color: '#ec4899' },
  { match: /dr|converted|conversion/i, icon: '✓', color: '#f59e0b' },
  { match: /product/i, icon: '▣', color: '#06b6d4' },
  { match: /unit/i, icon: '▢', color: '#a78bfa' },
  { match: /call/i, icon: '☎', color: '#7c3aed' },
  { match: /order/i, icon: '◈', color: '#14b8a6' },
  { match: /ctc|cost/i, icon: '€', color: '#f43f5e' },
  { match: /mr|active/i, icon: '◍', color: '#60a5fa' },
  { match: /budget|spent|received|balance/i, icon: '◐', color: '#f59e0b' },
  { match: /planned|executed|unplanned|rate/i, icon: '▥', color: '#7c3aed' },
  { match: /roi/i, icon: '↑', color: '#22c55e' },
]

function iconFor(label = '') {
  return ICONS.find(i => i.match.test(label)) || { icon: '●', color: '#7c3aed' }
}

export default function KpiCard({ label, value, sub, change, changeDir, monthColor }) {
  const { icon, color } = iconFor(label || '')
  const dot = monthColor || color
  return (
    <div className="kpi-card" style={{ '--kpi-accent': dot }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <div className="kpi-label">{label}</div>
        <span style={{
          width: 26, height: 26, borderRadius: 8, flexShrink: 0,
          background: `${dot}1c`, color: dot,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: '0.85rem', fontWeight: 700,
        }}>{icon}</span>
      </div>
      <div className="kpi-value">{value ?? '—'}</div>
      {sub && <div className="kpi-sub">{sub}</div>}
      {change !== undefined && change !== null && (
        <div className={`kpi-change ${changeDir || ''}`}>{changeDir === 'up' ? '▲' : changeDir === 'dn' ? '▼' : ''} {change}</div>
      )}
    </div>
  )
}
