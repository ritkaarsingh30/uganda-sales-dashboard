import { Bar, Radar } from 'react-chartjs-2'
import { useDelegates, useDelegateInsights, useRefreshDelegateInsights } from '../hooks/useDashboard.js'
import InsightBox from '../components/InsightBox.jsx'
import { useFilter } from '../context/FilterContext.jsx'
import { baseOptions, monthColor, PALETTE } from '../utils/chartConfig.js'
import { MONTH_CONFIG } from '../utils/monthConfig.js'
import KpiCard from '../components/KpiCard.jsx'
import ChartCard from '../components/ChartCard.jsx'
import DataTable from '../components/DataTable.jsx'
import SectionLabel from '../components/SectionLabel.jsx'



const EUR = n => n != null ? '€' + Math.round(n).toLocaleString() : '—'
const pct = n => n != null ? n.toFixed(1) + '%' : '—'
const num = n => n != null ? n.toLocaleString() : '—'

// ── Per-delegate card ─────────────────────────────────────────────────────────
function DelegateCard({ d, activeMonths }) {
  const monthKeys = Object.keys(d.months || {}).filter(m => activeMonths.includes(m))
  if (monthKeys.length === 0) return null

  const q = d.q1 || {}

  // Radar: normalise 5 dimensions relative to the delegate's own maxima so it always looks full
  const sortedM = [...monthKeys].sort(
    (a, b) => (MONTH_CONFIG[a]?.monthNum || 0) - (MONTH_CONFIG[b]?.monthNum || 0)
  )

  // Calls trend (mini bar – one bar per month)
  const callsData = {
    labels: sortedM.map(m => MONTH_CONFIG[m]?.short || m.toUpperCase()),
    datasets: [
      {
        label: 'Total Calls',
        data: sortedM.map(m => d.months[m]?.calls || 0),
        backgroundColor: sortedM.map(m => monthColor(m).alpha),
        borderColor: sortedM.map(m => monthColor(m).solid),
        borderWidth: 1,
        borderRadius: 4,
      },
    ],
  }

  const ordersData = {
    labels: sortedM.map(m => MONTH_CONFIG[m]?.short || m.toUpperCase()),
    datasets: [
      {
        label: 'Orders (EUR)',
        data: sortedM.map(m => d.months[m]?.orders_eur || 0),
        backgroundColor: sortedM.map(m => monthColor(m).soft || monthColor(m).alpha),
        borderColor: sortedM.map(m => monthColor(m).solid),
        borderWidth: 1,
        borderRadius: 4,
      },
    ],
  }

  const miniBarOpts = (yFormatter) => ({
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: '#1e293b',
        titleColor: '#f8fafc',
        bodyColor: '#cbd5e1',
        borderColor: '#334155',
        borderWidth: 1,
        cornerRadius: 6,
        padding: 8,
        callbacks: { label: ctx => yFormatter(ctx.parsed.y) },
      },
    },
    scales: {
      x: {
        ticks: { color: '#94a3b8', font: { size: 9 } },
        grid: { color: 'rgba(148,163,184,0.1)' },
      },
      y: {
        ticks: { color: '#94a3b8', font: { size: 9 }, callback: yFormatter },
        grid: { color: 'rgba(148,163,184,0.1)' },
        beginAtZero: true,
      },
    },
  })

  // Radar dimensions — normalised 0–100
  const maxCalls = Math.max(...monthKeys.map(m => d.months[m]?.calls || 0), 1)
  const maxOrders = Math.max(...monthKeys.map(m => d.months[m]?.orders_eur || 0), 1)
  const maxDays = Math.max(...monthKeys.map(m => d.months[m]?.days_worked || 0), 1)
  const maxPresc = Math.max(...monthKeys.map(m => d.months[m]?.prescriber || 0), 1)
  const maxPharm = Math.max(...monthKeys.map(m => d.months[m]?.pharmacy || 0), 1)

  const radarDatasets = sortedM.map(m => {
    const mm = d.months[m] || {}
    return {
      label: MONTH_CONFIG[m]?.short || m.toUpperCase(),
      data: [
        ((mm.calls || 0) / maxCalls * 100),
        ((mm.orders_eur || 0) / maxOrders * 100),
        ((mm.days_worked || 0) / maxDays * 100),
        ((mm.prescriber || 0) / maxPresc * 100),
        ((mm.pharmacy || 0) / maxPharm * 100),
      ],
      raw: [mm.calls || 0, mm.orders_eur || 0, mm.days_worked || 0, mm.prescriber || 0, mm.pharmacy || 0],
      backgroundColor: monthColor(m).soft || monthColor(m).alpha.replace('0.75', '0.15'),
      borderColor: monthColor(m).solid,
      borderWidth: 2,
      pointBackgroundColor: monthColor(m).solid,
      pointRadius: 3,
    }
  })

  const radarData = {
    labels: ['Calls', 'Orders', 'Days', 'Prescribers', 'Pharmacy'],
    datasets: radarDatasets,
  }

  const radarOpts = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: 'nearest', intersect: false },
    plugins: {
      legend: {
        position: 'bottom',
        labels: { color: '#64748b', font: { size: 9 }, boxWidth: 10, padding: 8 },
      },
      tooltip: {
        backgroundColor: '#1e293b',
        titleColor: '#f8fafc',
        bodyColor: '#cbd5e1',
        borderColor: '#334155',
        borderWidth: 1,
        cornerRadius: 6,
        callbacks: {
          label: ctx => {
            const raw = ctx.dataset.raw?.[ctx.dataIndex] ?? 0
            const fmtByAxis = [
              v => v.toLocaleString(),
              v => '€' + Math.round(v).toLocaleString(),
              v => v + 'd',
              v => v.toLocaleString(),
              v => v.toLocaleString(),
            ]
            const value = (fmtByAxis[ctx.dataIndex] || (v => v))(raw)
            return ` ${ctx.dataset.label}: ${value}`
          },
        },
      },
    },
    scales: {
      r: {
        min: 0, max: 100,
        ticks: { display: false },
        grid: { color: 'rgba(148,163,184,0.2)' },
        angleLines: { color: 'rgba(148,163,184,0.2)' },
        pointLabels: { color: '#64748b', font: { size: 10 } },
      },
    },
  }

  // Tour coverage pill colour
  const tourPct = q.tour_coverage_pct
  const coverageColor = tourPct == null ? 'var(--muted)'
    : tourPct >= 80 ? 'var(--green)'
      : tourPct >= 50 ? 'var(--orange)'
        : 'var(--red)'

  return (
    <div style={{
      background: 'var(--card)',
      border: '1px solid var(--border)',
      borderRadius: 14,
      padding: 20,
      marginBottom: 20,
      boxShadow: 'var(--shadow-sm)',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
        {/* Avatar */}
        <div style={{
          width: 42, height: 42, borderRadius: '50%',
          background: `linear-gradient(135deg, ${PALETTE[0]}, ${PALETTE[1]})`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          color: '#fff', fontWeight: 700, fontSize: '1rem', flexShrink: 0,
        }}>
          {(d.short_name || d.display_name || '?')[0].toUpperCase()}
        </div>
        <div>
          <div style={{ fontWeight: 700, fontSize: '0.95rem', color: 'var(--text)' }}>
            {d.display_name}
          </div>
          <div style={{ fontSize: '0.72rem', color: 'var(--muted)', marginTop: 2 }}>
            {d.territory || 'No territory'}
          </div>
        </div>
        {/* Summary pills */}
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 8, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
          <StatPill label="Calls" value={num(q.calls)} color="var(--accent)" />
          <StatPill label="Orders" value={EUR(q.orders_eur)} color="var(--purple)" />
          <StatPill label="Days" value={`${q.days_worked ?? '—'}d`} color="var(--teal)" />
          <StatPill label="Coverage" value={pct(tourPct)} color={coverageColor} />
        </div>
      </div>

      {/* Charts row */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 180px', gap: 16 }}>
        {/* Calls bar */}
        <div>
          <div style={{ fontSize: '0.68rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--muted)', marginBottom: 6 }}>
            Total Calls by Month
          </div>
          <div style={{ height: 130 }}>
            <Bar data={callsData} options={miniBarOpts(v => v.toLocaleString())} />
          </div>
        </div>

        {/* Orders bar */}
        <div>
          <div style={{ fontSize: '0.68rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--muted)', marginBottom: 6 }}>
            Orders (EUR) by Month
          </div>
          <div style={{ height: 130 }}>
            <Bar data={ordersData} options={miniBarOpts(v => '€' + (v >= 1000 ? (v / 1000).toFixed(1) + 'k' : v))} />
          </div>
        </div>

        {/* Radar */}
        <div>
          <div style={{ fontSize: '0.68rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--muted)', marginBottom: 6 }}>
            Performance Profile
          </div>
          <div style={{ height: 130 }}>
            <Radar data={radarData} options={radarOpts} />
          </div>
        </div>
      </div>

      {/* Month detail row */}
      <div style={{ display: 'flex', gap: 8, marginTop: 14, flexWrap: 'wrap' }}>
        {sortedM.map(m => {
          const mm = d.months[m] || {}
          const mc = monthColor(m)
          return (
            <div key={m} style={{
              flex: '1 1 120px',
              background: mc.soft || 'rgba(148,163,184,0.08)',
              border: `1px solid ${mc.solid}33`,
              borderRadius: 8,
              padding: '8px 12px',
            }}>
              <div style={{ fontSize: '0.65rem', fontWeight: 700, color: mc.solid, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 }}>
                {MONTH_CONFIG[m]?.short || m.toUpperCase()}
              </div>
              <div style={{ fontSize: '0.72rem', lineHeight: 1.9, color: 'var(--text)' }}>
                <div>Calls: <strong>{mm.calls ?? '—'}</strong></div>
                <div>Prescribers: <strong>{mm.prescriber ?? '—'}</strong></div>
                <div>Pharmacy: <strong>{mm.pharmacy ?? '—'}</strong></div>
                <div>Orders: <strong>{EUR(mm.orders_eur)}</strong></div>
                <div>Tour: <strong>{mm.tour_covered}/{mm.tour_planned}</strong></div>
                <div>Days: <strong>{mm.days_worked ?? '—'}/{mm.days_target ?? '—'}</strong></div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function StatPill({ label, value, color }) {
  return (
    <div style={{
      background: `${color}12`,
      border: `1px solid ${color}33`,
      borderRadius: 20,
      padding: '3px 10px',
      fontSize: '0.72rem',
      color,
      display: 'flex', flexDirection: 'column', alignItems: 'center',
      lineHeight: 1.3,
    }}>
      <span style={{ fontWeight: 700 }}>{value}</span>
      <span style={{ opacity: 0.7, fontSize: '0.62rem' }}>{label}</span>
    </div>
  )
}

// ── Main tab ──────────────────────────────────────────────────────────────────
export default function DelegatesTab() {
  const { data, isLoading } = useDelegates()
  const { data: ins, isLoading: insLoading } = useDelegateInsights()
  const { mutate: refreshIns, isPending: insRefreshing } = useRefreshDelegateInsights()
  const { activeMonths } = useFilter()

  if (isLoading) return <div style={{ color: 'var(--muted)', padding: 40 }}>Loading delegates...</div>
  if (!data) return null

  const { q1_summary, delegates } = data

  const filteredDels = (delegates || [])
    .filter(d => activeMonths.some(m => d.months?.[m]))
    .sort((a, b) => (b.q1?.orders_eur || 0) - (a.q1?.orders_eur || 0))

  // Cross-delegate bar charts
  const tourBar = {
    labels: filteredDels.map(d => d.short_name || d.display_name),
    datasets: [
      { label: 'Planned', data: filteredDels.map(d => d.q1?.tour_planned || 0), backgroundColor: 'rgba(148,163,184,0.4)', borderRadius: 3 },
      { label: 'Covered', data: filteredDels.map(d => d.q1?.tour_covered || 0), backgroundColor: PALETTE[0], borderRadius: 3 },
    ],
  }

  const callsBar = {
    labels: filteredDels.map(d => d.short_name || d.display_name),
    datasets: [
      { label: 'Total Calls', data: filteredDels.map(d => d.q1?.calls || 0), backgroundColor: PALETTE[0], borderRadius: 3 },
      { label: 'Prescribers', data: filteredDels.map(d => d.q1?.prescriber || 0), backgroundColor: PALETTE[2], borderRadius: 3 },
      { label: 'Pharmacy', data: filteredDels.map(d => d.q1?.pharmacy || 0), backgroundColor: PALETTE[1], borderRadius: 3 },
    ],
  }

  const ordersBar = {
    labels: filteredDels.map(d => d.short_name || d.display_name),
    datasets: [
      {
        label: 'Orders (EUR)',
        data: filteredDels.map(d => d.q1?.orders_eur || 0),
        backgroundColor: filteredDels.map((_, i) => PALETTE[i % PALETTE.length]),
        borderRadius: 4,
      },
    ],
  }

  const summaryRows = filteredDels.map((d, i) => ({
    rank: i + 1,
    name: d.display_name,
    initial: (d.short_name || d.display_name || '?')[0].toUpperCase(),
    color: PALETTE[i % PALETTE.length],
    territory: d.territory,
    total_calls: d.q1?.calls,
    prescriber: d.q1?.prescriber,
    pharmacy: d.q1?.pharmacy,
    drs_converted: d.q1?.drs_converted,
    conversion_pct: d.q1?.conversion_pct ?? null,
    orders_eur: d.q1?.orders_eur != null ? EUR(d.q1.orders_eur) : '—',
    ctc_eur: d.q1?.ctc_eur != null ? EUR(d.q1.ctc_eur) : '—',
    ctc_ratio: d.q1?.ctc_ratio ?? null,
    days_worked: d.q1?.days_worked ?? null,
    days_target: d.q1?.days_target ?? null,
    coverage_pct: d.q1?.tour_coverage_pct ?? null,
  }))

  const MiniBar = ({ pct, color, label }) => (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 110 }}>
      <div className="progress-bar" style={{ flex: 1, width: 64 }}>
        <div className="progress-fill" style={{ width: `${Math.min(100, Math.max(0, pct))}%`, background: color }} />
      </div>
      <span style={{ fontSize: '0.74rem', color: 'var(--muted)', fontFamily: 'var(--font-mono)', whiteSpace: 'nowrap' }}>{label}</span>
    </div>
  )

  const cols = [
    { key: 'rank', label: '#', align: 'center', render: row => <span className={`badge ${row.rank === 1 ? 'j' : 'n'}`}>#{row.rank}</span> },
    {
      key: 'name', label: 'MR',
      render: row => (
        <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
          <span style={{
            width: 24, height: 24, borderRadius: '50%', flexShrink: 0,
            background: row.color, color: '#fff', fontSize: '0.68rem', fontWeight: 700,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>{row.initial}</span>
          <span style={{ fontWeight: 700 }}>{row.name}</span>
        </div>
      ),
    },
    { key: 'territory', label: 'Territory' },
    { key: 'total_calls', label: 'Total Calls', align: 'right' },
    { key: 'prescriber', label: 'Prescribers', align: 'right' },
    { key: 'pharmacy', label: 'Pharmacy', align: 'right' },
    { key: 'drs_converted', label: 'DRs Conv.', align: 'right' },
    { key: 'orders_eur', label: 'Orders €', align: 'right' },
    { key: 'ctc_eur', label: 'CTC €', align: 'right' },
    { key: 'ctc_ratio', label: 'CTC Ratio', align: 'right' },
    {
      key: 'days_wt', label: 'Days Worked', align: 'left',
      render: row => row.days_worked == null ? '—' : (
        <MiniBar
          pct={row.days_target ? (row.days_worked / row.days_target) * 100 : 0}
          color={row.color}
          label={row.days_target ? `${row.days_worked}/${row.days_target}` : row.days_worked}
        />
      ),
    },
    {
      key: 'coverage_pct', label: 'Tour Coverage', align: 'left',
      render: row => row.coverage_pct == null ? '—' : (
        <MiniBar pct={row.coverage_pct} color={row.color} label={`${row.coverage_pct.toFixed(0)}%`} />
      ),
    },
  ]

  return (
    <div>
      {/* KPIs */}
      <div className="kpi">
        <KpiCard label="Total Calls" value={(q1_summary?.total_calls || 0).toLocaleString()} />
        <KpiCard label="Total Orders" value={EUR(q1_summary?.total_orders_eur)} />
        <KpiCard label="Total CTC" value={EUR(q1_summary?.total_ctc_eur)} />
        <KpiCard label="CTC Ratio" value={q1_summary?.overall_ctc_ratio != null ? (q1_summary.overall_ctc_ratio * 100).toFixed(1) + '%' : '—'} />
        <KpiCard label="Active MRs" value={filteredDels.length} />
      </div>

      {/* AI Insights */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <SectionLabel tag="AI INSIGHTS — FIELD FORCE" />
        <button className="btn" onClick={() => refreshIns()} disabled={insRefreshing} style={{ marginBottom: 12 }}>
          {insRefreshing ? 'Generating...' : 'Refresh Insights'}
        </button>
      </div>
      {(ins?.insights || []).map((item, i) => (
        <InsightBox key={i} type={item.type} icon={item.icon} title={item.title} text={item.text} loading={insLoading} />
      ))}

      {/* Cross-delegate overview charts */}
      <div className="grid-2" style={{ marginBottom: 16 }}>
        <ChartCard title="Calls by MR" sub="Total · Prescribers · Pharmacy" height="h260">
          <Bar data={callsBar} options={baseOptions()} />
        </ChartCard>
        <ChartCard title="Orders by MR (EUR)" sub="YTD across active months" height="h260">
          <Bar data={ordersBar} options={baseOptions({
            plugins: {
              legend: { display: false },
              tooltip: { callbacks: { label: ctx => ` €${ctx.parsed.y.toLocaleString()}` } },
            },
          })} />
        </ChartCard>
      </div>
      <ChartCard title="Tour Plan Coverage" sub="Planned vs covered stops per MR" height="h240">
        <Bar data={tourBar} options={baseOptions()} />
      </ChartCard>

      {/* Per-delegate detail cards */}
      <SectionLabel tag="PER MR" text="Calls · Orders · Performance Profile" />
      {filteredDels.map(d => (
        <DelegateCard key={d.id} d={d} activeMonths={activeMonths} />
      ))}

      {/* Summary table */}
      <SectionLabel tag="MR SUMMARY TABLE" />
      <DataTable
        title="MR Performance Summary"
        sub="Ranked by total orders (EUR), across active months"
        badge={`${filteredDels.length} MRs`}
        columns={cols}
        rows={summaryRows}
      />
    </div>
  )
}
