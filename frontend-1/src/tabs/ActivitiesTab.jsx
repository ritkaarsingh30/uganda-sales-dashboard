import { useMemo } from 'react'
import { Bar, Doughnut } from 'react-chartjs-2'
import { useActivities } from '../hooks/useDashboard.js'
import { useFilter } from '../context/FilterContext.jsx'
import { baseOptions, baseOptionsNoScale, PALETTE } from '../utils/chartConfig.js'
import { MONTH_CONFIG } from '../utils/monthConfig.js'
import KpiCard from '../components/KpiCard.jsx'
import ChartCard from '../components/ChartCard.jsx'
import SectionLabel from '../components/SectionLabel.jsx'
import DonutCenter from '../components/DonutCenter.jsx'

const UGX = n => n != null ? 'UGX ' + Math.round(n).toLocaleString() : '—'
const EUR = n => n != null ? '€' + n.toFixed(2) : '—'

const STATUS_COLORS = {
  executed:         'rgba(16,185,129,0.8)',
  planned_not_done: 'rgba(245,158,11,0.8)',
  unplanned:        'rgba(99,102,241,0.8)',
}

function ActivityTable({ rows, title, variant }) {
  if (!rows?.length) return null
  const colors = { executed: 'var(--green)', planned_not_done: 'var(--orange)', unplanned: 'var(--accent)' }
  const color = colors[variant] || 'var(--muted)'
  return (
    <div className="tbl-card" style={{ borderTop: `2px solid ${color}`, marginBottom: 12 }}>
      <div className="tbl-header">
        <span className="tbl-title" style={{ color }}>{title}</span>
        <span className="badge n">{rows.length}</span>
      </div>
      <table>
        <thead>
          <tr>
            <th>Doctor</th><th>Hospital</th><th>Speciality</th><th>MR</th>
            <th>Area</th><th>Activity Type</th><th>Focus Products</th>
            <th>Planned (EUR)</th><th>Actual</th><th>Visits</th>
            {variant !== 'planned_not_done' && <th>Sales Outcome</th>}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>
              <td>{r.doctor}</td>
              <td style={{ color: 'var(--muted)', fontSize: '0.75rem' }}>{r.hospital}</td>
              <td style={{ color: 'var(--muted)', fontSize: '0.75rem' }}>{r.speciality}</td>
              <td style={{ color: 'var(--muted)', fontSize: '0.75rem' }}>{r.delegate}</td>
              <td style={{ color: 'var(--muted)', fontSize: '0.75rem' }}>{r.area}</td>
              <td style={{ color: 'var(--muted)', fontSize: '0.75rem' }}>{r.activity}</td>
              <td style={{ fontSize: '0.75rem' }}>{r.focus_products}</td>
              <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem' }}>{r.planned_eur > 0 ? EUR(r.planned_eur) : '—'}</td>
              <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem' }}>{r.actual_eur > 0 ? EUR(r.actual_eur) : '—'}</td>
              <td>{r.num_visits || '—'}</td>
              {variant !== 'planned_not_done' && (
                <td style={{ fontSize: '0.75rem', maxWidth: 180 }}>
                  {r.sales_outcome && r.sales_outcome !== '0' && r.sales_outcome !== 'nan'
                    ? <span style={{ color: 'var(--green)', fontWeight: 600 }}>{Array.isArray(r.sales_outcome) ? r.sales_outcome.join(', ') : r.sales_outcome}</span>
                    : <span style={{ color: 'var(--muted)' }}>—</span>}
                </td>
              )}
            </tr>
          ))}
        </tbody>
        {variant !== 'planned_not_done' && (() => {
          const totalActual = rows.reduce((s, r) => s + (r.actual_eur || 0), 0)
          return totalActual > 0 ? (
            <tfoot>
              <tr style={{ background: '#f8fafc', borderTop: '2px solid var(--border)' }}>
                <td colSpan={7} style={{ padding: '6px 12px', fontSize: '0.72rem', color: 'var(--muted)', fontWeight: 600 }}>TOTAL</td>
                <td style={{ padding: '6px 12px', fontFamily: 'var(--font-mono)', fontSize: '0.78rem', fontWeight: 700, color: 'var(--text)' }}>—</td>
                <td style={{ padding: '6px 12px', fontFamily: 'var(--font-mono)', fontSize: '0.78rem', fontWeight: 700, color }}>{EUR(totalActual)}</td>
                <td colSpan={2} />
              </tr>
            </tfoot>
          ) : null
        })()}
      </table>
    </div>
  )
}

function useMonthCharts(mb) {
  return useMemo(() => {
    if (!mb) return {}
    const { matched = [], planned_not_done = [], unplanned_done = [], summary } = mb

    // Execution status doughnut
    const statusDoughnut = {
      labels: ['Executed', 'Not Executed', 'Unplanned'],
      datasets: [{
        data: [summary.executed, summary.not_executed, summary.unplanned],
        backgroundColor: [STATUS_COLORS.executed, STATUS_COLORS.planned_not_done, STATUS_COLORS.unplanned],
        borderWidth: 0,
      }],
    }

    // Activities by delegate — stacked
    const delegateMap = {}
    const addRow = (rows, status) => rows.forEach(r => {
      const del = r.delegate || r.responsible || 'Unknown'
      if (!delegateMap[del]) delegateMap[del] = { executed: 0, planned_not_done: 0, unplanned: 0 }
      delegateMap[del][status]++
    })
    addRow(matched, 'executed')
    addRow(planned_not_done, 'planned_not_done')
    addRow(unplanned_done, 'unplanned')
    const delLabels = Object.keys(delegateMap).sort()
    const delegateBar = {
      labels: delLabels,
      datasets: [
        { label: 'Executed',     data: delLabels.map(d => delegateMap[d].executed),         backgroundColor: STATUS_COLORS.executed,         stack: 'a' },
        { label: 'Not Executed', data: delLabels.map(d => delegateMap[d].planned_not_done), backgroundColor: STATUS_COLORS.planned_not_done, stack: 'a' },
        { label: 'Unplanned',   data: delLabels.map(d => delegateMap[d].unplanned),         backgroundColor: STATUS_COLORS.unplanned,         stack: 'a' },
      ],
    }

    // Activities by speciality — only executed + unplanned (planned_not_done never happened)
    const specMap = {}
    ;[...matched, ...unplanned_done].forEach(r => {
      const s = r.speciality || 'Other'
      specMap[s] = (specMap[s] || 0) + 1
    })
    const specEntries = Object.entries(specMap).sort((a, b) => b[1] - a[1])
    const specialityBar = {
      labels: specEntries.map(([k]) => k),
      datasets: [{
        label: 'Activities',
        data: specEntries.map(([, v]) => v),
        backgroundColor: specEntries.map((_, i) => PALETTE[i % PALETTE.length]),
      }],
    }

    // Budget: planned vs actual per delegate (EUR)
    const budgetMap = {}
    ;[...matched, ...planned_not_done].forEach(r => {
      const del = r.delegate || 'Unknown'
      if (!budgetMap[del]) budgetMap[del] = { planned: 0, actual: 0 }
      budgetMap[del].planned += r.planned_eur || 0
      budgetMap[del].actual  += r.actual_eur  || 0
    })
    unplanned_done.forEach(r => {
      const del = r.delegate || r.responsible || 'Unknown'
      if (!budgetMap[del]) budgetMap[del] = { planned: 0, actual: 0 }
      budgetMap[del].actual += r.actual_eur || 0
    })
    const budgetLabels = Object.keys(budgetMap).sort()
    const budgetBar = {
      labels: budgetLabels,
      datasets: [
        { label: 'Planned (EUR)', data: budgetLabels.map(d => +budgetMap[d].planned.toFixed(2)), backgroundColor: 'rgba(148,163,184,0.5)' },
        { label: 'Actual (EUR)',  data: budgetLabels.map(d => +budgetMap[d].actual.toFixed(2)),  backgroundColor: 'rgba(99,102,241,0.75)' },
      ],
    }

    return { statusDoughnut, delegateBar, specialityBar, budgetBar }
  }, [mb])
}

export default function ActivitiesTab() {
  const { data, isLoading } = useActivities()
  const { activeMonths } = useFilter()

  if (isLoading) return <div style={{ color: 'var(--muted)', padding: 40 }}>Loading activities...</div>
  if (!data) return null

  const { overall, by_month } = data

  // Overall execution doughnut (cross-month)
  const overallDoughnut = {
    labels: ['Executed', 'Not Executed', 'Unplanned'],
    datasets: [{
      data: [overall.executed, overall.not_executed, overall.unplanned],
      backgroundColor: [STATUS_COLORS.executed, STATUS_COLORS.planned_not_done, STATUS_COLORS.unplanned],
      borderWidth: 0,
    }],
  }

  return (
    <div>
      <div className="kpi">
        <KpiCard label="Total Planned"       value={overall?.total_planned} />
        <KpiCard label="Executed"            value={overall?.executed} />
        <KpiCard label="Not Executed"        value={overall?.not_executed} />
        <KpiCard label="Unplanned"           value={overall?.unplanned} />
        <KpiCard label="Execution Rate"      value={overall?.execution_rate_pct != null ? overall.execution_rate_pct.toFixed(1) + '%' : '—'} />
        <KpiCard label="Planned Budget"      value={EUR(overall?.planned_budget_eur)} />
        <KpiCard label="Actual Spent"        value={EUR(overall?.actual_spent_eur)} />

        <KpiCard
          label="Activity ROI"
          value={overall?.roi_pct != null ? overall.roi_pct.toFixed(1) + '%' : '—'}
          sub="outcome ÷ spend"
        />
        <KpiCard
          label="Cost per Visit"
          value={overall?.cost_per_visit_eur != null ? '€' + overall.cost_per_visit_eur.toFixed(2) : '—'}
          sub="EUR per doctor visit"
        />
        <KpiCard
          label="Cost per Outcome"
          value={overall?.cost_per_outcome_eur != null ? '€' + overall.cost_per_outcome_eur.toFixed(2) : '—'}
          sub="EUR per activity with sale"
        />
      </div>

      <div className="grid-2" style={{ marginBottom: 20 }}>
        <ChartCard title="Overall Execution Status" height="h250">
          <DonutCenter
            data={overallDoughnut}
            options={baseOptionsNoScale()}
            value={overall?.execution_rate_pct != null ? overall.execution_rate_pct.toFixed(0) + '%' : '—'}
            label="Executed"
            color="var(--green)"
          />
        </ChartCard>
        <ChartCard title="With vs Without Sales Outcome" height="h250">
          <DonutCenter
            data={{
              labels: ['With Outcome', 'Without Outcome'],
              datasets: [{
                data: [overall.with_outcome, overall.without_outcome],
                backgroundColor: ['rgba(34,197,94,0.82)', 'rgba(143,138,168,0.35)'],
                borderWidth: 0,
              }],
            }}
            options={baseOptionsNoScale()}
            value={overall?.with_outcome != null && overall?.without_outcome != null && (overall.with_outcome + overall.without_outcome) > 0
              ? Math.round(overall.with_outcome / (overall.with_outcome + overall.without_outcome) * 100) + '%'
              : '—'}
            label="With Outcome"
            color="var(--accent)"
          />
        </ChartCard>
      </div>

      {activeMonths.map(m => {
        const mb = by_month?.[m]
        if (!mb) return null
        const s = mb.summary
        const monthColor = MONTH_CONFIG[m]?.color || 'var(--accent)'
        return <MonthSection key={m} m={m} mb={mb} s={s} monthColor={monthColor} />
      })}
    </div>
  )
}

function MonthSection({ m, mb, s, monthColor }) {
  const { statusDoughnut, delegateBar, specialityBar, budgetBar } = useMonthCharts(mb)

  return (
    <div>
      <SectionLabel tag={MONTH_CONFIG[m]?.label || m.toUpperCase()} text="Activity Plan vs Actual" monthColor={monthColor} large />

      <div className="kpi" style={{ marginBottom: 16 }}>
        <KpiCard label="Planned"        value={s?.total_planned} monthColor={monthColor} />
        <KpiCard label="Executed"       value={s?.executed} />
        <KpiCard label="Not Executed"   value={s?.not_executed} />
        <KpiCard label="Unplanned"      value={s?.unplanned} />
        <KpiCard label="Execution Rate" value={s?.execution_rate_pct != null ? s.execution_rate_pct.toFixed(1) + '%' : '—'} />

        <KpiCard label="With Outcome"   value={s?.with_outcome} />
        <KpiCard label="Actual Spent"   value={EUR(s?.actual_spent_eur)} />
      </div>

      <div className="grid-2" style={{ marginBottom: 16 }}>
        <ChartCard title="Execution Status" height="h250" monthColor={monthColor}>
          <DonutCenter
            data={statusDoughnut}
            options={baseOptionsNoScale()}
            value={s?.execution_rate_pct != null ? s.execution_rate_pct.toFixed(0) + '%' : '—'}
            label="Executed"
            color={monthColor}
          />
        </ChartCard>
        <ChartCard title="Activities by MR" sub="Stacked: Executed · Not Executed · Unplanned" height="h250" monthColor={monthColor}>
          <Bar data={delegateBar} options={baseOptions({ scales: { x: { stacked: true, ticks: { color: '#94a3b8', font: { size: 10 } }, grid: { color: 'rgba(226,232,240,0.8)' } }, y: { stacked: true, ticks: { color: '#94a3b8', font: { size: 11 } }, grid: { color: 'rgba(226,232,240,0.8)' } } } })} />
        </ChartCard>
      </div>

      <div className="grid-2" style={{ marginBottom: 16 }}>
        <ChartCard title="Activities by Speciality" height="h270" monthColor={monthColor}>
          <Bar data={specialityBar} options={baseOptions({ indexAxis: 'y' })} />
        </ChartCard>
        <ChartCard title="Planned vs Actual Budget by MR" height="h270" monthColor={monthColor}>
          <Bar data={budgetBar} options={baseOptions()} />
        </ChartCard>
      </div>

      <ActivityTable rows={mb.matched}          title="Executed Activities"    variant="executed"         />
      <ActivityTable rows={mb.planned_not_done} title="Planned — Not Executed" variant="planned_not_done" />
      <ActivityTable rows={mb.unplanned_done}   title="Unplanned Activities"   variant="unplanned"        />
    </div>
  )
}
