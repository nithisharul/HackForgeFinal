import { useEffect, useRef, useState } from 'react'
import { api } from '../api/client.js'
import { Icon, Tier, words } from './bits.jsx'

const typing = (e) => e.target.closest('input, textarea, select, [contenteditable="true"]')
const isMac = typeof navigator !== 'undefined' && /Mac|iPhone|iPad/.test(navigator.platform)
export const MOD = isMac ? '⌘' : 'Ctrl'

function go(hash) { window.location.hash = hash }
function askBrain() {
  if (window.location.hash.startsWith('#/brain')) return window.dispatchEvent(new Event('csn-ask'))
  try { sessionStorage.setItem('csn-ask', '1') } catch { /* private mode: the page still opens */ }
  go('#/brain/index')
}

// Command palette (Ctrl/Cmd+K): jump to any case or page by typing part of a name, ID, city or pattern.
// Shortcut sheet (?): every keyboard shortcut in the app.
export default function Palette() {
  const box = useRef(null)
  const help = useRef(null)
  const input = useRef(null)
  const [q, setQ] = useState('')
  const [cases, setCases] = useState(null)
  const [at, setAt] = useState(0)

  const open = () => {
    setQ(''); setAt(0)
    box.current?.showModal()
    api.queue(90, 3).then((d) => setCases(d.cases)).catch(() => setCases([]))
  }
  useEffect(() => {
    const on = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); box.current?.open ? box.current.close() : open() }
      else if (e.key === '?' && !typing(e) && !document.querySelector('dialog[open]')) { e.preventDefault(); help.current?.showModal() }
    }
    const show = () => open()
    document.addEventListener('keydown', on)
    window.addEventListener('csn-palette', show)
    return () => { document.removeEventListener('keydown', on); window.removeEventListener('csn-palette', show) }
  }, [])

  // Every typed word must appear somewhere, in any order: 'houston ring' finds ring cases in Houston.
  const needles = q.trim().toLowerCase().split(/\s+/).filter(Boolean)
  const has = (text) => needles.every((w) => text.toLowerCase().includes(w))
  const pages = [
    { key: 'queue', label: 'Case queue', icon: 'queue', run: () => go('#/queue') },
    { key: 'brain', label: 'Second Brain', icon: 'brain', run: () => go('#/brain/index') },
    { key: 'ask', label: 'Ask the Second Brain a question', icon: 'search', run: askBrain },
    { key: 'about', label: 'About ClaimShield', icon: 'home', run: () => go('#/') },
    { key: 'keys', label: 'Keyboard shortcuts', icon: 'command', run: () => help.current?.showModal() },
  ].filter((p) => has(p.label))
  const hits = (cases || [])
    .filter((c) => has([c.case_id, c.provider_id, c.provider_name, c.city, c.specialty, words(c.pattern), c.network && `network ${c.network}`].join(' ')))
    .slice(0, 8)
    .map((c) => ({ key: c.case_id, c, run: () => go(`#/case/${c.case_id}`) }))
  const items = [...hits, ...pages]
  const pick = (it) => { box.current.close(); it.run() }
  const keys = (e) => {
    if (e.key === 'ArrowDown') { e.preventDefault(); setAt((i) => Math.min(items.length - 1, i + 1)) }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setAt((i) => Math.max(0, i - 1)) }
    else if (e.key === 'Enter' && items[at]) { e.preventDefault(); pick(items[at]) }
  }
  useEffect(() => { document.getElementById(`pal-${at}`)?.scrollIntoView({ block: 'nearest' }) }, [at])

  return (
    <>
      <dialog ref={box} className="modal palette" aria-label="Go to" onClick={(e) => e.target === box.current && box.current.close()}>
        <div className="pal-search">
          <Icon name="search" />
          <input ref={input} autoFocus value={q} onChange={(e) => { setQ(e.target.value); setAt(0) }} onKeyDown={keys}
            placeholder="Search cases, providers, cities or pages" aria-label="Search" role="combobox" aria-expanded="true"
            aria-controls="pal-list" aria-activedescendant={items[at] ? `pal-${at}` : undefined} />
          <kbd>Esc</kbd>
        </div>
        <ul id="pal-list" role="listbox" className="pal-list">
          {hits.length > 0 && <li className="pal-group" role="presentation">Cases</li>}
          {items.map((it, i) => (
            <WithGroup key={it.key} first={i === hits.length && hits.length > 0}>
              <li id={`pal-${i}`} role="option" aria-selected={i === at} className={i === at ? 'on' : undefined}
                onMouseMove={() => setAt(i)} onClick={() => pick(it)}>
                {it.c ? (
                  <>
                    <span className="pal-rank">{it.c.rank}</span>
                    <span className="pal-main"><b>{it.c.provider_name}</b><small><span className="id">{it.c.case_id}</span>, <span className="cap">{words(it.c.pattern)}</span>, {it.c.city}</small></span>
                    {it.c.status === 'open' ? <Tier tier={it.c.tier} /> : <span className={`status status-${it.c.status}`}>{it.c.status}</span>}
                  </>
                ) : <><Icon name={it.icon} /><span className="pal-main">{it.label}</span></>}
              </li>
            </WithGroup>
          ))}
          {cases === null && <li className="pal-empty" role="presentation">Loading cases…</li>}
          {cases && items.length === 0 && <li className="pal-empty" role="presentation">Nothing matches “{q.trim()}”.</li>}
        </ul>
        <p className="pal-foot"><span><kbd>↑</kbd> <kbd>↓</kbd> to move</span><span><kbd>Enter</kbd> to open</span><span><kbd>?</kbd> all shortcuts</span></p>
      </dialog>

      <dialog ref={help} className="modal" aria-labelledby="keys-h" onClick={(e) => e.target === help.current && help.current.close()}>
        <div className="modal-body">
          <h3 id="keys-h">Keyboard shortcuts</h3>
          <button type="button" className="modal-x" aria-label="Close" onClick={() => help.current.close()}>×</button>
          <dl className="keys">
            {[[`${MOD} K`, 'Go to a case or page'], ['/', 'Search the case queue'], ['J  K', 'Next and previous case in the queue'],
              ['Enter', 'Open the selected case'], ['?', 'Show this list'], ['Esc', 'Close a dialog']].map(([k, v]) => (
              <div key={k}><dt>{k.split('  ').map((x) => <kbd key={x}>{x}</kbd>)}</dt><dd>{v}</dd></div>
            ))}
          </dl>
        </div>
      </dialog>
    </>
  )
}

// A group heading before the first page item, once there are case results above it.
function WithGroup({ first, children }) {
  return <>{first && <li className="pal-group" role="presentation">Pages</li>}{children}</>
}
