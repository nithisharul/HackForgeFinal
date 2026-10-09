import { useEffect, useRef, useState } from 'react'

// One explorable figure: a full-width stage, numbered steps under it, and a caption for the step in focus.
// Overview first, then one idea at a time (focus + context), details on demand.
//   Presenting: the deck's arrow key drives the step (build).
//   On the page: the steps advance by themselves while the figure is on screen and nobody is using it
//   (at least 60% in view, tab visible, not hovered or focused, not touched in the last 20 s). Any interaction pauses it.
// stage(at) draws the figure for the step in focus; detail, when given, replaces the caption (a selected part).
const DWELL = 6500

export default function Explore({ steps, build, stage, detail, paused, label }) {
  const [own, setOwn] = useState(0)
  const [auto, setAuto] = useState(false)
  const root = useRef(null)
  const hold = useRef(0)
  const at = build == null ? own : Math.min(build, steps.length - 1)

  useEffect(() => {
    if (build != null || matchMedia('(prefers-reduced-motion: reduce)').matches || !('IntersectionObserver' in window)) return setAuto(false)
    const el = root.current
    let seen = false, using = false
    const update = () => setAuto(seen && !using && document.visibilityState === 'visible')
    const io = new IntersectionObserver(([e]) => { seen = e.intersectionRatio >= 0.6; update() }, { threshold: [0, 0.6, 1] })
    const on = () => { using = true; update() }
    const off = () => { using = el.matches(':focus-within'); update() }
    const blur = () => { using = el.matches(':hover'); update() }
    io.observe(el)
    el.addEventListener('pointerenter', on); el.addEventListener('pointerleave', off)
    el.addEventListener('focusin', on); el.addEventListener('focusout', blur)
    document.addEventListener('visibilitychange', update)
    return () => {
      io.disconnect()
      el.removeEventListener('pointerenter', on); el.removeEventListener('pointerleave', off)
      el.removeEventListener('focusin', on); el.removeEventListener('focusout', blur)
      document.removeEventListener('visibilitychange', update)
    }
  }, [build])

  const playing = auto && !paused
  useEffect(() => {
    if (!playing) return
    const id = setInterval(() => { if (performance.now() > hold.current) setOwn((i) => (i + 1) % steps.length) }, DWELL)
    return () => clearInterval(id)
  }, [playing, steps.length])

  const pick = (i) => { hold.current = performance.now() + 20000; setOwn(i) }
  const step = steps[at]

  return (
    <div ref={root} className="explore" role="group" aria-label={label} onPointerDown={() => { hold.current = performance.now() + 20000 }}>
      <div className="ex-stage">{stage(at)}</div>
      <div className="ex-bar">
        <ol className="ex-steps" aria-label="Steps">
          {steps.map((s, i) => (
            <li key={s.t}>
              <button type="button" disabled={build != null} aria-current={i === at ? 'step' : undefined} aria-label={`Step ${i + 1}: ${s.t}`}
                className={i === at ? (playing ? 'on playing' : 'on') : i < at ? 'past' : undefined}
                style={{ '--dwell': `${DWELL}ms` }} onClick={() => pick(i)}>
                {i + 1}
              </button>
            </li>
          ))}
        </ol>
        <div key={detail ? 'detail' : at} className="ex-caption" aria-live="polite">
          {detail || <><h3>{step.t}</h3><p>{step.d}</p></>}
        </div>
      </div>
    </div>
  )
}
