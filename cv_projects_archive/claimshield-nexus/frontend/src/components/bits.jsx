export const money = (x) => '$' + Math.round(x).toLocaleString('en-US')
export const pct = (x) => Math.round(x * 100) + '%'
export const words = (s) => (s || '').replace(/_/g, ' ')

const TIER_TEXT = { high: 'Fast-track', medium: 'Review', low: 'Not enough evidence' }

export function Tier({ tier }) {
  return <span className={`tier tier-${tier}`}>{TIER_TEXT[tier]}</span>
}

export function Status({ status }) {
  return <span className={`status status-${status}`}>{status}</span>
}

export function Meter({ value, tone = 'accent' }) {
  return (
    <span className="meter" title={pct(value)}>
      <span className={`meter-fill tone-${tone}`} style={{ width: `${Math.max(2, value * 100)}%` }} />
    </span>
  )
}

export function Loading({ error }) {
  if (error) {
    return (
      <div className="notice error">
        <strong>Could not reach the API.</strong> {error}
        <br />
        Start it from the project root with <code>uvicorn backend.app.main:app --reload</code>.
      </div>
    )
  }
  return <div className="notice">Loading…</div>
}

// Tiny renderer for wiki pages: headings, bullets, bold, code and [[wikilinks]].
function inline(text, key) {
  const parts = text.split(/(\[\[[^\]]+\]\]|\*\*[^*]+\*\*|`[^`]+`)/g)
  return parts.map((p, i) => {
    if (p.startsWith('[[')) {
      const name = p.slice(2, -2)
      return <a key={`${key}-${i}`} className="wikilink" href={`#/brain/${name}`}>{name}</a>
    }
    if (p.startsWith('**')) return <strong key={`${key}-${i}`}>{p.slice(2, -2)}</strong>
    if (p.startsWith('`')) return <code key={`${key}-${i}`}>{p.slice(1, -1)}</code>
    return p
  })
}

export function Markdown({ text }) {
  const out = []
  let list = []
  const flush = () => {
    if (list.length) out.push(<ul key={`ul-${out.length}`}>{list}</ul>)
    list = []
  }
  text.split('\n').forEach((line, i) => {
    if (line.startsWith('<!--') || !line.trim()) return flush()
    if (line.startsWith('- ')) return list.push(<li key={i}>{inline(line.slice(2), i)}</li>)
    flush()
    if (line.startsWith('## ')) out.push(<h3 key={i}>{line.slice(3)}</h3>)
    else if (line.startsWith('# ')) out.push(<h2 key={i}>{line.slice(2)}</h2>)
    else out.push(<p key={i}>{inline(line, i)}</p>)
  })
  flush()
  return <div className="md">{out}</div>
}
