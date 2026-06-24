import { Bar, Doughnut } from 'react-chartjs-2'
import { useMonth } from '../hooks/useDashboard.js'
import { baseOptions, baseOptionsNoScale, PALETTE } from '../utils/chartConfig.js'
import { MONTH_CONFIG } from '../utils/monthConfig.js'
import KpiCard from '../components/KpiCard.jsx'
import ChartCard from '../components/ChartCard.jsx'
import DataTable from '../components/DataTable.jsx'
import SectionLabel from '../components/SectionLabel.jsx'
import SalesOutcomeCell from '../components/SalesOutcomeCell.jsx'
import TourPlanSection from '../components/TourPlanSection.jsx'
import VisitTrackerSection from '../components/VisitTrackerSection.jsx'

const UGX = n => n != null ? 'UGX ' + Math.round(n).toLocaleString() : '—'
const EUR = n => n != null ? '€' + Math.round(n).toLocaleString() : '—'
const pct = n => n != null ? n.toFixed(1) + '%' : '—'

export default function MonthTab({ month }) {
  const { data: md, isLoading } = useMonth(month)
  const cfg = MONTH_CONFIG[month] || { label: month, color: 'var(--accent)', short: month }

  if (isLoading) return <div style={{ color: 'var(--muted)', padding: 40 }}>Loading {cfg.label}...</div>
  if (!md) return null

  const { kpis, product_sales, delegate_table, activity_expenses, tour_plan, visit_tracker } = md
  const color = cfg.color

  // Target vs Achieved per product
  const topProducts = [...(product_sales || [])].sort((a, b) => b.sales_eur - a.sales_eur)
  const targetBar = {
    labels: topProducts.map(p => p.product),
    datasets: [
      { label: 'Sales (EUR)', data: topProducts.map(p => p.sales_eur), backgroundColor: PALETTE[0] },
      { label: 'Target (EUR)', data: topProducts.map(p => p.target_eur), backgroundColor: 'rgba(148,163,184,0.4)' },
    ],
  }

  // Achievement rate per product (products with a target)
  const achievementProducts = [...(product_sales || [])]
    .filter(p => p.target_eur > 0)
    .sort((a, b) => (b.sales_eur / b.target_eur) - (a.sales_eur / a.target_eur))

  const achievementBar = {
    labels: achievementProducts.map(p => p.product),
    datasets: [{
      label: 'Achievement %',
      data: achievementProducts.map(p => +((p.sales_eur / p.target_eur) * 100).toFixed(1)),
      backgroundColor: achievementProducts.map(p => {
        const r = (p.sales_eur / p.target_eur) * 100
        return r >= 100 ? 'rgba(16,185,129,0.75)' : r >= 70 ? 'rgba(245,158,11,0.75)' : 'rgba(239,68,68,0.75)'
      }),
    }],
  }

  // Units sold per product
  const topByUnits = [...(product_sales || [])].sort((a, b) => b.units - a.units)
  const unitsBar = {
    labels: topByUnits.map(p => p.product),
    datasets: [{
      label: 'Units Sold',
      data: topByUnits.map(p => p.units),
      backgroundColor: color,
    }],
  }

  // Activity expense charts
  const expByMR = {}
  const expBySpec = {}
    ; (activity_expenses || []).forEach(r => {
      const mr = r.responsible || 'Unknown'
      const spec = r.speciality || 'Other'
      expByMR[mr] = (expByMR[mr] || 0) + (r.amount_eur || 0)
      expBySpec[spec] = (expBySpec[spec] || 0) + (r.amount_eur || 0)
    })
  const mrLabels = Object.keys(expByMR).sort((a, b) => expByMR[b] - expByMR[a])
  const specLabels = Object.keys(expBySpec).sort((a, b) => expBySpec[b] - expBySpec[a])
  const expByMRBar = {
    labels: mrLabels,
    datasets: [{
      label: 'Expense (EUR)',
      data: mrLabels.map(k => +expByMR[k].toFixed(2)),
      backgroundColor: PALETTE.slice(0, mrLabels.length),
    }],
  }
  const expBySpecDoughnut = {
    labels: specLabels,
    datasets: [{
      data: specLabels.map(k => +expBySpec[k].toFixed(2)),
      backgroundColor: PALETTE.slice(0, specLabels.length),
      borderWidth: 0,
    }],
  }

  const productCols = [
    { key: 'product', label: 'Product' },
    { key: 'units', label: 'Units Sold' },
    { key: 'target_units', label: 'Target Units' },
    { key: 'sales_eur', label: 'Sales (EUR)' },
    { key: 'target_eur', label: 'Target (EUR)' },
    { key: 'closing', label: 'Closing Stock' },
  ]

  const delegateCols = [
    { key: 'name', label: 'MR' },
    { key: 'territory', label: 'Territory' },
    { key: 'dr_in_list', label: 'DR List' },
    { key: 'listed_covered', label: 'Listed Cov.' },
    { key: 'pct_listed', label: '% Listed' },
    { key: 'prescriber', label: 'Prescribers Calls' },
    { key: 'non_prescriber', label: 'Non-Prescribers Calls' },
    { key: 'total_calls', label: 'Total Calls (Prescrber Calls + Non Prescriber Calls)' },
    { key: 'pharmacy', label: 'Pharmacy Calls' },
    { key: 'drs_converted', label: 'DRs Conv.' },
    { key: 'days_worked', label: 'Days' },
    { key: 'avg_per_day', label: 'Avg/Day' },
    { key: 'orders_eur', label: 'Orders (EUR)' },
    { key: 'ctc_eur', label: 'CTC (EUR)' },
    { key: 'ctc_ratio', label: 'CTC Ratio' },
  ]

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
        <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '1.4rem' }}>{cfg.label} 2026</h2>
        <span className={`badge ${kpis.achievement_pct >= 100 ? 'g' : kpis.achievement_pct >= 70 ? 'w' : 'd'}`}>
          {pct(kpis.achievement_pct)} Achievement
        </span>
      </div>

      <div className="kpi">
        <KpiCard label="Sales" value={EUR(kpis.total_sales_eur)} monthColor={color} />
        <KpiCard label="Target" value={EUR(kpis.total_target_eur)} />
        <KpiCard label="Achievement" value={pct(kpis.achievement_pct)} />

        <KpiCard label="Total Visits" value={((kpis.prescriber_calls ?? 0) + (kpis.non_prescriber_calls ?? 0)).toLocaleString()} />
        <KpiCard label="Prescriber Calls" value={kpis.prescriber_calls?.toLocaleString()} />
        <KpiCard label="Non Prescriber Calls" value={kpis.non_prescriber_calls?.toLocaleString()} />
        <KpiCard label="Pharmacy Calls" value={kpis.pharmacy_calls?.toLocaleString()} />
        <KpiCard label="DRs Converted" value={kpis.drs_converted?.toLocaleString()} />
        <KpiCard label="Opening Balance" value={EUR(kpis.opening_balance_eur)} />
        <KpiCard label="Activity Budget Spent" value={EUR(kpis.activity_spent_eur)} />
      </div>

      <ChartCard title="Target vs Sales by Product" height="h340" monthColor={color}>
        <Bar data={targetBar} options={baseOptions({ indexAxis: 'x' })} />
      </ChartCard>

      <div className="grid-2" style={{ marginBottom: 16 }}>
        <ChartCard title="Achievement Rate by Product" sub="Green ≥100% · Yellow ≥70% · Red <70%" height="h300" monthColor={color}>
          <Bar data={achievementBar} options={baseOptions({ indexAxis: 'y', scales: { x: { ticks: { color: '#94a3b8', font: { size: 11 }, callback: v => v + '%' }, grid: { color: 'rgba(226,232,240,0.8)' } }, y: { ticks: { color: '#94a3b8', font: { size: 10 }, autoSkip: false }, grid: { color: 'rgba(226,232,240,0.8)' } } } })} />
        </ChartCard>
        <ChartCard title="Units Sold by Product" height="h300" monthColor={color}>
          <Bar data={unitsBar} options={baseOptions({ indexAxis: 'y', scales: { x: { ticks: { color: '#94a3b8', font: { size: 11 } }, grid: { color: 'rgba(226,232,240,0.8)' } }, y: { ticks: { color: '#94a3b8', font: { size: 10 }, autoSkip: false }, grid: { color: 'rgba(226,232,240,0.8)' } } } })} />
        </ChartCard>
      </div>

      <DataTable
        title="Product Sales Detail"
        badge={`${product_sales?.length || 0} products`}
        borderColor={color}
        columns={productCols}
        rows={product_sales || []}
      />

      <SectionLabel tag="MR PERFORMANCE" monthColor={color} />
      <DataTable
        title="MR Table"
        badge={`${delegate_table?.length || 0} MRs`}
        borderColor={color}
        columns={delegateCols}
        rows={delegate_table || []}
      />

      {activity_expenses?.length > 0 && (
        <>
          <SectionLabel tag="ACTIVITY EXPENSES" monthColor={color} />
          <div className="grid-2" style={{ marginBottom: 16 }}>
            <ChartCard title="Expense by MR / Responsible" height="h250" monthColor={color}>
              <Bar data={expByMRBar} options={baseOptions({ indexAxis: mrLabels.length > 4 ? 'y' : 'x' })} />
            </ChartCard>
            <ChartCard title="Expense by Speciality" height="h250" monthColor={color}>
              <Doughnut data={expBySpecDoughnut} options={baseOptionsNoScale()} />
            </ChartCard>
          </div>
          <div className="tbl-card" style={{ borderTop: `2px solid ${color}` }}>
            <div className="tbl-header">
              <span className="tbl-title">Activity Expenses</span>
              <span className="badge n">{activity_expenses.length} entries</span>
            </div>
            <table>
              <thead>
                <tr>
                  <th>#</th><th>Doctor</th><th>Hospital</th><th>Speciality</th>
                  <th>Activity Type</th><th>Products</th><th>Amount (EUR)</th><th>Visits</th><th>Responsible</th>
                </tr>
              </thead>
              <tbody>
                {activity_expenses.map((r, i) => (
                  <tr key={i}>
                    <td style={{ color: 'var(--muted)' }}>{r.sn}</td>
                    <td>{r.doctor}</td>
                    <td style={{ color: 'var(--muted)', fontSize: '0.75rem' }}>{r.hospital}</td>
                    <td style={{ color: 'var(--muted)', fontSize: '0.75rem' }}>{r.speciality}</td>
                    <td style={{ color: 'var(--muted)', fontSize: '0.75rem' }}>{r.activity}</td>
                    <td style={{ fontSize: '0.75rem' }}>{r.products}</td>
                    <td style={{ fontFamily: 'var(--font-mono)' }}>{EUR(r.amount_eur)}</td>
                    <td>{r.num_visits}</td>
                    <td style={{ color: 'var(--muted)', fontSize: '0.75rem' }}>{r.responsible}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      <div style={{ marginTop: 24 }}>
        <TourPlanSection tourPlan={tour_plan} cfg={cfg} />
      </div>

      <div style={{ marginTop: 24 }}>
        <VisitTrackerSection visitTracker={visit_tracker} cfg={cfg} />
      </div>
    </div>
  )
}
