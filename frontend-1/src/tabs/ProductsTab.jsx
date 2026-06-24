import { Bar } from 'react-chartjs-2'
import { useProducts, useOverview } from '../hooks/useDashboard.js'
import { useFilter } from '../context/FilterContext.jsx'
import { baseOptions, monthColor } from '../utils/chartConfig.js'
import { MONTH_CONFIG } from '../utils/monthConfig.js'
import KpiCard from '../components/KpiCard.jsx'
import ChartCard from '../components/ChartCard.jsx'
import DataTable from '../components/DataTable.jsx'

export default function ProductsTab() {
  const { data, isLoading } = useProducts()
  const { data: ov } = useOverview()
  const { activeMonths } = useFilter()

  if (isLoading) return <div style={{ color: 'var(--muted)', padding: 40 }}>Loading products...</div>
  if (!data) return null

  const { q1_kpis, q1_trend, annual_vs_q1 } = data
  const kpis = q1_kpis || {}

  // All products with a total > 0 across active months, sorted desc by total
  const allProducts = (q1_trend || [])
    .map(p => ({ ...p, total: activeMonths.reduce((a, m) => a + (p[m] || 0), 0) }))
    .filter(p => p.total > 0)
    .sort((a, b) => b.total - a.total)

  // Dynamic title: "Jan – Apr 2026 Revenue Trend"
  const sortedMonths = [...activeMonths].sort(
    (a, b) => (MONTH_CONFIG[a]?.monthNum || 0) - (MONTH_CONFIG[b]?.monthNum || 0)
  )
  const first = MONTH_CONFIG[sortedMonths[0]]?.short || ''
  const last  = MONTH_CONFIG[sortedMonths[sortedMonths.length - 1]]?.short || ''
  const rangeLabel = sortedMonths.length > 1
    ? `${first} – ${last} 2026 Revenue Trend`
    : sortedMonths.length === 1
      ? `${MONTH_CONFIG[sortedMonths[0]]?.label || ''} 2026 Revenue Trend`
      : 'Revenue Trend'

  // Grouped bar dataset — one dataset per active month
  const revenueGrouped = {
    labels: allProducts.map(p => p.product),
    datasets: activeMonths.map(m => ({
      label: MONTH_CONFIG[m]?.label || m.toUpperCase(),
      data: allProducts.map(p => +(p[m] || 0).toFixed(2)),
      backgroundColor: monthColor(m).alpha,
      borderColor: monthColor(m).solid,
      borderWidth: 1,
      borderRadius: 3,
      borderSkipped: false,
    })),
  }

  const revenueOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top',
        labels: {
          color: '#64748b',
          font: { size: 11 },
          usePointStyle: true,
          pointStyle: 'rect',
          padding: 18,
          boxWidth: 12,
          boxHeight: 12,
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
          label: ctx =>
            ` ${ctx.dataset.label}: €${ctx.parsed.y.toLocaleString(undefined, { maximumFractionDigits: 0 })}`,
        },
      },
    },
    scales: {
      x: {
        ticks: {
          color: '#64748b',
          font: { size: 9, weight: '500' },
          maxRotation: 45,
          minRotation: 30,
        },
        grid: { color: 'rgba(148,163,184,0.12)' },
      },
      y: {
        ticks: {
          color: '#94a3b8',
          font: { size: 10 },
          callback: v =>
            '€' + (v >= 1000 ? (v / 1000).toFixed(v % 1000 === 0 ? 0 : 1) + 'k' : v),
        },
        grid: { color: 'rgba(148,163,184,0.12)' },
        beginAtZero: true,
      },
    },
  }

  // Monthly sales vs target
  const visibleMonths = (ov?.month_comparison || []).filter(m => activeMonths.includes(m.key))
  const monthCompData = {
    labels: visibleMonths.map(m => MONTH_CONFIG[m.key]?.short || m.month),
    datasets: [
      {
        label: 'Sales (EUR)',
        data: visibleMonths.map(m => m.sales),
        backgroundColor: visibleMonths.map(m => monthColor(m.key).solid),
        borderRadius: 4,
      },
      {
        label: 'Target (EUR)',
        data: visibleMonths.map(m => m.projection),
        backgroundColor: 'rgba(148,163,184,0.4)',
        borderRadius: 4,
      },
    ],
  }

  const annualCols = [
    { key: 'product',       label: 'Product'             },
    { key: 'ytd_achieved',  label: 'YTD Sales (EUR)'     },
    { key: 'annual_target', label: 'Yearly Target (EUR)' },
  ]

  return (
    <div>
      {/* KPI row */}
      <div className="kpi">
        <KpiCard label="Total Sales (EUR)" value={'€' + Math.round(kpis.total_sales_eur || 0).toLocaleString()} />
        <KpiCard label="Total Units"       value={(kpis.total_units || 0).toLocaleString()} />
        {activeMonths.map(m => (
          <KpiCard
            key={m}
            label={`${MONTH_CONFIG[m]?.short || m} Sales`}
            value={'€' + Math.round(kpis.month_sales?.[m] || 0).toLocaleString()}
            monthColor={monthColor(m).solid}
          />
        ))}
      </div>

      {/* ── All-products grouped bar chart ── */}
      {allProducts.length > 0 ? (
        <ChartCard
          title={`All Products — ${rangeLabel}`}
          sub="Side-by-side comparison across all loaded months"
          height="h400"
        >
          <Bar data={revenueGrouped} options={revenueOptions} />
        </ChartCard>
      ) : (
        <div className="chart-card" style={{ color: 'var(--muted)', fontSize: '0.85rem', padding: 32, textAlign: 'center' }}>
          No product sales data for the selected months.
        </div>
      )}

      {/* Monthly sales vs target */}
      {visibleMonths.length > 0 && (
        <ChartCard
          title="Monthly Sales vs Target"
          sub="Actual sales compared to monthly projection — auto-updates as new months load"
          height="h300"
        >
          <Bar data={monthCompData} options={baseOptions()} />
        </ChartCard>
      )}

      {/* Table */}
      <DataTable
        title="Yearly Target vs YTD"
        badge={`${annual_vs_q1?.length || 0} products`}
        columns={annualCols}
        rows={annual_vs_q1 || []}
      />
    </div>
  )
}
