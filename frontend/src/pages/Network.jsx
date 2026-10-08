import { useEffect, useState } from 'react'
import { api } from '../api/client.js'

const W = 520
const H = 380
const STYLE = {
  shared_members: { stroke: 'var(--link-shared)', dash: '' },
  referral: { stroke: 'var(--link-referral)', dash: '' },
  ownership: { stroke: 'var(--link-owner)', dash: '5 4' },
  facility: { stroke: 'var(--line)', dash: '2 3' },
}

export default function Network({ providerId }) {
  const [g, setG] = useState(null)
  const [hover, setHover] = useState(null)
  useEffect(() => { setG(null); api.graph(providerId).then(setG).catch(() => setG({ nodes: [], links: [] })) }, [providerId])
  if (!g) return <div className="sk sk-graph" role="status" aria-label="Loading network" />
  if (!g.nodes.length) return null

  const pos = {}
  const provs = g.nodes.filter((n) => n.type === 'provider' && !n.center)
  const facs = g.nodes.filter((n) => n.type === 'facility')
  const owner = g.nodes.find((n) => n.type === 'owner')
  pos[providerId] = [W / 2, H / 2 - 20]
  provs.forEach((n, i) => {
    const a = (2 * Math.PI * i) / provs.length - Math.PI / 2
    pos[n.id] = [W / 2 + 185 * Math.cos(a), H / 2 - 20 + 125 * Math.sin(a)]
  })
  if (owner) pos[owner.id] = [44, 28]
  facs.forEach((n, i) => { pos[n.id] = [((i + 1) * W) / (facs.length + 1), H - 22] })
  const maxW = Math.max(1, ...g.links.filter((l) => l.type === 'shared_members').map((l) => l.weight))

  return (
    <figure className="network">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Relationship graph for ${providerId}`}>
        <defs>
          <marker id="arrow" viewBox="0 0 10 10" refX="19" refY="5" markerWidth="5" markerHeight="5" orient="auto">
            <path d="M0 0 L10 5 L0 10 z" fill="var(--link-referral)" />
          </marker>
        </defs>
        {g.links.map((l, i) => {
          const [x1, y1] = pos[l.source]
          const [x2, y2] = pos[l.target]
          const s = STYLE[l.type]
          const bend = l.type === 'referral' ? 14 : 0
          const mx = (x1 + x2) / 2 - ((y2 - y1) / Math.hypot(x2 - x1, y2 - y1 || 1)) * bend
          const my = (y1 + y2) / 2 + ((x2 - x1) / Math.hypot(x2 - x1, y2 - y1 || 1)) * bend
          return (
            <path key={i} d={`M${x1} ${y1} Q${mx} ${my} ${x2} ${y2}`} fill="none" stroke={s.stroke}
              strokeDasharray={s.dash} markerEnd={l.type === 'referral' ? 'url(#arrow)' : undefined}
              strokeWidth={l.type === 'shared_members' ? 1 + (3 * l.weight) / maxW : 1.4}
              opacity={hover && hover !== l.source && hover !== l.target ? 0.12 : 0.8}>
              <title>{l.source} → {l.target}: {l.label}</title>
            </path>
          )
        })}
        {g.nodes.map((n) => {
          const [x, y] = pos[n.id]
          const cls = n.type === 'provider' ? (n.center ? 'center' : n.flagged ? 'flagged' : 'plain') : n.type
          const go = n.type === 'provider' && n.flagged && !n.center ? () => (window.location.hash = `#/case/CASE-${n.id}`) : undefined
          return (
            <g key={n.id} className={`node node-${cls}`} transform={`translate(${x} ${y})`}
              onMouseEnter={() => setHover(n.id)} onMouseLeave={() => setHover(null)}
              onFocus={() => setHover(n.id)} onBlur={() => setHover(null)}
              tabIndex={go ? 0 : undefined} role={go ? 'link' : undefined} aria-label={go ? `Open case for ${n.id}` : undefined}
              onClick={go} onKeyDown={go && ((e) => e.key === 'Enter' && go())}>
              {n.type === 'provider' ? <circle r={n.center ? 15 : 11} /> : <rect x="-17" y="-10" width="34" height="20" rx="4" />}
              <text textAnchor="middle" dy="4">{n.label}</text>
              <title>{n.id} {n.name}{n.specialty ? ` · ${n.specialty}` : ''}{n.city ? ` · ${n.city}` : ''}</title>
            </g>
          )
        })}
      </svg>
      <figcaption>
        <span><i className="sw sw-shared" /> shared members</span>
        <span><i className="sw sw-referral" /> referrals</span>
        <span><i className="sw sw-owner" /> same owner</span>
        <span><i className="dot dot-flagged" /> flagged provider</span>
        <span><i className="dot dot-plain" /> other provider</span>
      </figcaption>
    </figure>
  )
}

// Hero version: only the ring itself. Members sit on a circle in referral order, so the
// closed loop reads at a glance; the shared owner sits in the middle.
const RW = 480
const RH = 440
const R = 158
const NODE = 22
const polar = (a, r) => [RW / 2 + r * Math.cos(a), RH / 2 + r * Math.sin(a)]

export function RingHero({ c }) {
  const [g, setG] = useState(null)
  const [hover, setHover] = useState(null)
  useEffect(() => { api.graph(c.provider_id).then(setG).catch(() => setG({ nodes: [], links: [] })) }, [c.provider_id])
  if (!g) return <div className="sk ring-sk" role="status" aria-label="Loading network" />

  const members = g.nodes.filter((n) => n.type === 'provider' && n.cluster === c.network)
  if (members.length < 3) return null
  const ids = new Set(members.map((n) => n.id))
  const inRing = (l) => ids.has(l.source) && ids.has(l.target)
  const refs = g.links.filter((l) => l.type === 'referral' && inRing(l))
  // Follow referrals from the case's provider; members off the loop are appended in data order.
  const order = [c.provider_id]
  for (let cur = c.provider_id; ;) {
    const next = refs.find((l) => l.source === cur && !order.includes(l.target))?.target
    if (!next) break
    order.push(next)
    cur = next
  }
  members.forEach((n) => order.includes(n.id) || order.push(n.id))
  const closed = refs.some((l) => l.source === order[order.length - 1] && l.target === order[0])
  const owner = g.nodes.find((n) => n.type === 'owner')
  const byId = Object.fromEntries(members.map((n) => [n.id, n]))
  const ang = Object.fromEntries(order.map((id, i) => [id, -Math.PI / 2 + (2 * Math.PI * i) / order.length]))

  // Referral arcs bow outward between neighbours; ends are trimmed so arrows clear the nodes.
  const trim = (NODE + 6) / R
  const arc = (l) => {
    const a1 = ang[l.source]
    let a2 = ang[l.target]
    if (a2 < a1) a2 += 2 * Math.PI
    const [x1, y1] = polar(a1 + trim, R)
    const [x2, y2] = polar(a2 - trim, R)
    const [cx, cy] = polar((a1 + a2) / 2, R * 1.2)
    return { start: [x1, y1], d: `Q${cx} ${cy} ${x2} ${y2}`, path: `M${x1} ${y1} Q${cx} ${cy} ${x2} ${y2}` }
  }
  const loopRefs = order.map((id, i) => refs.find((l) => l.source === id && l.target === order[(i + 1) % order.length])).filter(Boolean)
  const otherRefs = refs.filter((l) => !loopRefs.includes(l))
  const shared = g.links.filter((l) => l.type === 'shared_members' && inRing(l))
  const maxW = Math.max(1, ...shared.map((l) => l.weight))
  // One continuous path around the loop for the travelling pulses (they pass under each node).
  const tour = loopRefs.map((l, i) => { const a = arc(l); return `${i ? 'L' : 'M'}${a.start[0]} ${a.start[1]} ${a.d}` }).join(' ')
  const totalRefs = loopRefs.reduce((n, l) => n + l.weight, 0)
  const still = typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches
  const dim = (l) => hover && hover !== l.source && hover !== l.target
  const go = (id) => () => (window.location.hash = `#/case/CASE-${id}`)

  return (
    <figure className="ring">
      <svg viewBox={`0 0 ${RW} ${RH}`} role="img" aria-label={`Network ${c.network}: ${order.length} providers referring patients in a ${closed ? 'closed loop' : 'chain'}`}>
        <defs>
          <marker id="ring-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto">
            <path d="M0 0 L10 5 L0 10 z" fill="var(--link-referral)" />
          </marker>
        </defs>
        {owner && order.map((id) => {
          const [x, y] = polar(ang[id], R - NODE)
          return <line key={`o-${id}`} className="r-own" x1={RW / 2} y1={RH / 2} x2={x} y2={y} opacity={hover && hover !== id && hover !== owner.id ? 0.1 : 0.55} />
        })}
        {shared.map((l, i) => {
          const [x1, y1] = polar(ang[l.source], R)
          const [x2, y2] = polar(ang[l.target], R)
          return (
            <line key={`s-${i}`} className="r-shared" x1={x1} y1={y1} x2={x2} y2={y2}
              strokeWidth={0.8 + (2.2 * l.weight) / maxW} opacity={dim(l) ? 0.06 : 0.35}>
              <title>{l.source} and {l.target}: {l.label}</title>
            </line>
          )
        })}
        {[...loopRefs, ...otherRefs].map((l, i) => (
          <path key={`r-${i}`} className="r-ref" d={arc(l).path} pathLength="1" markerEnd="url(#ring-arrow)"
            style={{ animationDelay: `${0.2 + i * 0.12}s` }} opacity={dim(l) ? 0.15 : 1}>
            <title>{l.source} to {l.target}: {l.label}</title>
          </path>
        ))}
        {!still && closed && [0, 0.5].map((off) => (
          <circle key={off} className="r-pulse" r="5" opacity="0">
            <set attributeName="opacity" to="1" begin={`${1 + off * 7}s`} />
            <animateMotion dur="7s" begin={`${1 + off * 7}s`} repeatCount="indefinite" path={tour} />
          </circle>
        ))}
        {owner && (
          <g className="r-owner" onMouseEnter={() => setHover(owner.id)} onMouseLeave={() => setHover(null)}>
            <rect x={RW / 2 - 26} y={RH / 2 - 13} width="52" height="26" rx="4" />
            <text x={RW / 2} y={RH / 2 + 4} textAnchor="middle">{owner.label}</text>
            <title>{owner.id} {owner.name}: owns every provider in the ring</title>
          </g>
        )}
        {order.map((id) => {
          const n = byId[id]
          const [x, y] = polar(ang[id], R)
          const [lx, ly] = polar(ang[id], R + NODE + 16)
          const cos = Math.cos(ang[id])
          return (
            <g key={id} className={`r-node${id === c.provider_id ? ' r-focus' : ''}`} tabIndex={0} role="link"
              aria-label={`Open case for ${id}, ${n.name}`}
              onMouseEnter={() => setHover(id)} onMouseLeave={() => setHover(null)}
              onFocus={() => setHover(id)} onBlur={() => setHover(null)}
              onClick={go(id)} onKeyDown={(e) => e.key === 'Enter' && go(id)()}>
              <circle cx={x} cy={y} r={NODE} />
              <text x={x} y={y + 4} textAnchor="middle">{n.label}</text>
              <text className="r-sub" x={lx} y={ly + 4} textAnchor={Math.abs(cos) < 0.3 ? 'middle' : cos > 0 ? 'start' : 'end'}>{n.specialty}</text>
              <title>{id} {n.name}, {n.specialty}</title>
            </g>
          )
        })}
      </svg>
      <figcaption>
        <p>
          Network analysis found <b>{order.length} providers</b>{owner ? <> under one owner, <b>{owner.label}</b>,</> : ''} sending{' '}
          <b>{totalRefs.toLocaleString('en-US')} referrals</b> around a {closed ? 'closed loop' : 'chain'}. Select a provider to open its case.
        </p>
        <span className="r-key"><i className="sw sw-referral" /> referrals</span>
        <span className="r-key"><i className="sw sw-shared" /> shared members</span>
        {owner && <span className="r-key"><i className="sw sw-owner" /> same owner</span>}
      </figcaption>
    </figure>
  )
}
