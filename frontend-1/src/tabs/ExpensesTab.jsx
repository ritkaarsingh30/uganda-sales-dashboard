import { Bar } from 'react-chartjs-2'
import { useExpenses } from '../hooks/useDashboard.js'
import { useFilter } from '../context/FilterContext.jsx'
import { baseOptions, PALETTE } from '../utils/chartConfig.js'
import { MONTH_CONFIG } from '../utils/monthConfig.js'
import KpiCard from '../components/KpiCard.jsx'
import ChartCard from '../components/ChartCard.jsx'
import SectionLabel from '../components/SectionLabel.jsx'

const UGX = n => n != null ? 'UGX ' + Math.round(n).toLocaleString() : '—'
const EUR = n => n != null ? '€' + n.toFixed(2) : '—'

export default function ExpensesTab() {
  const { data, isLoading } = useExpenses()
  const { activeMonths } = useFilter()

  if (isLoading) return <div style={{ color: 'var(--muted)', padding: 40 }}>Loading expenses...</div>
  if (!data) return null

  const { budget_flow, activity_type_totals, expenses_by_month } = data

  const visibleFlow = (budget_flow || []).filter(b =>
    activeMonths.some(m => (MONTH_CONFIG[m]?.short || m) === b.month || b.month?.toLowerCase().startsWith(m))
  )

  const lastFlow = [...(budget_flow || [])].sort(
    (a, b) => (MONTH_CONFIG[a.month?.toLowerCase().slice(0, 3)]?.monthNum || 0) -
      (MONTH_CONFIG[b.month?.toLowerCase().slice(0, 3)]?.monthNum || 0)
  ).at(-1)

  const totalBalance = lastFlow?.received_eur || 0

  const flowBar = {
    labels: (budget_flow || []).map(b => b.month),
    datasets: [
      { label: 'Received (EUR)', data: (budget_flow || []).map(b => b.received_eur), backgroundColor: PALETTE[0], borderRadius: 3 },
      { label: 'Spent (EUR)', data: (budget_flow || []).map(b => b.spent_eur), backgroundColor: PALETTE[3], borderRadius: 3 },

    ],
  }


  return (
    <div>
      <div className="kpi">

        <KpiCard label="Current Month Balance (EUR)" value={EUR(totalBalance)} />

      </div>

      <div>
        <ChartCard title="Budget Flow by Month (EUR)" height="h300">
          <Bar data={flowBar} options={baseOptions()} />
        </ChartCard>
      </div>

      {activeMonths.map(m => {
        const entries = expenses_by_month?.[m] || []
        if (!entries.length) return null

        const totalEUR = entries.reduce((a, r) => a + (r.amount_eur || 0), 0)
        const totalOutcome = entries.reduce((a, r) => {
          const v = Array.isArray(r.sales_outcome) ? r.sales_outcome.join(',') : r.sales_outcome
          const n = parseFloat(v)
          return a + (Number.isFinite(n) ? n : 0)
        }, 0)
        const monthCol = `var(--${m})`

        // Aggregate count + EUR per product
        // Filter out short prefix-tokens (e.g. "Bio" from "Bio Nerv") and numeric fragments
        const SKIP = new Set(['Bio', 'BIO', 'COQ', 'All', 'ALL', 'products', 'Products'])
        const productData = {}
        entries.forEach(r => {
          const prods = (r.products || '')
            .split(/[\s,]+/)
            .map(p => p.trim())
            .filter(p => p.length >= 4 && !SKIP.has(p) && !/^\d+$/.test(p))
          const eurShare = prods.length > 0 ? (r.amount_eur || 0) / prods.length : 0
          prods.forEach(p => {
            if (!productData[p]) productData[p] = { count: 0, eur: 0 }
            productData[p].count += 1
            productData[p].eur += eurShare
          })
        })
        const sorted = Object.entries(productData).sort((a, b) => b[1].count - a[1].count)
        const top = sorted.slice(0, 12)

        const productChartData = {
          labels: top.map(([p]) => p),
          datasets: [
            {
              label: 'Activities',
              data: top.map(([, d]) => d.count),
              backgroundColor: 'rgba(13,148,136,0.75)',
              borderColor: '#0d9488',
              borderWidth: 1,
              borderRadius: 4,
              borderSkipped: false,
              xAxisID: 'x',
            },
            {
              label: 'EUR Spent',
              data: top.map(([, d]) => +d.eur.toFixed(2)),
              backgroundColor: 'rgba(129,140,248,0.75)',
              borderColor: '#818cf8',
              borderWidth: 1,
              borderRadius: 4,
              borderSkipped: false,
              xAxisID: 'x1',
            },
          ],
        }

        // Dynamic height: ~36px per product row (two bars) + legend + axes
        const chartPx = Math.max(220, top.length * 38 + 80)

        const productChartOpts = {
          responsive: true,
          maintainAspectRatio: false,
          indexAxis: 'y',
          plugins: {
            legend: {
              position: 'top',
              labels: {
                color: '#64748b', font: { size: 11 },
                usePointStyle: true, pointStyle: 'rect',
                padding: 16, boxWidth: 12, boxHeight: 12,
              },
            },
            tooltip: {
              backgroundColor: '#1e293b',
              titleColor: '#f8fafc',
              bodyColor: '#cbd5e1',
              borderColor: '#334155',
              borderWidth: 1,
              cornerRadius: 8,
              padding: 10,
              callbacks: {
                label: ctx => ctx.dataset.xAxisID === 'x'
                  ? ` ${ctx.parsed.x} ${ctx.parsed.x === 1 ? 'activity' : 'activities'}`
                  : ` €${ctx.parsed.x.toFixed(2)} spent`,
              },
            },
          },
          scales: {
            x: {
              position: 'bottom',
              beginAtZero: true,
              ticks: {
                color: '#0d9488',
                font: { size: 10 },
                stepSize: 1,
                callback: v => Number.isInteger(v) ? v : '',
              },
              grid: { color: 'rgba(13,148,136,0.08)' },
              title: { display: true, text: 'Number of activities', color: '#0d9488', font: { size: 10 } },
            },
            x1: {
              position: 'top',
              beginAtZero: true,
              ticks: {
                color: '#818cf8',
                font: { size: 10 },
                callback: v => '€' + (v >= 100 ? Math.round(v) : v.toFixed(1)),
              },
              grid: { drawOnChartArea: false, color: 'rgba(129,140,248,0.08)' },
              title: { display: true, text: 'EUR Spent', color: '#818cf8', font: { size: 10 } },
            },
            y: {
              ticks: { color: '#334155', font: { size: 10, weight: '500' } },
              grid: { display: false },
            },
          },
        }

        return (
          <div key={m} style={{ marginBottom: 20 }}>
            <SectionLabel tag={MONTH_CONFIG[m]?.label || m.toUpperCase()} text="Activity Expenses" />

            {/* Product activity vs expense chart */}
            {top.length > 0 && (
              <div className="chart-card" style={{ borderTop: `2px solid ${monthCol}`, marginBottom: 12 }}>
                <div className="chart-title">Product Activity vs. Expense</div>
                <div className="chart-sub">
                  Activity count (teal · bottom axis) vs. EUR attributed to each product (purple · top axis)
                </div>
                <div style={{ height: chartPx }}>
                  <Bar data={productChartData} options={productChartOpts} />
                </div>
              </div>
            )}


            <div className="tbl-card" style={{ borderTop: `2px solid ${monthCol}` }}>
              <div className="tbl-header">
                <span className="tbl-title">Expenses — {MONTH_CONFIG[m]?.label || m}</span>
                <span className="badge n">{entries.length} entries · {EUR(totalEUR)}</span>
              </div>
              <div className="tbl-scroll">
<table>
                <thead>
                  <tr>
                    <th>#</th><th>Doctor</th><th>Hospital</th><th>Speciality</th>
                    <th>Activity Type</th><th>Products</th><th>Amount (EUR)</th><th>Visits</th><th>MR</th><th>Sales Outcome</th>
                  </tr>
                </thead>
                <tbody>
                  {entries.map((r, i) => (
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
                      <td style={{ fontSize: '0.75rem' }}>
                        {r.sales_outcome && r.sales_outcome !== '0' && r.sales_outcome !== 'nan'
                          ? <span style={{ color: 'var(--green)', fontWeight: 600 }}>{Array.isArray(r.sales_outcome) ? r.sales_outcome.join(', ') : r.sales_outcome}</span>
                          : <span style={{ color: 'var(--muted)' }}>—</span>}
                      </td>
                    </tr>
                  ))}
                  <tr className="tbl-footer-row">
                    <td colSpan={6} style={{ textAlign: 'right', color: 'var(--muted)' }}>Total</td>
                    <td style={{ fontFamily: 'var(--font-mono)' }}>{EUR(totalEUR)}</td>
                    <td colSpan={2} />
                    <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--green)', fontWeight: 600 }}>
                      {totalOutcome ? totalOutcome.toLocaleString() : '—'}
                    </td>
                  </tr>
                </tbody>
              </table>
</div>
            </div>
          </div>
        )
      })}
    </div>
  )
}
