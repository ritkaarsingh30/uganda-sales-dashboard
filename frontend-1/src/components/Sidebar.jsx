import { MONTH_CONFIG } from '../utils/monthConfig.js'

const REPORT_TABS = [
  { key: 'prod', label: 'Products' },
  { key: 'del',  label: 'MRs' },
  { key: 'exp',  label: 'Expenses' },
  { key: 'act',  label: 'Activities' },
]

export default function Sidebar({ activeTab, onTabChange, availableMonths = [], collapsed, onToggleCollapsed, mobileOpen }) {
  return (
    <aside className={`sidebar ${collapsed ? 'collapsed' : ''} ${mobileOpen ? 'mobile-open' : ''}`}>
      <div className="brand">
        <div className="brand-mark">U</div>
        <div className="brand-text">
          <div className="brand-title">Uganda Sales</div>
          <div className="brand-sub">INSIGHTS · 2026</div>
        </div>
        <button
          className="sidebar-toggle"
          onClick={onToggleCollapsed}
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? '»' : '«'}
        </button>
      </div>

      <div className="nav-section">
        <button
          className={`nav-item ${activeTab === 'ov' ? 'active' : ''}`}
          onClick={() => onTabChange('ov')}
        >
          <span className="nav-dot" style={{ color: '#a78bfa' }} />
          <span className="nav-label">Overview</span>
        </button>
      </div>

      {availableMonths.length > 0 && (
        <div className="nav-section">
          <div className="nav-section-label">Months</div>
          {availableMonths.map(m => {
            const cfg = MONTH_CONFIG[m] || {}
            return (
              <button
                key={m}
                className={`nav-item ${activeTab === m ? 'active' : ''}`}
                onClick={() => onTabChange(m)}
              >
                <span className="nav-dot" style={{ color: cfg.color || '#fff' }} />
                <span className="nav-label">{cfg.label || m.toUpperCase()}</span>
              </button>
            )
          })}
        </div>
      )}

      <div className="nav-section">
        <div className="nav-section-label">Reports</div>
        {REPORT_TABS.map(t => (
          <button
            key={t.key}
            className={`nav-item ${activeTab === t.key ? 'active' : ''}`}
            onClick={() => onTabChange(t.key)}
          >
            <span className="nav-dot" style={{ color: '#14b8a6' }} />
            <span className="nav-label">{t.label}</span>
          </button>
        ))}
      </div>

      <div className="nav-section">
        <div className="nav-section-label">Reference</div>
        <button
          className={`nav-item ${activeTab === 'nom' ? 'active' : ''}`}
          onClick={() => onTabChange('nom')}
        >
          <span className="nav-dot" style={{ color: '#fbbf24' }} />
          <span className="nav-label">Team & Nomenclature</span>
        </button>
      </div>

      <div className="nav-spacer" />
      <div className="sidebar-foot">
        Pharma Sales Intelligence<br />FastAPI + React
      </div>
    </aside>
  )
}
