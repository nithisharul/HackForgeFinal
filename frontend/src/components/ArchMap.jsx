import { useState } from 'react'
import Explore from './Explore.jsx'

// Interactive system map. Overview first, then one scene at a time (a build in Present mode, buttons elsewhere),
// then details on demand: select any part for what it does, what happens when it fails, and what protects it.
// Focus + context: the parts in the current scene stay bright, the rest dims but stays in place.
// Motion only where data moves: the dashes on an edge run only while that edge is part of the scene.
const COLS = [['Payer data', 20], ['Offline pipeline', 225], ['Saved results', 430], ['API', 630], ['People and systems', 835]]
const W = 162, H = 54

const nodes = (india) => ({
  claims: [20, 64, india ? 'Admissions' : 'Claims', india ? 'PM-JAY-style extract' : 'CMS-style extract'],
  registry: [20, 136, india ? 'Hospital registry' : 'Provider registry', 'owners, referrals'],
  reference: [20, 208, 'Reference tables', india ? 'HBP package rates' : 'CMS NCCI, MUE'],
  rules: [225, 48, 'Rules', india ? 'India rule pack' : 'R1 to R5', 'rule'],
  ml: [225, 116, 'Anomaly model', 'Isolation Forest', 'ml'],
  graph: [225, 184, 'Network', 'Leiden, BiRank', 'graph'],
  pred: [225, 252, 'Prediction', '30/60/90 days', 'pred'],
  results: [430, 64, 'Cases and scores', 'per region'],
  brain: [430, 150, 'Second Brain', 'linked pages'],
  audit: [430, 236, 'Audit log', 'signed hash chain'],
  api: [630, 48, 'API', 'both regions', null, 168],
  llm: [630, 252, 'LLM', 'text only, fact-checked'],
  app: [835, 64, 'Investigator app', 'queue, case, verdict'],
  exports: [835, 150, 'FHIR and CSV', 'case management'],
  notify: [835, 236, 'Chat and webhooks', 'Slack, Teams; IDs only'],
})

const EDGES = [['claims', 'rules'], ['claims', 'ml'], ['claims', 'graph'], ['claims', 'pred'], ['registry', 'graph'], ['reference', 'rules'],
  ['rules', 'results'], ['ml', 'results'], ['graph', 'results'], ['pred', 'results'],
  ['results', 'api'], ['brain', 'api'], ['api', 'audit', 'back'], ['api', 'llm', 'down'], ['api', 'app'], ['api', 'exports'], ['api', 'notify']]

const ALL = Object.keys(nodes(false))
const SCENES = [
  { t: 'The whole system', d: 'Payer data on the left, people and systems on the right. Select any part for what it does, what happens if it fails, and what protects it.', n: ALL },
  { t: 'Claims come in', d: 'An extract of claims, the registry with owners and referrals, and reference tables. Read, never changed.',
    n: ['claims', 'registry', 'reference', 'rules', 'ml', 'graph', 'pred'], e: ['claims', 'registry', 'reference'] },
  { t: 'Scored offline', d: 'Four detector families run in a scheduled pipeline, each on its own. Results are saved, so the app never waits on a model.',
    n: ['rules', 'ml', 'graph', 'pred', 'results'], e: ['rules', 'ml', 'graph', 'pred'] },
  { t: 'Served with memory', d: 'Each request joins saved results with the Second Brain. Precedents move confidence; every approved change is signed into the log.',
    n: ['results', 'brain', 'audit', 'api'], e: ['results', 'brain', 'api>audit'] },
  { t: 'Explained, then decided', d: 'The LLM writes text only, and every ID, code and amount it writes is checked. A person decides in the app.',
    n: ['api', 'llm', 'app'], e: ['api>llm', 'api>app'] },
  { t: 'Out to your systems', d: 'FHIR and CSV for case management. Slack, Teams and signed webhooks for events as they happen.',
    n: ['api', 'exports', 'notify'], e: ['api>exports', 'api>notify'] },
  { t: 'If a detector fails', d: 'Network analysis is down in this example. The others still score, weights spread over them, and the app says what is missing.',
    n: ALL.filter((x) => x !== 'graph'), e: ['claims', 'registry', 'reference', 'rules', 'ml', 'pred', 'results', 'brain', 'api>app'], down: 'graph' },
  { t: 'Where data stays', d: 'Everything inside the line runs on the payer\'s servers, the LLM included in the default setup. Only IDs and links cross it.',
    n: ALL, e: ['api>notify'], fence: true },
]
export const SCENE_COUNT = SCENES.length

const DETAIL = {
  claims: ['The claim or admission lines to score.', 'Without a new extract, the last results stay in service and their age is shown.', 'Read-only; members appear only as tokens.'],
  registry: ['Who owns which provider, where they bill, and who refers to whom.', 'Network analysis loses its input; the other detectors still run.', 'Read-only.'],
  reference: ['Published code pairs, unit limits or package rates the rules check against.', 'Rules that need them are skipped and named in the run record.', 'Versioned in the repository.'],
  rules: ['Exact checks on single claims and provider months.', 'Its weight is spread over the other detectors; briefs carry a caution.', 'Each hit links to the claim and the rule text.'],
  ml: ['Flags providers unlike their peers, calibrated to a probability.', 'As for rules: degraded mode, named in the banner.', 'Calibration reported with the model.'],
  graph: ['Finds rings: shared members, referral loops, common owners.', 'Rings are not drawn; single-provider evidence still scores.', 'Ring evidence names the links, not people.'],
  pred: ['Chance the provider is flagged again in 30, 60 or 90 days.', 'Risk drops this term and re-weights the rest.', 'Target is future flags, not proven fraud.'],
  results: ['Cases, scores, network edges and a health record per region.', 'The API keeps serving the last good run.', 'Written only by the pipeline.'],
  brain: ['Patterns, policies and closed cases as linked pages.', 'Without it, cases still rank; precedent adjustment is zero.', 'Every file fingerprinted in the signed log; edits outside the app raise an alert.'],
  audit: ['Who approved what and when, chained and HMAC-signed.', 'A broken chain is reported as a critical event.', 'Tamper-evident; the key belongs in a vault in production.'],
  api: ['Ranks the queue, writes briefs, plans next checks, records verdicts.', 'Liveness and readiness probes for the load balancer.', 'Roles checked on every save; security headers; request IDs.'],
  llm: ['Writes summaries, lessons and answers. Never scores, ranks or decides.', 'Templates take over; the app says so.', 'Unverified IDs or amounts are discarded; documents scanned for prompt injection first.'],
  app: ['Queue, case file, network view and the verdict form.', 'Shows a degraded-mode banner naming what is missing.', 'Sign-in and role for every save.'],
  exports: ['FHIR ExplanationOfBenefit per case, and the queue as CSV.', 'Pull on demand; nothing is lost if the receiver is down.', 'Patient reference masked; spreadsheet formulas neutralised.'],
  notify: ['Verdicts, withdrawn precedents, approvals and security alerts.', '3 retries in the background; never delays an investigator.', 'HTTPS only, signed, IDs and links only.'],
}

const mid = ([x, y, , , , h = H], side) => [side === 'r' ? x + W : x, y + h / 2]

export default function ArchMap({ region, build }) {
  const [pick, setPick] = useState(null)
  const N = nodes(region === 'in')
  const sel = (id) => setPick((p) => (p === id ? null : id))
  const info = pick && DETAIL[pick]

  const stage = (at) => {
    const scene = SCENES[at]
    const lit = new Set(pick ? [pick, ...EDGES.filter(([a, b]) => a === pick || b === pick).flatMap(([a, b]) => [a, b])] : scene.n)
    const flows = (a, b) => (pick ? a === pick || b === pick : (scene.e || []).some((k) => k === a || k === `${a}>${b}`)) && at !== 0
    return (
      <svg className="am-svg" viewBox="0 0 1005 330" role="group" aria-label="System map. Select a part for details.">
        {COLS.map(([label, x]) => <text key={label} className="am-col" x={x} y={22}>{label}</text>)}
        <rect className={scene.fence && !pick ? 'am-fence on' : 'am-fence'} x="8" y="34" width="806" height="290" rx="14" />
        <text className={scene.fence && !pick ? 'am-fence-label on' : 'am-fence-label'} x="800" y="318" textAnchor="end">Payer's servers</text>
        {EDGES.map(([a, b, kind]) => {
          const [x1, y1] = kind === 'down' ? [N[a][0] + W / 2, N[a][1] + N[a][5]] : mid(N[a], 'r')
          let [x2, y2] = kind === 'down' ? [N[b][0] + W / 2, N[b][1]] : mid(N[b], 'l')
          if (b === 'api') y2 = Math.max(N.api[1] + 14, Math.min(N.api[1] + N.api[5] - 14, y1))  // enter the tall API box level with the source
          if (kind === 'back') [x2, y2] = [N[b][0] + W, N[b][1] + H / 2]
          const yA = Math.max(N[a][1] + 10, Math.min(N[a][1] + (N[a][5] || H) - 10, y2))
          const sy = a === 'api' && kind !== 'down' ? yA : y1
          const d = kind === 'down' ? `M${x1},${y1} L${x2},${y2}`
            : kind === 'back' ? `M${N[a][0]},${sy} C${N[a][0] - 40},${sy} ${x2 + 40},${y2} ${x2},${y2}`
              : `M${x1},${sy} C${x1 + 40},${sy} ${x2 - 40},${y2} ${x2},${y2}`
          const on = lit.has(a) && lit.has(b)
          const down = scene.down && !pick && (a === scene.down || b === scene.down)
          return <path key={a + b} d={d} className={`am-edge${on ? '' : ' dim'}${flows(a, b) && on ? ' flow' : ''}${down ? ' down' : ''}`} />
        })}
        {Object.entries(N).map(([id, [x, y, label, sub, fam, h = H]]) => {
          const down = scene.down === id && !pick
          const cls = `am-node${lit.has(id) || down ? '' : ' dim'}${pick === id ? ' picked' : ''}${down ? ' down' : ''}${fam ? ` f-${fam}` : ''}`
          return (
            <g key={id} className={cls} transform={`translate(${x},${y})`} tabIndex="0" role="button" aria-pressed={pick === id}
              aria-label={`${label}: ${sub}${down ? ', down in this example' : ''}`} onClick={() => sel(id)}
              onKeyDown={(e) => { if (e.key === 'Enter') { e.stopPropagation(); e.preventDefault(); sel(id) } }}>
              <rect width={W} height={h} rx="8" />
              {fam && <rect className="am-fam" width={W} height="3" rx="1.5" />}
              <text x="12" y="23" className="am-label">{label}</text>
              <text x="12" y="40" className="am-sub">{down ? 'down in this example' : sub}</text>
              {id === 'api' && ['Queue and scoring', 'Briefs and fact checks', 'AuditNext', 'Roles, signed log', 'Integrations'].map((t, i) => (
                <text key={t} x="12" y={70 + i * 19} className="am-sub">{t}</text>
              ))}
            </g>
          )
        })}
      </svg>
    )
  }

  const detail = info && (
    <>
      <h3>{N[pick][2]} <button type="button" className="linklike" onClick={() => setPick(null)}>Back to the steps</button></h3>
      <dl className="ex-detail">
        <div><dt>Does</dt><dd>{info[0]}</dd></div>
        <div><dt>If it fails</dt><dd>{info[1]}</dd></div>
        <div><dt>Protected by</dt><dd>{info[2]}</dd></div>
      </dl>
    </>
  )
  return <Explore label="System map" steps={SCENES} build={build} stage={stage} detail={detail} paused={Boolean(pick)} />
}
