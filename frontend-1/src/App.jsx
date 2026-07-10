import { useState } from 'react'
import { FilterProvider } from './context/FilterContext.jsx'
import { useAvailableMonths } from './hooks/useDashboard.js'
import Sidebar    from './components/Sidebar.jsx'
import FilterBar  from './components/FilterBar.jsx'
import { MONTH_CONFIG } from './utils/monthConfig.js'

import OverviewTab    from './tabs/OverviewTab.jsx'
import MonthTab       from './tabs/MonthTab.jsx'
import ProductsTab    from './tabs/ProductsTab.jsx'
import DelegatesTab   from './tabs/DelegatesTab.jsx'
import ExpensesTab    from './tabs/ExpensesTab.jsx'
import ActivitiesTab  from './tabs/ActivitiesTab.jsx'
import NomenclatureTab from './tabs/NomenclatureTab.jsx'

const AGGREGATE_TABS = new Set(['ov', 'prod', 'del', 'exp', 'act'])

const TITLES = {
  ov:   { title: 'Overview',   sub: 'Sales performance across all loaded months' },
  prod: { title: 'Products',   sub: 'Revenue and units by product, across the selected period' },
  del:  { title: 'MRs',        sub: 'Field-force calls, orders and tour coverage' },
  exp:  { title: 'Expenses',   sub: 'Activity budget flow and spend by product' },
  act:  { title: 'Activities', sub: 'Planned vs executed field activities and ROI' },
  nom:  { title: 'Team & Nomenclature', sub: 'Reference data — MRs, products, territories' },
}

function Dashboard() {
  const { data: availableMonths = [] } = useAvailableMonths()
  const [activeTab, setActiveTab] = useState('ov')
  const [collapsed, setCollapsed] = useState(false)
  const [mobileNavOpen, setMobileNavOpen] = useState(false)

  const staticPanels = {
    ov:   <OverviewTab    />,
    prod: <ProductsTab    />,
    del:  <DelegatesTab   />,
    exp:  <ExpensesTab    />,
    act:  <ActivitiesTab  />,
    nom:  <NomenclatureTab />,
  }

  let panel = staticPanels[activeTab]
  const isMonthTab = !panel && availableMonths.includes(activeTab)
  if (isMonthTab) {
    panel = <MonthTab month={activeTab} />
  }

  const cfg = isMonthTab ? MONTH_CONFIG[activeTab] : null
  const heading = cfg
    ? { title: `${cfg.label} 2026`, sub: 'Monthly deep-dive — sales, MR performance, tour & visit tracking' }
    : (TITLES[activeTab] || { title: 'Dashboard', sub: '' })

  return (
    <FilterProvider availableMonths={availableMonths}>
      <div className="shell">
        <Sidebar
          activeTab={activeTab}
          onTabChange={(tab) => { setActiveTab(tab); setMobileNavOpen(false) }}
          availableMonths={availableMonths}
          collapsed={collapsed}
          onToggleCollapsed={() => setCollapsed(c => !c)}
          mobileOpen={mobileNavOpen}
        />
        {mobileNavOpen && <div className="sidebar-overlay" onClick={() => setMobileNavOpen(false)} />}
        <div className="main">
          <div className="topbar">
            <button className="mobile-nav-toggle" onClick={() => setMobileNavOpen(o => !o)} aria-label="Toggle navigation">
              ☰
            </button>
            <div>
              <div className="topbar-title">{heading.title}</div>
              <div className="topbar-sub">{heading.sub}</div>
            </div>
            <div className="topbar-right">
              <div className="month-dots">
                {availableMonths.map(m => (
                  <span key={m} className="dot" style={{ background: MONTH_CONFIG[m]?.color || 'var(--accent)' }} />
                ))}
                <span className="lbl">{availableMonths.length} month{availableMonths.length !== 1 ? 's' : ''} loaded</span>
              </div>
            </div>
          </div>
          {AGGREGATE_TABS.has(activeTab) && <FilterBar availableMonths={availableMonths} />}
          {panel || <div style={{ color: 'var(--muted)', padding: 40 }}>Loading...</div>}
        </div>
      </div>
    </FilterProvider>
  )
}

export default function App() {
  return <Dashboard />
}
