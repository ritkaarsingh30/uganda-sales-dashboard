import { useState, useMemo } from 'react'
import { Bar } from 'react-chartjs-2'
import { baseOptions, PALETTE } from '../utils/chartConfig.js'
import ChartCard from './ChartCard.jsx'
import SectionLabel from './SectionLabel.jsx'

const TH = ({ children }) => (
  <th style={{ padding: '8px 12px', textAlign: 'left', color: 'var(--muted)', borderBottom: '1px solid var(--border)', fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600, background: '#f8fafc' }}>
    {children}
  </th>
)
const TD = ({ children, muted, mono }) => (
  <td style={{ padding: '7px 12px', borderBottom: '1px solid #f1f5f9', color: muted ? 'var(--muted)' : 'var(--text)', fontFamily: mono ? 'var(--font-mono)' : undefined, fontSize: '0.8rem' }}>
    {children}
  </td>
)

function FilterToggle({ value, onChange }) {
  return (
    <div style={{ display: 'flex', gap: 4 }}>
      {['byDay', 'mostVisited'].map(mode => (
        <button
          key={mode}
          onClick={e => { e.stopPropagation(); onChange(mode) }}
          style={{
            padding: '3px 10px', borderRadius: 12, border: '1px solid var(--border)',
            background: value === mode ? 'var(--accent)' : 'var(--card)',
            color: value === mode ? '#fff' : 'var(--muted)',
            fontSize: '0.72rem', cursor: 'pointer', fontWeight: value === mode ? 600 : 400,
            transition: 'all 0.15s',
          }}
        >
          {mode === 'byDay' ? 'By Day' : 'Most Visited'}
        </button>
      ))}
    </div>
  )
}

function ByDayView({ visits }) {
  const dates = useMemo(() => {
    const s = new Set(visits.map(v => v.date).filter(Boolean))
    return [...s].sort()
  }, [visits])

  const [selectedDate, setSelectedDate] = useState(dates[0] || '')
  const filtered = useMemo(
    () => visits.filter(v => v.date === selectedDate),
    [visits, selectedDate]
  )

  if (!dates.length) return <div style={{ padding: '12px 16px', color: 'var(--muted)', fontSize: '0.8rem' }}>No dated visits.</div>

  return (
    <div>
      <div style={{ padding: '10px 14px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: 10 }}>
        <span style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>Date</span>
        <select
          value={selectedDate}
          onChange={e => setSelectedDate(e.target.value)}
          onClick={e => e.stopPropagation()}
          style={{ padding: '4px 8px', borderRadius: 6, border: '1px solid var(--border)', fontSize: '0.78rem', color: 'var(--text)', background: 'var(--card)', cursor: 'pointer' }}
        >
          {dates.map(d => (
            <option key={d} value={d}>{d}</option>
          ))}
        </select>
        <span style={{ fontSize: '0.75rem', color: 'var(--muted)' }}>{filtered.length} doctor{filtered.length !== 1 ? 's' : ''} visited</span>
      </div>
      {filtered.length > 0 ? (
        <div className="tbl-scroll">
<table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr><TH>Doctor</TH><TH>Speciality</TH><TH>Hospital / Clinic</TH><TH>Status</TH></tr>
          </thead>
          <tbody>
            {filtered.map((v, i) => (
              <tr key={i} style={{ cursor: 'default' }}>
                <TD>{v.doctor || '—'}</TD>
                <TD muted>{v.speciality || '—'}</TD>
                <TD muted>{v.clinic || '—'}</TD>
                <TD><ListedBadge value={v.listed} /></TD>
              </tr>
            ))}
          </tbody>
        </table>
</div>
      ) : (
        <div style={{ padding: '12px 16px', color: 'var(--muted)', fontSize: '0.8rem' }}>No visits on this date.</div>
      )}
    </div>
  )
}

function ListedBadge({ value }) {
  if (!value) return <span style={{ color: 'var(--muted)', fontSize: '0.75rem' }}>—</span>
  const isListed = value.includes('LISTED') && !value.includes('NON') && !value.includes('UN')
  return (
    <span style={{
      display: 'inline-block', padding: '2px 8px', borderRadius: 10, fontSize: '0.7rem', fontWeight: 600,
      background: isListed ? '#dcfce7' : '#fee2e2',
      color: isListed ? '#15803d' : '#b91c1c',
    }}>
      {isListed ? 'Listed' : 'Unlisted'}
    </span>
  )
}

function MostVisitedView({ visits }) {
  const ranked = useMemo(() => {
    const map = {}
    visits.forEach(v => {
      const key = v.doctor || '—'
      if (!map[key]) map[key] = { doctor: key, speciality: v.speciality, clinic: v.clinic, listed: v.listed, count: 0, dates: [] }
      map[key].count++
      if (v.date && !map[key].dates.includes(v.date)) map[key].dates.push(v.date)
    })
    return Object.values(map).sort((a, b) => b.count - a.count)
  }, [visits])

  if (!ranked.length) return <div style={{ padding: '12px 16px', color: 'var(--muted)', fontSize: '0.8rem' }}>No visit data.</div>

  const max = ranked[0]?.count || 1

  return (
    <div className="tbl-scroll">
<table style={{ width: '100%', borderCollapse: 'collapse' }}>
      <thead>
        <tr><TH>Rank</TH><TH>Doctor</TH><TH>Speciality</TH><TH>Clinic</TH><TH>Status</TH><TH>Visits</TH><TH>Dates</TH></tr>
      </thead>
      <tbody>
        {ranked.map((r, i) => (
          <tr key={r.doctor}>
            <TD muted>#{i + 1}</TD>
            <TD>{r.doctor}</TD>
            <TD muted>{r.speciality || '—'}</TD>
            <TD muted>{r.clinic || '—'}</TD>
            <TD><ListedBadge value={r.listed} /></TD>
            <td style={{ padding: '7px 12px', borderBottom: '1px solid #f1f5f9' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <div style={{ flex: 1, height: 6, background: '#f1f5f9', borderRadius: 3, maxWidth: 80 }}>
                  <div style={{ height: '100%', borderRadius: 3, background: i === 0 ? 'var(--green)' : i < 3 ? 'var(--accent)' : 'var(--muted)', width: `${(r.count / max) * 100}%` }} />
                </div>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem', fontWeight: 600, color: i === 0 ? 'var(--green)' : 'var(--text)' }}>{r.count}</span>
              </div>
            </td>
            <TD muted>{r.dates.sort().join(', ')}</TD>
          </tr>
        ))}
      </tbody>
    </table>
</div>
  )
}

export default function VisitTrackerSection({ visitTracker, cfg }) {
  const [expanded, setExpanded] = useState({})
  const [viewMode, setViewMode] = useState({})

  if (!visitTracker?.by_delegate?.length) {
    return <div style={{ color: 'var(--muted)', padding: '16px 0' }}>No visit tracker data.</div>
  }

  const { by_delegate } = visitTracker
  const color = cfg?.color || 'var(--accent)'
  const barData = {
    labels: by_delegate.map(d => d.mr),
    datasets: [
      { label: 'Total Visits', data: by_delegate.map(d => d.total_visits), backgroundColor: PALETTE[0] },
      { label: 'Listed Dr Covered', data: by_delegate.map(d => d.listed_covered || 0), backgroundColor: PALETTE[2] },
    ],
  }

  const toggle = (id) => setExpanded(e => ({ ...e, [id]: !e[id] }))
  const getMode = (id) => viewMode[id] || 'byDay'
  const setMode = (id, mode) => setViewMode(v => ({ ...v, [id]: mode }))

  return (
    <div>
      <SectionLabel tag="VISIT TRACKER" text="Doctor Visits" monthColor={color} />
      <ChartCard title="Visits by MR" height="h250" monthColor={color}>
        <Bar data={barData} options={baseOptions()} />
      </ChartCard>

      {by_delegate.map((del, idx) => {
        const isOpen = !!expanded[del.mr_id]
        const mode = getMode(del.mr_id)
        const mrColor = PALETTE[idx % PALETTE.length]
        return (
          <div key={del.mr_id} className="tbl-card" style={{ marginBottom: 12, borderTop: `2px solid ${mrColor}` }}>
            <div
              className="tbl-header"
              onClick={() => toggle(del.mr_id)}
              style={{ cursor: 'pointer', userSelect: 'none' }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', background: mrColor }} />
                <span className="tbl-title">{del.mr}</span>
                <span className="badge n">{del.total_visits} visits</span>
                <span className="badge j">{del.listed_covered ?? 0} listed doctors</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                {isOpen && (
                  <FilterToggle value={mode} onChange={m => setMode(del.mr_id, m)} />
                )}
                <span style={{ color: 'var(--muted)', fontSize: '0.8rem' }}>{isOpen ? '▲' : '▼'}</span>
              </div>
            </div>

            {isOpen && del.visits.length > 0 && (
              mode === 'byDay'
                ? <ByDayView visits={del.visits} />
                : <MostVisitedView visits={del.visits} />
            )}
            {isOpen && del.visits.length === 0 && (
              <div style={{ padding: '12px 16px', color: 'var(--muted)', fontSize: '0.8rem' }}>No visit records.</div>
            )}
          </div>
        )
      })}
    </div>
  )
}
