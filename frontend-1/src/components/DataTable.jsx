function fmtCell(key, val) {
  if (val === null || val === undefined) return '—'
  if (key === 'rank' && typeof val === 'number') {
    return <span className={`badge ${val === 1 ? 'j' : 'n'}`}>#{val}</span>
  }
  if (key === 'conversion_pct' && typeof val === 'number') {
    const cls = val >= 30 ? 'g' : val >= 15 ? 'w' : 'd'
    return <span className={`badge ${cls}`}>{val.toFixed(1)}%</span>
  }
  if (key === 'ctc_ratio' && typeof val === 'number') {
    const cls = val > 0.3 ? 'd' : val > 0.2 ? 'w' : 'g'
    return <span className={`badge ${cls}`}>{(val * 100).toFixed(1)}%</span>
  }
  if (key === 'closing_stock' && typeof val === 'number') {
    const cls = val < 50 ? 'd' : val < 150 ? 'w' : 'n'
    return <span className={`badge ${cls}`}>{Math.round(val).toLocaleString()}</span>
  }
  if (key === 'pct_listed' && typeof val === 'number') return `${(val * 100).toFixed(0)}%`
  if (key === 'coverage_pct' && typeof val === 'number') return `${val.toFixed(0)}%`
  if (key === 'achievement_pct' && typeof val === 'number') {
    const cls = val >= 100 ? 'g' : val >= 70 ? 'w' : 'd'
    return <span className={`badge ${cls}`}>{val.toFixed(1)}%</span>
  }
  if (typeof val === 'number') {
    if (val === 0) return '0'
    return val % 1 === 0 ? val.toLocaleString() : val.toLocaleString(undefined, { maximumFractionDigits: 2 })
  }
  if (typeof val === 'boolean') {
    return val ? <span className="badge g">✓</span> : <span className="badge d">✗</span>
  }
  return String(val)
}

export default function DataTable({ title, sub, badge, borderColor, columns = [], rows = [], totalRow }) {
  return (
    <div className="tbl-card" style={borderColor ? { borderTop: `2px solid ${borderColor}` } : {}}>
      <div className="tbl-header">
        <div>
          <span className="tbl-title">{title}</span>
          {sub && <div style={{ fontSize: '0.72rem', color: 'var(--muted)', marginTop: 2 }}>{sub}</div>}
        </div>
        {badge && <span className="badge n">{badge}</span>}
      </div>
      <div className="tbl-scroll">
<table>
        <thead>
          <tr>{columns.map(c => <th key={c.key} style={c.align ? { textAlign: c.align } : undefined}>{c.label}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i}>{columns.map(c => (
              <td key={c.key} style={c.align ? { textAlign: c.align } : undefined}>
                {c.render ? c.render(row) : fmtCell(c.key, row[c.key])}
              </td>
            ))}</tr>
          ))}
          {totalRow && (
            <tr className="tbl-footer-row">
              {columns.map(c => (
                <td key={c.key} style={c.align ? { textAlign: c.align } : undefined}>
                  {c.render ? c.render(totalRow) : fmtCell(c.key, totalRow[c.key])}
                </td>
              ))}
            </tr>
          )}
        </tbody>
      </table>
</div>
    </div>
  )
}
