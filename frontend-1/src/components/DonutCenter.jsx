import { Doughnut } from 'react-chartjs-2'

export default function DonutCenter({ data, options, value, label, color }) {
  return (
    <div style={{ position: 'relative', height: '100%' }}>
      <Doughnut data={data} options={{ cutout: '68%', ...options }} />
      {value != null && (
        <div style={{
          position: 'absolute', top: '46%', left: '50%',
          transform: 'translate(-50%, -50%)', textAlign: 'center', pointerEvents: 'none',
        }}>
          <div style={{ fontFamily: 'var(--font-display)', fontSize: '1.5rem', fontWeight: 800, color: color || 'var(--accent)' }}>
            {value}
          </div>
          {label && (
            <div style={{ fontSize: '0.62rem', color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginTop: 2 }}>
              {label}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
