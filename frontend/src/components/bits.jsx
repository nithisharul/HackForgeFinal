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

// Shannon entropy of a yes/no probability: 0 bits is certain, 1 bit is a coin flip.
export const bits = (p) => (p <= 0 || p >= 1 ? 0 : -(p * Math.log2(p) + (1 - p) * Math.log2(1 - p)))
export function Doubt({ p, short }) {
  const b = bits(p)
  return (
    <small className={b > 0.8 ? 'doubt high' : 'doubt'} title="Uncertainty: 0 bits means certain, 1 bit means no better than a coin flip">
      {b.toFixed(2)} {short ? 'bits' : 'bits uncertain'}
    </small>
  )
}

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
    if (p === ' | ') return <span key={`${key}-${i}`} className="sep" aria-hidden="true"> / </span>
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

// Readouts tick up from zero once, when they first appear (instantly if reduced motion is on).
export function useCountUp(target, ms = 900) {
  const [n, setN] = useState(target)
  useEffect(() => {
    if (matchMedia('(prefers-reduced-motion: reduce)').matches) return setN(target)
    let raf
    const start = performance.now()
    const step = (now) => {
      const k = Math.min(1, (now - start) / ms)
      setN(Math.round(target * (1 - Math.pow(1 - k, 3))))
      if (k < 1) raf = requestAnimationFrame(step)
    }
    raf = requestAnimationFrame(step)
    return () => cancelAnimationFrame(raf)
  }, [target, ms])
  return n
}

// Brand mark: a shield with the highlighter stroke across it.
export function Logo() {
  return (
    <svg className="logo" viewBox="0 0 32 32" aria-hidden="true">
      <path className="logo-shield" d="M16 2.5 4.5 6.8v8.4c0 7.3 4.8 12.3 11.5 14.3 6.7-2 11.5-7 11.5-14.3V6.8L16 2.5Z" />
      <path className="logo-mark" d="M10 16.5h12" />
    </svg>
  )
}

// Line icons, 24px grid, drawn with currentColor.
const ICONS = {
  queue: 'M4 6h16M4 12h16M4 18h10',
  brain: 'M5 4.5h9.5L19 9v10.5H5zM14.5 4.5V9H19M8.5 13h7M8.5 16.5h5',
  home: 'M4 11 12 4l8 7v9h-5.5v-5.5h-5V20H4z',
  info: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18ZM12 11v5.5M12 7.6v.4',
  rank: 'M5 19V11M12 19V5M19 19v-5',
  brief: 'M6 3.5h8l4 4V20.5H6zM9 11h6M9 14.5h6M9 18h3.5',
  network: 'M12 6.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5ZM5 22a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5ZM19 22a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5ZM10.8 6 6.2 17.2M13.2 6l4.6 11.2M7.5 19.5h9',
  check: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18ZM8 12.2l2.8 2.8L16.2 9.5',
  learn: 'M4.5 12a7.5 7.5 0 0 1 13-5.1M19.5 12a7.5 7.5 0 0 1-13 5.1M17.5 3.5v3.4h-3.4M6.5 20.5v-3.4h3.4',
  export: 'M12 3.5v11M7.5 10 12 14.5 16.5 10M4.5 16.5v4h15v-4',
  shield: 'M12 3 4.5 6v5.5c0 4.8 3.2 8.1 7.5 9.5 4.3-1.4 7.5-4.7 7.5-9.5V6L12 3Z',
  print: 'M7 9V3.5h10V9M7 17.5H4.5v-8h15v8H17M7 14h10v6.5H7z',
  command: 'M9 6.5a2.5 2.5 0 1 0-2.5 2.5H9V6.5Zm0 0v11m0-11h6m-6 11a2.5 2.5 0 1 1-2.5-2.5H9v2.5Zm0 0h6m0-11a2.5 2.5 0 1 1 2.5 2.5H15V6.5Zm0 0v11m0 0a2.5 2.5 0 1 0 2.5-2.5H15v2.5Z',
  search: 'M10.5 17.5a7 7 0 1 0 0-14 7 7 0 0 0 0 14ZM15.5 15.5 20.5 20.5',
}
export function Icon({ name }) {
  return <svg className="icon" viewBox="0 0 24 24" aria-hidden="true"><path d={ICONS[name]} /></svg>
}

const REGIONS = [['us', 'US'], ['in', 'India']]
export function RegionSwitch({ region, onSwitch }) {
  return (
    <div className="region" role="group" aria-label="Region">
      {REGIONS.map(([r, label]) => (
        <button type="button" key={r} className={r === region ? 'on' : ''} aria-pressed={r === region} onClick={() => onSwitch(r)}>{label}</button>
      ))}
    </div>
  )
}
