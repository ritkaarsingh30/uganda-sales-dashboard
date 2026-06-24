import { useState } from 'react'
import { Bar, Doughnut } from 'react-chartjs-2'
import { baseOptions, baseOptionsNoScale, PALETTE } from '../utils/chartConfig.js'
import ChartCard from './ChartCard.jsx'
import SectionLabel from './SectionLabel.jsx'
import DataTable from './DataTable.jsx'

const entryCols = [
  { key: 'date', label: 'Date' },
  { key: 'planned_area', label: 'Planned Area' },
  { key: 'actual_area', label: 'Actual Area' },
  { key: 'covered', label: 'Covered' },
  { key: 'joint_working', label: 'Joint Working' },
]

export default function TourPlanSection({ tourPlan, cfg }) {
  const [expanded, setExpanded] = useState({})
  const toggle = (mrName) => setExpanded(e => ({ ...e, [mrName]: !e[mrName] }))

  if (!tourPlan || !tourPlan.summary || !tourPlan.summary.total) {
    return <div style={{ color: 'var(--muted)', padding: '16px 0' }}>No tour plan data.</div>
  }

  const { summary, by_delegate, entries_by_delegate } = tourPlan
  const color = cfg?.color || 'var(--accent)'
  const monthLabel = cfg?.label || ''

  // Sort by coverage rate descending for the stacked bar
  const sorted = [...(by_delegate || [])].sort((a, b) => (b.coverage_pct ?? 0) - (a.coverage_pct ?? 0))

  const coverageBarData = {
    labels: sorted.map(d => d.mr),
    datasets: [
      {
        label: 'Covered',
        data: sorted.map(d => d.covered),
        backgroundColor: 'rgba(16,185,129,0.8)',
        stack: 'cov',
      },
      {
        label: 'Missed',
        data: sorted.map(d => d.uncovered),
        backgroundColor: 'rgba(239,68,68,0.75)',
        stack: 'cov',
      },
    ],
  }

  const coverageBarOptions = {
    ...baseOptions({
      indexAxis: 'y',
      plugins: {
        legend: { labels: { color: '#64748b', font: { size: 11 } } },
        tooltip: {
          callbacks: {
            afterLabel: ctx => {
              const d = sorted[ctx.dataIndex]
              return `Coverage: ${d?.coverage_pct?.toFixed(1) ?? '—'}%`
            },
          },
        },
      },
      scales: {
        x: { stacked: true, ticks: { color: '#94a3b8', font: { size: 11 } }, grid: { color: 'rgba(226,232,240,0.8)' } },
        y: { stacked: true, ticks: { color: '#94a3b8', font: { size: 11 } }, grid: { color: 'rgba(226,232,240,0.8)' } },
      },
    }),
  }

  const totalCov = summary.covered || 0
  const totalMissed = summary.uncovered || 0
  const overallPct = summary.coverage_pct ?? (summary.total ? (totalCov / summary.total * 100) : 0)

  const doughnutData = {
    labels: ['Covered', 'Missed'],
    datasets: [{
      data: [totalCov, totalMissed],
      backgroundColor: ['rgba(16,185,129,0.85)', 'rgba(239,68,68,0.75)'],
      borderWidth: 0,
    }],
  }

  const doughnutOptions = {
    ...baseOptionsNoScale({
      plugins: {
        legend: { position: 'bottom', labels: { color: '#64748b', font: { size: 11 } } },
        tooltip: { callbacks: { label: ctx => ` ${ctx.label}: ${ctx.parsed}` } },
      },
      cutout: '62%',
    }),
  }

  const mrNames = Object.keys(entries_by_delegate || {})

  return (
    <div>
      <SectionLabel tag="TOUR PLAN" text="vs Actual Working Area" monthColor={color} />
      {/* <div className="kpi" style={{ marginBottom: 16 }}>
        <div className="kpi-card"><div className="kpi-label">Total Days</div><div className="kpi-value">{summary.total}</div></div>
        <div className="kpi-card"><div className="kpi-label">Covered</div><div className="kpi-value" style={{ color: 'var(--green)' }}>{summary.covered}</div></div>
        <div className="kpi-card"><div className="kpi-label">Uncovered</div><div className="kpi-value" style={{ color: 'var(--red)' }}>{summary.uncovered}</div></div>
        <div className="kpi-card"><div className="kpi-label">Coverage</div><div className="kpi-value">{summary.coverage_pct?.toFixed(1)}%</div></div>
        <div className="kpi-card"><div className="kpi-label">Joint Working Days</div><div className="kpi-value">{summary.joint_working}</div></div>
      </div> */}
      <div className="grid-2" style={{ marginBottom: 16, alignItems: 'start' }}>
        <ChartCard
          title={`Coverage by MR — ${monthLabel}`}
          sub="Covered vs Missed stops · sorted by adherence rate"
          height={sorted.length > 8 ? 'h400' : sorted.length > 6 ? 'h340' : sorted.length > 4 ? 'h300' : 'h250'}
        >
          <Bar data={coverageBarData} options={coverageBarOptions} />
        </ChartCard>
        <ChartCard title="Overall Plan Coverage" sub={`${overallPct.toFixed(1)}% of planned stops visited`} height="h280">
          <div style={{ position: 'relative', height: '100%' }}>
            <Doughnut data={doughnutData} options={doughnutOptions} />
            <div style={{
              position: 'absolute', top: '42%', left: '50%',
              transform: 'translate(-50%, -50%)',
              textAlign: 'center', pointerEvents: 'none',
            }}>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: '1.4rem', fontWeight: 700, color: overallPct >= 70 ? 'var(--green)' : overallPct >= 40 ? 'var(--orange)' : 'var(--red)' }}>
                {overallPct.toFixed(0)}%
              </div>
              <div style={{ fontSize: '0.65rem', color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>covered</div>
            </div>
          </div>
        </ChartCard>
      </div>

      {mrNames.map((mrName, idx) => {
        const mrEntries = entries_by_delegate[mrName] || []
        const mrStats = by_delegate.find(d => d.mr === mrName)
        const mrColor = PALETTE[idx % PALETTE.length]
        const covPct = mrStats ? mrStats.coverage_pct?.toFixed(1) : null
        const isOpen = !!expanded[mrName]
        return (
          <div key={mrName} style={{ marginBottom: 16 }}>
            <div
              onClick={() => toggle(mrName)}
              style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10, marginBottom: 8, cursor: 'pointer', userSelect: 'none' }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <span style={{
                  display: 'inline-block', width: 10, height: 10,
                  borderRadius: '50%', background: mrColor, flexShrink: 0,
                }} />
                <span style={{ fontWeight: 700, fontSize: '0.82rem', textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--text)' }}>
                  {mrName}
                </span>
                {mrStats && (
                  <>
                    <span className="badge n">{mrStats.planned} planned</span>
                    <span className="badge g">{mrStats.covered} covered</span>
                    {mrStats.uncovered > 0 && <span className="badge d">{mrStats.uncovered} uncovered</span>}
                    {covPct && <span className="badge j">{covPct}%</span>}
                  </>
                )}
              </div>
              <span style={{ color: 'var(--muted)', fontSize: '0.8rem' }}>{isOpen ? '▲' : '▼'}</span>
            </div>

            {isOpen && (
              <DataTable
                title=""
                badge={`${mrEntries.length} days`}
                borderColor={mrColor}
                columns={entryCols}
                rows={mrEntries}
              />
            )}
          </div>
        )
      })}
    </div>
  )
}
