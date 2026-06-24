export default function SectionLabel({ tag, text, monthColor, large }) {
  return (
    <div style={{ marginBottom: large ? 18 : 14 }}>
      <span className="section-label"
        style={{
          ...(monthColor ? { background: `${monthColor}22`, color: monthColor } : {}),
          ...(large ? { fontSize: '0.8rem', padding: '6px 14px' } : {}),
        }}>
        {tag || text}
      </span>
      {tag && text && (
        <span style={{ marginLeft: 10, fontSize: large ? '1.15rem' : '0.85rem', fontWeight: 700 }}>
          {text}
        </span>
      )}
    </div>
  )
}
