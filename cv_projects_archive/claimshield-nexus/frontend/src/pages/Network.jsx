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
  if (!g) return <p>Loading network…</p>
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
          return (
            <g key={n.id} className={`node node-${cls}`} transform={`translate(${x} ${y})`}
              onMouseEnter={() => setHover(n.id)} onMouseLeave={() => setHover(null)}
              onClick={() => n.type === 'provider' && n.flagged && (window.location.hash = `#/case/CASE-${n.id}`)}>
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
