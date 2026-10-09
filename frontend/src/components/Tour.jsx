import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { terms } from '../region.js'

// Guided walkthrough of the live app for the presentation, in the case page's Gutenberg order. Each step opens a route, waits for one element,
// and dims everything else so the audience looks where the presenter is talking. The app stays fully usable:
// clicks pass through, and Esc ends the walkthrough where it is.
const KEY = 'csn-tour'
const read = () => { try { return JSON.parse(sessionStorage.getItem(KEY)) } catch { return null } }
const write = (v) => { try { v ? sessionStorage.setItem(KEY, JSON.stringify(v)) : sessionStorage.removeItem(KEY) } catch { /* storage blocked: the tour still runs this visit */ } }

export function startTour(caseId) {
  write({ caseId, i: 0 })
  window.dispatchEvent(new Event('csn-tour'))
}

function steps(caseId) {
  const t = terms()
  const c = `#/case/${caseId}`
  return [
    { route: '#/queue', sel: '.kpis', title: 'This week, in four numbers',
      text: `Every claim scored, every alert grouped into a case per ${t.provider}, and how many cases the team can take this week.` },
    { route: '#/queue', sel: 'tr.capacity-line', title: 'The capacity line',
      text: 'Cases above the line fit this week with 3 investigators, 5 cases each. Change the team size and the line moves.' },
    { route: c, sel: '.pod-identity', title: 'Subject identity',
      text: 'Top left, where reading starts: who, where, the money at stake on a log ruler, and how many claims were flagged.' },
    { route: c, sel: '.pod-confidence', title: 'Algorithmic confidence',
      text: 'Top right: each probability is drawn as its distance from a coin flip, with the uncertainty in bits and how many of the 3 methods agree.' },
    { route: c, sel: '#pod-forensic + section', title: 'Forensic discrepancy',
      text: 'Then the reading path: the most damning claim as two records and the gap between them. Red appears only when a claim is logically impossible.' },
    { route: c, sel: '.sec.record', optional: true, title: 'Provider record review',
      text: 'A returned record laid out as one timeline. The LLM compares it with the flagged claims and marks the conflict for a human to judge.' },
    { route: c, sel: '.plan', optional: true, title: 'What to check next',
      text: 'AuditNext ranks checks by doubt removed per hour. The gain in bits sits beside the cost, so the ranking can be checked at a glance.' },
    { route: c, sel: '#verdict', title: 'The investigator decides',
      text: 'A verdict needs a reason, a preview of every page it will change, and a signed-in approver. It then becomes precedent.' },
    { route: '#/security', sel: '.integrity', title: 'Tamper check, live',
      text: 'Every approved change is signed into a hash chain. Every knowledge file is compared with it on each check; an edit made outside the app is named here in red.' },
  ]
}

// Resolves as soon as the element is in the page (pages load their data first): a MutationObserver, not polling.
function waitFor(sel, ms = 6000) {
  return new Promise((resolve) => {
    const found = () => { const el = document.querySelector(sel); return el && el.getBoundingClientRect().height > 0 ? el : null }
    const now = found()
    if (now) return resolve(now)
    const done = (el) => { mo.disconnect(); clearTimeout(timer); resolve(el) }
    const mo = new MutationObserver(() => { const el = found(); if (el) done(el) })
    const timer = setTimeout(() => done(found()), ms)
    mo.observe(document.body, { childList: true, subtree: true })
  })
}

const typing = (e) => e.target.closest('input, textarea, select, [contenteditable="true"]')
const PAD = 8
// A zero-size spotlight at the centre of the screen: everything dimmed, used while a new page loads.
const closed = () => ({ top: innerHeight / 2, left: innerWidth / 2, width: 0, height: 0, glide: false })

export default function Tour() {
  const [state, setState] = useState(read)
  const [box, setBox] = useState(closed)  // the spotlight; glide = animate this change
  const [missing, setMissing] = useState(false)
  const card = useRef(null)
  const el = useRef(null)
  const dir = useRef(1)
  const [cardPos, setCardPos] = useState(null)

  useEffect(() => {
    const on = () => setState(read())
    window.addEventListener('csn-tour', on)
    return () => window.removeEventListener('csn-tour', on)
  }, [])

  // While it runs, the page is marked so the scrollbar dims with everything else.
  useEffect(() => {
    document.documentElement.classList.toggle('touring', Boolean(state))
    return () => document.documentElement.classList.remove('touring')
  }, [Boolean(state)])

  const list = state ? steps(state.caseId) : []
  const step = state && list[state.i]

  const set = (v) => { write(v); setState(v) }
  const end = () => { set(null); setBox(closed()); el.current = null }
  // After the last step the presentation continues on the landing page, at the slide after the live demo.
  const finish = () => {
    end()
    try { sessionStorage.setItem('csn-deck-resume', 'ring') } catch { /* the landing page still opens */ }
    window.location.hash = '#/'
  }
  const move = (d) => {
    if (!state) return
    dir.current = d
    const i = state.i + d
    if (i < 0) return
    if (i >= list.length) return finish()
    set({ ...state, i })
  }

  // Open the step's route, find its element, bring it into view, then move the spotlight there once.
  // Same page: the spotlight stays where it was and glides to the new part after the page has jumped (nothing to chase).
  // New page: it closes to the centre (everything dimmed) and opens onto the new part when that has loaded.
  useEffect(() => {
    if (!step) return
    let live = true
    setMissing(false); el.current = null
    if (window.location.hash.split('?')[0] !== step.route) {
      setBox(closed())
      window.location.hash = step.route
    }
    // Optional parts sit on a page that is already loaded, so they are skipped quickly when absent.
    waitFor(step.sel, step.optional ? 1500 : 6000).then((found) => {
      if (!live) return
      if (!found) {
        if (step.optional) return move(dir.current)
        return setMissing(true)
      }
      el.current = found
      const tall = found.getBoundingClientRect().height > window.innerHeight * 0.6
      found.scrollIntoView({ block: tall ? 'start' : 'center', behavior: 'auto' })
      place(true)
    })
    return () => { live = false }
  }, [state?.i, state?.caseId])

  // A glide lasts its full 0.42 s: a late scroll or layout event during it updates the target without cutting it short.
  const glideUntil = useRef(0)
  const place = (glide) => {
    const r = el.current?.getBoundingClientRect()
    if (!r) return
    if (glide && !matchMedia('(prefers-reduced-motion: reduce)').matches) glideUntil.current = performance.now() + 450
    setBox({ top: r.top - PAD, left: r.left - PAD, width: r.width + PAD * 2, height: r.height + PAD * 2, glide: performance.now() < glideUntil.current })
  }
  // While the page scrolls, the spotlight follows exactly (no transition), at most once per frame.
  const frame = useRef(0)
  const measure = () => {
    if (frame.current) return
    frame.current = requestAnimationFrame(() => { frame.current = 0; place(false) })
  }
  useEffect(() => {
    if (!state) return
    window.addEventListener('scroll', measure, { capture: true, passive: true })
    window.addEventListener('resize', measure, { passive: true })
    return () => { window.removeEventListener('scroll', measure, true); window.removeEventListener('resize', measure) }
  }, [state])

  // The caption sits below the highlight when there is room, else above, else inside the bottom of the screen.
  useLayoutEffect(() => {
    const c = card.current
    if (!c) return
    const w = c.offsetWidth, h = c.offsetHeight, vw = window.innerWidth, vh = window.innerHeight, gap = 14
    if (!box.width) return setCardPos({ left: (vw - w) / 2, top: (vh - h) / 2 })
    let top = box.top + box.height + gap
    if (top + h > vh - 12) top = box.top - h - gap
    if (top < 12) top = vh - h - 16
    const left = Math.min(vw - w - 12, Math.max(12, box.left))
    setCardPos({ left, top })
  }, [box, state?.i, missing])

  useEffect(() => {
    if (!state) return
    const keys = (e) => {
      if (e.ctrlKey || e.metaKey || e.altKey || typing(e) || document.querySelector('dialog[open]')) return
      if (['ArrowRight', 'ArrowDown', 'PageDown', ' ', 'Enter'].includes(e.key)) { e.preventDefault(); e.stopPropagation(); move(1) }
      else if (['ArrowLeft', 'ArrowUp', 'PageUp'].includes(e.key)) { e.preventDefault(); e.stopPropagation(); move(-1) }
      else if (e.key === 'Escape') { e.preventDefault(); end() }
    }
    document.addEventListener('keydown', keys, true)
    return () => document.removeEventListener('keydown', keys, true)
  }, [state])

  if (!step) return null
  return (
    <div className="tour" role="dialog" aria-modal="false" aria-labelledby="tour-h" aria-describedby="tour-p">
      <div className={box.glide ? 'tour-spot glide' : 'tour-spot'} style={{ width: box.width, height: box.height, transform: `translate(${box.left}px, ${box.top}px)` }} aria-hidden="true" />
      {box.width > 0 && el.current && <div key={state.i} className="tour-ring" style={{ width: box.width, height: box.height, transform: `translate(${box.left}px, ${box.top}px)` }} aria-hidden="true" />}
      <div ref={card} className={box.glide ? 'tour-card glide' : 'tour-card'} style={cardPos && (el.current || missing) ? { transform: `translate(${cardPos.left}px, ${cardPos.top}px)` } : { visibility: 'hidden' }}>
        <p className="pod-label">Live walkthrough <span className="tour-n">{state.i + 1} / {list.length}</span></p>
        <div key={state.i} className="tour-text">
          <h3 id="tour-h">{step.title}</h3>
          <p id="tour-p">{missing ? 'This part is not on screen right now. Continue to the next step.' : step.text}</p>
        </div>
        <div className="tour-btns">
          <button type="button" className="top-btn" onClick={end}>End walkthrough</button>
          <span>
            {state.i > 0 && <button type="button" className="btn" onClick={() => move(-1)}>Back</button>}
            <button type="button" className="btn primary" onClick={() => move(1)} autoFocus>{state.i === list.length - 1 ? 'Back to slides' : 'Next'}</button>
          </span>
        </div>
      </div>
    </div>
  )
}
