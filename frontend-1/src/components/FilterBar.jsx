import { useFilter } from '../context/FilterContext.jsx'
import { MONTH_CONFIG } from '../utils/monthConfig.js'

export default function FilterBar({ availableMonths = [] }) {
  const { isFiltered, toggleMonth, clearFilter, isMonthSelected } = useFilter()
  return (
    <div className="filter-bar">
      <span style={{ fontSize: '0.73rem', color: 'var(--muted)', fontWeight: 600 }}>FILTER</span>
      {availableMonths.map(m => {
        const cfg = MONTH_CONFIG[m] || {}
        const selected = isMonthSelected(m)
        return (
          <button key={m} onClick={() => toggleMonth(m)} className="filter-chip"
            style={!selected ? { opacity: 0.35, background: 'transparent' } : { borderColor: `${cfg.color}55`, color: cfg.color, background: `${cfg.color}14` }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: cfg.color || 'var(--accent)', display: 'inline-block' }} />
            {cfg.short || m.toUpperCase()}
          </button>
        )
      })}
      {isFiltered && (
        <button onClick={clearFilter} className="filter-chip" style={{ color: 'var(--muted)' }}>
          Clear
        </button>
      )}
    </div>
  )
}
