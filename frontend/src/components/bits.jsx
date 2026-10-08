import { useEffect, useState } from 'react'
import { getRegion } from '../region.js'

const INR = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 })
// Dollars as before; rupees in lakh and crore (1 lakh = 1,00,000; 1 crore = 100 lakh).
export const money = (x) => {
  if (getRegion() !== 'in') return '$' + Math.round(x).toLocaleString('en-US')
  const a = Math.abs(x)
  if (a >= 1e7) return `₹${(x / 1e7).toFixed(2)} crore`
  if (a >= 1e5) return `₹${(x / 1e5).toFixed(2)} lakh`
  return '₹' + INR.format(Math.round(x))
}
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
        <p>The server did not answer. Check your connection and try again.</p>
        {import.meta.env.DEV && <p><small>Dev: start the API from the project root with <code>uvicorn backend.app.main:app --reload</code>.</small></p>}
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

// Toasts: call toast('Saved') from anywhere; <Toaster /> in App shows them for a few seconds.
export const toast = (text) => window.dispatchEvent(new CustomEvent('csn-toast', { detail: text }))

export function Toaster() {
  const [items, setItems] = useState([])
  useEffect(() => {
    const on = (e) => {
      const id = Math.random()
      setItems((xs) => [...xs, { id, text: e.detail }])
      setTimeout(() => setItems((xs) => xs.filter((x) => x.id !== id)), 4000)
    }
    window.addEventListener('csn-toast', on)
    return () => window.removeEventListener('csn-toast', on)
  }, [])
  return <div className="toasts" role="status" aria-live="polite">{items.map((x) => <p key={x.id} className="toast">{x.text}</p>)}</div>
}
