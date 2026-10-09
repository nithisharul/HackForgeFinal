// A weighted sum drawn as blocks: each block's width is its share of the score, so the biggest driver is visible before anything is read.
// Top edges follow the evidence palette: slate = rules, cyan = model, purple = network, sky = prediction.
export const RISK = [[0.35, 'Rules', 'rule'], [0.2, 'Anomaly model', 'ml', '2 × score, capped at 1'], [0.2, 'Network', 'graph'],
  [0.05, 'BiRank', 'graph'], [0.2, 'Repeat risk', 'pred', 'at the chosen horizon']]
export const PRIORITY = [[0.3, 'Risk'], [0.2, 'Money at stake', null, 'log scale'], [0.1, 'People affected', null, 'log scale'],
  [0.15, 'Severity'], [0.25, 'Confidence']]

export default function Weights({ name, terms }) {
  return (
    <figure className="weights" aria-label={`${name}: ${terms.map(([w, t]) => `${Math.round(w * 100)}% ${t}`).join(', ')}`}>
      <figcaption>{name}</figcaption>
      <ol aria-hidden="true">
        {terms.map(([w, label, fam, hint]) => (
          <li key={label} className={fam ? `w-${fam}` : undefined} style={{ flexGrow: w * 100 }}>
            <b>{Math.round(w * 100)}%</b><span>{label}</span>{hint && <small>{hint}</small>}
          </li>
        ))}
      </ol>
    </figure>
  )
}
