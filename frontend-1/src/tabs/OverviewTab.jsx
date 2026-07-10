import { Bar, Line } from 'react-chartjs-2'
import { useOverview, useInsights, useRefreshData, useRefreshInsights } from '../hooks/useDashboard.js'
import { useFilter } from '../context/FilterContext.jsx'
import { baseOptions, monthColor, PALETTE, gradientFill } from '../utils/chartConfig.js'
import { MONTH_CONFIG } from '../utils/monthConfig.js'
import KpiCard from '../components/KpiCard.jsx'
import ChartCard from '../components/ChartCard.jsx'
import InsightBox from '../components/InsightBox.jsx'
import SectionLabel from '../components/SectionLabel.jsx'

function fmt(n) { return n != null ? '€' + Math.round(n).toLocaleString() : '—' }
function fmtPct(n) { return n != null ? n.toFixed(1) + '%' : '—' }

export default function OverviewTab() {
  const { data: ov, isLoading } = useOverview()
  const { data: ins, isLoading: insLoading } = useInsights()
  const { mutate: refreshData, isPending: refreshing } = useRefreshData()
  const { mutate: refreshInsights, isPending: insRefreshing } = useRefreshInsights()
  const { activeMonths } = useFilter()

  if (isLoading) return <div style={{ color: 'var(--muted)', padding: 40 }}>Loading overview...</div>
  if (!ov) return null

  const { q1_summary: s, month_comparison: mc, product_mix, all_products_trend, months_loaded } = ov
  const visibleMonths = (mc || []).filter(m => activeMonths.includes(m.key))

  // Month comparison bar chart
  const monthCompData = {
    labels: visibleMonths.map(m => MONTH_CONFIG[m.key]?.short || m.month),
    datasets: [
      { label: 'Sales (EUR)', data: visibleMonths.map(m => m.sales), backgroundColor: visibleMonths.map(m => monthColor(m.key).alpha), borderRadius: 6, borderSkipped: false },
      { label: 'Target (EUR)', data: visibleMonths.map(m => m.projection), backgroundColor: 'rgba(143,138,168,0.30)', borderRadius: 6, borderSkipped: false },
    ],
  }

  const baseChartOptions = baseOptions()
  const monthCompOptions = {
    ...baseChartOptions,
    plugins: {
      ...baseChartOptions.plugins,
      tooltip: {
        ...baseChartOptions.plugins.tooltip,
        callbacks: { label: (ctx) => `${ctx.dataset.label}: ${fmt(ctx.parsed.y)}` },
      },
    },
  }

  // All products, sorted by total sales across active months
  const allProdsSorted = (all_products_trend || [])
    .map(p => ({ ...p, total: activeMonths.reduce((a, m) => a + (p[m] || 0), 0) }))
    .sort((a, b) => b.total - a.total)

  // KPI figures scoped to the selected months
  const sortedActive = [...activeMonths].sort(
    (a, b) => (MONTH_CONFIG[a]?.monthNum || 0) - (MONTH_CONFIG[b]?.monthNum || 0)
  )
  const filteredSales  = sortedActive.reduce((a, m) => a + (s.month_sales?.[m] || 0), 0)
  const filteredVisits = sortedActive.reduce((a, m) => a + (s.total_visits?.[m] || 0), 0)
  const filteredDrs    = sortedActive.reduce((a, m) => a + (s.drs_converted?.[m] || 0), 0)
  const achievementPct = s.annual_target_eur ? (filteredSales / s.annual_target_eur) * 100 : 0
  const topProduct     = allProdsSorted[0]

  let filteredMomEur = null, filteredMomPct = null, filteredMomVisitsPct = null
  if (sortedActive.length >= 2) {
    const prevM = sortedActive[sortedActive.length - 2]
    const latestM = sortedActive[sortedActive.length - 1]
    const prevSales = s.month_sales?.[prevM] || 0
    const latestSales = s.month_sales?.[latestM] || 0
    filteredMomEur = latestSales - prevSales
    filteredMomPct = prevSales ? ((latestSales - prevSales) / prevSales) * 100 : null
    const prevVisits = s.total_visits?.[prevM] || 0
    const latestVisits = s.total_visits?.[latestM] || 0
    filteredMomVisitsPct = prevVisits ? ((latestVisits - prevVisits) / prevVisits) * 100 : null
  }

  const trendData = {
    labels: allProdsSorted.map(p => p.product),
    datasets: activeMonths.map((m, i) => ({
      label: MONTH_CONFIG[m]?.short || m.toUpperCase(),
      data: allProdsSorted.map(p => p[m] || 0),
      borderColor: monthColor(m).solid,
      backgroundColor: gradientFill(monthColor(m).solid, 0.32, 0.01),
      borderWidth: 2.5,
      pointRadius: 3,
      pointBackgroundColor: monthColor(m).solid,
      pointBorderWidth: 0,
      tension: 0.35,
      fill: true,
    })),
  }

  return (
    <div>
      <div className="kpi">
        <KpiCard
          label="Total Sales"
          value={fmt(filteredSales)}
          sub={`${sortedActive.length} month(s)`}
          change={filteredMomPct != null ? filteredMomPct.toFixed(1) + '%' : null}
          changeDir={filteredMomPct != null ? (filteredMomPct >= 0 ? 'up' : 'dn') : null}
        />
        <KpiCard label="Annual Target" value={fmt(s.annual_target_eur)} />
        <KpiCard label="Achievement" value={fmtPct(achievementPct)} sub="vs full-year target" />
        {filteredMomEur != null && (
          <KpiCard
            label="MoM Growth"
            value={(filteredMomEur >= 0 ? '+' : '') + fmt(filteredMomEur)}
            sub="latest vs prev selected month"
            change={filteredMomPct != null ? filteredMomPct.toFixed(1) + '%' : null}
            changeDir={filteredMomPct != null ? (filteredMomPct >= 0 ? 'up' : 'dn') : null}
          />
        )}
        <KpiCard
          label="Total Visits"
          value={filteredVisits.toLocaleString()}
          sub={`across ${sortedActive.length} month(s)`}
          change={filteredMomVisitsPct != null ? filteredMomVisitsPct.toFixed(1) + '%' : null}
          changeDir={filteredMomVisitsPct != null ? (filteredMomVisitsPct >= 0 ? 'up' : 'dn') : null}
        />
        <KpiCard label="DRs Converted" value={filteredDrs.toLocaleString()} sub={`across ${sortedActive.length} month(s)`} />
        <KpiCard label="Top Product" value={topProduct?.product} sub={fmt(topProduct?.total)} />
      </div>

      <ChartCard title="Sales vs Target by Month" height="h300">
        <Bar data={monthCompData} options={monthCompOptions} />
      </ChartCard>
      <ChartCard title="All Products — Sales (EUR)" height={`${Math.max(300, allProdsSorted.length * 28)}px`}>
        <Bar
          data={{
            labels: allProdsSorted.map(p => p.product),
            datasets: [{ label: 'Sales EUR', data: allProdsSorted.map(p => p.total), backgroundColor: allProdsSorted.map((_, i) => PALETTE[i % PALETTE.length]), borderRadius: 6, borderSkipped: false }],
          }}
          options={baseOptions({ indexAxis: 'y', plugins: { legend: { display: false } } })}
        />
      </ChartCard>


      {activeMonths.length > 0 && allProdsSorted.length > 0 && (
        <ChartCard title="Product Sales Trend" sub="All products across months" height={`${Math.max(340, allProdsSorted.length * 34)}px`}>
          <Line data={trendData} options={baseOptions()} />
        </ChartCard>
      )}

      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        <button className="btn" onClick={() => refreshData()} disabled={refreshing}>
          {refreshing ? 'Refreshing...' : 'Refresh Data'}
        </button>
        <button className="btn" onClick={() => refreshInsights()} disabled={insRefreshing}>
          {insRefreshing ? 'Generating...' : 'Refresh AI Insights'}
        </button>
      </div>

      <SectionLabel tag="AI INSIGHTS" />
      {(ins?.insights || []).length === 0 && !insLoading ? (
        <div className="insight-box info"><div className="insight-title">No insights available — set GROQ_API_KEY to enable.</div></div>
      ) : (
        (ins?.insights || []).map((ins, i) => (
          <InsightBox key={i} type={ins.type} icon={ins.icon} title={ins.title} text={ins.text} loading={insLoading} />
        ))
      )}

      <SectionLabel tag="MONTH-WISE DEEP COMPARISON" style={{ marginTop: 20 }} />
      {visibleMonths.length > 0 && (
        <div className="mdc-grid">
          {visibleMonths.map(m => {
            const cfg   = MONTH_CONFIG[m.key]
            const color = monthColor(m.key).solid
            const ach   = m.achievement
            const achCls = ach >= 90 ? 'good' : ach >= 60 ? 'warn' : 'danger'
            return (
              <div key={m.key} className="mdc-card">
                <div className="mdc-header">
                  <span className="mdc-dot" style={{ background: color }} />
                  <span className="mdc-month-name" style={{ color }}>{cfg?.label || m.month}</span>
                </div>
                <div className="mdc-body">
                  <div className="mdc-row"><span className="mdc-label">Sales</span><span className="mdc-val">€{Math.round(m.sales).toLocaleString()}</span></div>
                  <div className="mdc-row"><span className="mdc-label">Projection</span><span className="mdc-val" style={{ color: 'var(--muted)' }}>€{Math.round(m.projection).toLocaleString()}</span></div>
                  <div className="mdc-row"><span className="mdc-label">Achievement</span><span className={`mdc-val ${achCls}`}>{ach.toFixed(1)}%</span></div>
                  <div className="mdc-row"><span className="mdc-label">Total Visits</span><span className="mdc-val">{m.visits?.toLocaleString()}</span></div>
                  <div className="mdc-row"><span className="mdc-label">Prescriber Calls</span><span className="mdc-val">{m.prescriber_calls?.toLocaleString()}</span></div>
                  <div className="mdc-row"><span className="mdc-label">Pharmacy Calls</span><span className="mdc-val">{m.pharmacy_calls?.toLocaleString()}</span></div>
                  <div className="mdc-row"><span className="mdc-label">DRs Converted</span><span className={`mdc-val ${m.drs_converted > 0 ? 'good' : 'danger'}`}>{m.drs_converted}</span></div>
                  <div className="mdc-row"><span className="mdc-label">Active MRs</span><span className="mdc-val">{m.active_mrs ?? '—'}</span></div>
                  <div className="mdc-row"><span className="mdc-label">Activity Spent</span><span className="mdc-val">€{m.activity_spent_eur != null ? m.activity_spent_eur.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '—'}</span></div>
                  <div className="mdc-row"><span className="mdc-label">Top Product</span><span className="mdc-val top-prod">{m.top_product || '—'}</span></div>
                </div>
              </div>
            )
          })}
        </div>
      )}

      <SectionLabel tag="MONTH SUMMARY" style={{ marginTop: 20 }} />
      {visibleMonths.length > 0 && (
        <div className="tbl-card">
          <div className="tbl-scroll">
<table>
            <thead>
              <tr>
                <th>Month</th><th>Sales (EUR)</th><th>Target (EUR)</th><th>Achievement</th>
                <th>Growth</th><th>Visits</th><th>DRs Conv.</th><th>Top Product</th>
              </tr>
            </thead>
            <tbody>
              {visibleMonths.map(m => (
                <tr key={m.key}>
                  <td><span className="badge j">{MONTH_CONFIG[m.key]?.short || m.month}</span></td>
                  <td style={{ fontFamily: 'var(--font-mono)' }}>€{Math.round(m.sales).toLocaleString()}</td>
                  <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--muted)' }}>€{Math.round(m.projection).toLocaleString()}</td>
                  <td>
                    <span className={`badge ${m.achievement >= 100 ? 'g' : m.achievement >= 70 ? 'w' : 'd'}`}>
                      {m.achievement.toFixed(1)}%
                    </span>
                  </td>
                  <td>
                    {m.growth_pct != null
                      ? <span className={`badge ${m.growth_pct >= 0 ? 'g' : 'd'}`}>{m.growth_pct >= 0 ? '+' : ''}{m.growth_pct.toFixed(1)}%</span>
                      : <span style={{ color: 'var(--muted)' }}>—</span>
                    }
                  </td>
                  <td>{m.visits}</td>
                  <td>{m.drs_converted}</td>
                  <td style={{ color: 'var(--muted)', fontSize: '0.75rem' }}>{m.top_product}</td>
                </tr>
              ))}
            </tbody>
          </table>
</div>
        </div>
      )}
    </div>
  )
}
