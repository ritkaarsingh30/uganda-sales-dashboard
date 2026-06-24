export default function InsightBox({ type = 'info', icon, title, text, loading }) {
  if (loading) {
    return (
      <div className="insight-box info" style={{ opacity: 0.5 }}>
        <div className="insight-title">Generating insights...</div>
        <div className="insight-text">Please wait.</div>
      </div>
    )
  }
  return (
    <div className={`insight-box ${type}`}>
      <div className="insight-title">
        {icon && <span style={{ marginRight: 8 }}>{icon}</span>}
        <span style={{ textTransform: 'uppercase', letterSpacing: '0.05em', fontSize: '0.72rem', fontWeight: 700 }}>{title}</span>
      </div>
      {text && text !== title && (
        <div className="insight-text" style={{ marginTop: 6, lineHeight: 1.6 }}>{text}</div>
      )}
    </div>
  )
}
