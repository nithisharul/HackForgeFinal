export const money = (x) => '$' + Math.round(x).toLocaleString('en-US')
export const pct = (x) => Math.round(x * 100) + '%'
export const words = (s) => (s || '').replace(/_/g, ' ')

export const TIER_TEXT = { high: 'Fast-track', medium: 'Review', low: 'Not enough evidence' }

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

export function Loading({ error, what = 'this page', onRetry }) {
  if (error) {
    return (
      <div className="notice error" role="alert">
        <strong>Could not load {what}.</strong> {error}
        <p>Check that the API is running from the project root with <code>uvicorn backend.app.main:app --reload</code>, then try again.</p>
        <button type="button" className="btn" onClick={onRetry || (() => window.location.reload())}>Try again</button>
      </div>
    )
  }
  return (
    <div className="skeleton" role="status" aria-label={`Loading ${what}`}>
      <span className="sk sk-title" /><span className="sk sk-line" /><span className="sk sk-line short" />
      <span className="sk sk-block" />
    </div>
  )
}

// Tiny renderer for wiki pages: headings, bullets, bold, code and [[wikilinks]].
function inline(text, key) {
  const parts = text.split(/(\[\[[^\]]+\]\]|\*\*[^*]+\*\*|`[^`]+`| \| )/g)
  return parts.map((p, i) => {
    if (p === ' | ') return <span key={`${key}-${i}`} className="sep"> · </span>
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
  let compact = true
  const flush = () => {
    // Lists of bare IDs (e.g. the provider index) read better as a grid than a long column.
    if (list.length) out.push(<ul key={`ul-${out.length}`} className={compact && list.length > 6 ? 'compact' : undefined}>{list}</ul>)
    list = []
    compact = true
  }
  text.split('\n').forEach((line, i) => {
    if (line.startsWith('<!--') || !line.trim()) return flush()
    if (line.startsWith('- ')) {
      const item = line.slice(2)
      if (item.length > 16) compact = false
      return list.push(<li key={i}>{inline(item, i)}</li>)
    }
    flush()
    if (line.startsWith('## ')) out.push(<h3 key={i}>{line.slice(3)}</h3>)
    else if (line.startsWith('# ')) out.push(<h2 key={i}>{line.slice(2)}</h2>)
    else out.push(<p key={i}>{inline(line, i)}</p>)
  })
  flush()
  return <div className="md">{out}</div>
}
