import { useEffect, useState } from 'react'
import { api } from '../api/client.js'
import Weights, { PRIORITY, RISK } from '../components/Weights.jsx'
import { terms } from '../region.js'

// Documentation: how to run, use, score, secure, integrate and operate ClaimShield Nexus.
// Wording follows README.md; the API reference is read live from the server's OpenAPI spec.
const SECTIONS = [
  ['overview', 'Overview'], ['quick-start', 'Quick start'], ['architecture', 'Architecture'], ['workflow', 'Workflow'],
  ['scoring', 'Scoring'], ['auditnext', 'AuditNext'], ['second-brain', 'The Second Brain'], ['human', 'Human in the loop'],
  ['privacy', 'Data privacy'], ['resilience', 'When a method is down'], ['security', 'Roles and security'],
  ['integrations', 'Integrations'], ['operations', 'Deployment and operations'], ['regions', 'Regions'],
  ['api', 'API reference'], ['limits', 'Honest limits'],
]

export default function Docs({ anchor }) {
  const [at, setAt] = useState(anchor || 'overview')

  useEffect(() => {
    if (anchor) document.getElementById(`doc-${anchor}`)?.scrollIntoView()
  }, [])

  // The section nearest the top of the screen is highlighted in the contents.
  useEffect(() => {
    if (!('IntersectionObserver' in window)) return
    const io = new IntersectionObserver((entries) => {
      const hit = entries.filter((e) => e.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)[0]
      if (hit) setAt(hit.target.id.slice(4))
    }, { rootMargin: '0px 0px -70% 0px' })
    SECTIONS.forEach(([id]) => { const el = document.getElementById(`doc-${id}`); if (el) io.observe(el) })
    return () => io.disconnect()
  }, [])

  const go = (id) => (e) => {
    e.preventDefault()
    document.getElementById(`doc-${id}`)?.scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' })
    history.replaceState(null, '', `#/docs?${id}`)
    setAt(id)
  }

  return (
    <>
      <header className="page-head">
        <div>
          <h1>Documentation</h1>
          <p>How to run ClaimShield Nexus, how it scores and explains a case, how it is secured, and how it connects to the systems around it.</p>
        </div>
      </header>
      <div className="docs">
        <nav className="docs-toc" aria-label="Contents">
          <p>On this page</p>
          {SECTIONS.map(([id, label]) => (
            <a key={id} href={`#/docs?${id}`} className={at === id ? 'on' : undefined} aria-current={at === id ? 'location' : undefined} onClick={go(id)}>{label}</a>
          ))}
        </nav>
        <div className="docs-body">
          <Overview />
          <QuickStart />
          <Architecture />
          <Workflow />
          <Scoring />
          <AuditNextDoc />
          <SecondBrain />
          <Human />
          <Privacy />
          <Resilience />
          <SecurityDoc />
          <Integrations />
          <Operations />
          <Regions />
          <ApiReference />
          <Limits />
        </div>
      </div>
    </>
  )
}

function Doc({ id, title, children }) {
  return <section id={`doc-${id}`} className="sec" aria-labelledby={`doc-${id}-h`}><h2 id={`doc-${id}-h`}>{title}</h2>{children}</section>
}

function Table({ head, rows }) {
  return (
    <div className="table-wrap" tabIndex="0" role="region" aria-label={head.filter(Boolean).join(', ')}>
      <table className="data">
        <thead><tr>{head.map((h) => <th key={h}>{h}</th>)}</tr></thead>
        <tbody>{rows.map((r, i) => <tr key={i}>{r.map((c, i) => <td key={i}>{c}</td>)}</tr>)}</tbody>
      </table>
    </div>
  )
}

function Overview() {
  return (
    <Doc id="overview" title="Overview">
      <p>
        ClaimShield Nexus finds suspicious claims and coordinated provider networks in payer data, predicts 30, 60 and 90-day
        repeat risk, ranks cases for a Special Investigations Unit, and explains each case with evidence. Every investigator
        decision is saved to a linked knowledge base, the Second Brain, and becomes precedent for the next case.
      </p>
      <p>All data in this build is synthetic. The system produces leads for human review; it never decides that fraud occurred.</p>
      <Table head={['Stage', 'What happens', 'Where']} rows={[
        ['Detect', 'Claim rules, an anomaly model, network analysis and three prediction models score every claim and provider', <code>backend/pipeline/</code>],
        ['Rank', 'Alerts become cases in three tiers, ordered by priority against team capacity', <code>backend/app/store.py</code>],
        ['Explain', 'A brief with checked facts, a network diagram, precedents and a plan for what to verify next', <code>backend/brain/</code>],
        ['Decide', 'A signed-in investigator records a verdict after previewing what it will change', <code>backend/app/routes/cases.py</code>],
        ['Remember', 'The verdict becomes a Second Brain page and moves the confidence of similar open cases', <code>backend/brain/wiki.py</code>],
        ['Protect', 'Accounts and roles, a signed audit log, tamper detection, document screening, security events', <code>backend/security/</code>],
      ]} />
    </Doc>
  )
}

function QuickStart() {
  return (
    <Doc id="quick-start" title="Quick start">
      <p>Python 3.11 or later and Node 18 or later. Two terminals, both starting in the project folder.</p>
      <pre tabIndex="0">{`python -m pip install -r backend/requirements.txt
python -m uvicorn backend.app.main:app --reload`}</pre>
      <pre tabIndex="0">{`cd frontend
npm install
npm run dev`}</pre>
      <p>
        Open http://localhost:5173, then open Security and access in the sidebar and create an account. The first account on a
        server becomes the admin; every later account starts as a read-only viewer until an admin gives it a role.
      </p>
      <p>
        Pipeline outputs and trained models are in the repository, so nothing has to be generated or trained first. To rebuild,
        run <code>python -m backend.pipeline.run_all</code> (add <code>--region in</code> for India, <code>--retrain</code> to retrain), then restart the API.
      </p>
      <p>
        To connect an LLM, add <code>LLM_BASE_URL</code> and <code>LLM_MODEL</code> to <code>.env</code>. Any OpenAI-compatible endpoint works; a local
        Ollama server keeps every claim on the machine. Without an LLM everything still runs, from templates and keyword lookup.
      </p>
    </Doc>
  )
}

function Architecture() {
  return (
    <Doc id="architecture" title="Architecture">
      <p>
        Detection runs offline. A pipeline run reads the source files, runs each detector, and writes the results per region:
        cases, provider scores, network edges, metrics and a health record. The API serves those saved results and joins them with the
        live Second Brain on every request, so a detector outage never takes the investigators' app down.
      </p>
      <Table head={['Layer', 'Parts', 'Notes']} rows={[
        ['Sources', 'Claims or admissions, provider registry with owners, facilities and referrals, reference tables', 'CSV in this build; a claims warehouse extract in production'],
        ['Offline pipeline', 'Rules, Isolation Forest with isotonic calibration, Leiden communities, referral loops and BiRank, gradient boosting per horizon', 'Each detector isolated; failures recorded, not fatal'],
        ['API', 'FastAPI. Queue and scoring, briefs with fact checks, AuditNext, record review, Second Brain, accounts, security, integrations', 'Every route takes region=us|in'],
        ['Stores', 'Second Brain as linked markdown; SQLite for accounts, the signed audit log and security events; saved LLM text', 'Production: managed database, write-once log storage'],
        ['Out', 'React app, FHIR and CSV exports, Slack, Teams and signed webhooks, any OpenAI-compatible LLM', 'The LLM writes text only'],
      ]} />
      <p>
        Regions share the code and keep everything else apart: raw data, outputs, models and the Second Brain. The active region is
        set per request, so nothing written for one region is read by the other.
      </p>
    </Doc>
  )
}

function Workflow() {
  return (
    <Doc id="workflow" title="Workflow">
      <h3>The queue</h3>
      <p>
        Cases are ranked by priority in three tiers: fast-track, review and not enough evidence. A capacity line marks how many
        open cases the team can take this week, at 5 cases per investigator; change the investigator count to move it.
        Keyboard: <kbd>/</kbd> searches, <kbd>J</kbd> and <kbd>K</kbd> move between cases, <kbd>Enter</kbd> opens one.
      </p>
      <h3>The case page</h3>
      <p>Four pods, read in Gutenberg order:</p>
      <ul>
        <li><b>Subject identity</b>, top left: who, where, the money at stake on a log scale, and how many claims were flagged.</li>
        <li><b>Algorithmic confidence</b>, top right: confidence and repeat risk as distance from a coin flip, uncertainty in bits, and which of the 3 detection methods agree.</li>
        <li><b>Forensic discrepancy</b>, the reading path: the most damning claim as two records and the gap between them, in red only when it is logically impossible; then the record review, the brief, evidence, timeline, network and precedents.</li>
        <li><b>Adaptive action plan</b>, bottom right: the route, the playbook, AuditNext's ranked checks and the decision.</li>
      </ul>
      <h3>Recording a verdict</h3>
      <ol>
        <li>Choose confirm, clear or inconclusive, and write why. The reason becomes precedent for similar cases.</li>
        <li>Preview the Second Brain pages that will change, including the lesson the LLM wrote.</li>
        <li>Sign in, if not already, and approve. The signed-in name is recorded, whatever the form says.</li>
      </ol>
      <p>Similar open cases are re-scored at once, and cases that changed route are marked in the queue.</p>
    </Doc>
  )
}

function Scoring() {
  return (
    <Doc id="scoring" title="Scoring">
      <div className="weights-pair">
        <Weights name="Risk" terms={RISK} />
        <Weights name="Priority" terms={PRIORITY} />
      </div>
      <dl className="formula-panel">
        <div><dt>Evidence strength</dt><dd>min(1, 0.5 rules + 0.2 min(1, 2·ml) + 0.4 graph + 0.15 if 2 or more agree)</dd></div>
        <div><dt>Confidence</dt><dd>evidence strength + precedent adjustment (capped at −0.35 and +0.30)</dd></div>
        <div><dt>Capacity</dt><dd>investigators × 5 cases a week</dd></div>
      </dl>
      <p>
        A detection method agrees when its score reaches its threshold: rules 0.3 or more, the anomaly model 0.25 or more, network
        analysis 0.5 or more. Tiers: high at 0.70 or more, medium at 0.35 or more, otherwise not enough evidence. Dollars and members are
        log-scaled against the largest case. When a detector did not run, risk weights are spread over the ones that did.
      </p>
      <h3>PrecedentGuard</h3>
      <ul>
        <li><b>Contradictions cancel.</b> Confirmed and cleared verdicts on the same pattern for the same provider or network cancel out.</li>
        <li><b>Freshness.</b> A precedent's pull halves every 730 days.</li>
        <li><b>Revocable.</b> A withdrawn precedent is never retrieved again, and every score it moved returns to where it would be without it.</li>
      </ul>
    </Doc>
  )
}

function AuditNextDoc() {
  return (
    <Doc id="auditnext" title="AuditNext">
      <p>
        AuditNext ranks the checks an investigator could run next by <code>U(a) = ΔH ÷ hours</code>: the expected uncertainty a check removes,
        in bits, per hour of investigator time. The starting uncertainty is the case's confidence; 0 bits is certain and 1 bit is a coin flip.
      </p>
      <p>
        Each check's accuracy starts from an assumed value and is updated from closed cases in the Second Brain. Costs assume $90 per
        investigator hour in the US and ₹1,200 in India. The gain, the cost and the utility are shown side by side so the ranking can be checked.
      </p>
    </Doc>
  )
}

function SecondBrain() {
  return (
    <Doc id="second-brain" title="The Second Brain">
      <p>A folder of linked markdown pages, with raw sources kept unedited beside them.</p>
      <ul>
        <li><b>Ask.</b> Questions are answered from the pages, citing the pages used.</li>
        <li><b>Add a source.</b> A lead pastes a document; the preview shows the pages it would create or change, and a signed-in lead approves it.</li>
        <li><b>New patterns.</b> A document can propose a new fraud pattern. It is saved only when the lead approves it, and has no detection rule until one is written.</li>
        <li><b>Document scanner.</b> Runs before the LLM reads a pasted document. Instruction-override text is blocked; softer signs are shown to the approver.</li>
      </ul>
      <p>Confirmed precedents raise the confidence of similar open cases; cleared ones lower it. Precedents, innocent explanations and the evidence to request on each case page come from these pages.</p>
    </Doc>
  )
}

function Human() {
  return (
    <Doc id="human" title="Human in the loop">
      <p>The system produces leads. Only a person closes a case, and every step that changes what the system knows is approved by one.</p>
      <ul>
        <li>A verdict needs a written reason of at least 10 characters, a preview of every page it will change, and a signed-in investigator.</li>
        <li>Source documents and new patterns need a signed-in lead. The server checks the role on every save and reads it fresh each time.</li>
        <li>The LLM writes text only: summaries, the suggested first step, lessons, document summaries, pattern proposals and answers. It never scores, ranks or decides.</li>
        <li>India's watch list is monitored and re-scored, never opened automatically.</li>
        <li>A precedent can be withdrawn with a reason; its effect on every open case is undone at once and the withdrawal is logged.</li>
      </ul>
    </Doc>
  )
}

function Privacy() {
  const t = terms()
  return (
    <Doc id="privacy" title="Data privacy">
      <ul>
        <li>{t.Members} appear only as tokens. In India no name, Aadhaar or mobile number is written to the Second Brain. FHIR exports mask the patient reference.</li>
        <li>The documented LLM setup is a local Ollama server, so no claim leaves the machine. A hosted endpoint is a deliberate configuration choice.</li>
        <li>Slack, Teams and webhook messages carry event type, case and provider IDs, the verdict, the approver and a link. Never member IDs, claim lines or free-text reasoning.</li>
        <li>Every API response is marked <code>Cache-Control: no-store</code>. Access logs record method, path, status and timing, never query strings or bodies.</li>
        <li>Accounts, the audit log and security events stay in a local database file that is not in git.</li>
      </ul>
    </Doc>
  )
}

function Resilience() {
  return (
    <Doc id="resilience" title="When a method is down">
      <p>Detection runs offline and the app serves its saved results, so a detector outage never takes the investigators' app down.</p>
      <ul>
        <li>Within a pipeline run each detector is isolated: if one fails, the run records why and continues with the others.</li>
        <li>Scoring weights are spread over the detectors that ran, and each affected case carries a caution in its brief.</li>
        <li>The app shows a degraded-mode banner naming what is missing, and a security event is recorded.</li>
        <li>If the LLM is unreachable, briefs, suggestions and answers fall back to templates and keyword lookup.</li>
        <li><code>GET /api/health</code> reports detectors, result age, LLM reachability and knowledge integrity.</li>
      </ul>
      <p>To see it, run the pipeline with a simulated failure, then restart the API:</p>
      <pre tabIndex="0">{`$env:CSN_SIMULATE_FAILURE="ml"; python -m backend.pipeline.run_all     # PowerShell
CSN_SIMULATE_FAILURE=ml python -m backend.pipeline.run_all             # bash`}</pre>
      <p>Values: <code>rules</code>, <code>ml</code>, <code>graph</code>, <code>prediction</code>, comma-separated. Clear the variable and run again to return to normal.</p>
    </Doc>
  )
}

function SecurityDoc() {
  return (
    <Doc id="security" title="Roles and security">
      <Table head={['Role', 'May']} rows={[
        ['viewer', 'Read only. Every new account after the first starts here'],
        ['investigator', 'Record verdicts, keep answers, withdraw precedents'],
        ['lead', 'Also approve source documents and new patterns; read the audit trail and security events'],
        ['admin', 'Also manage accounts, accept files after a tampering alert, and manage integrations'],
      ]} />
      <Table head={['Control', 'What it does']} rows={[
        ['Passcodes and sessions', 'Salted PBKDF2-SHA256 at 310,000 iterations; HMAC-signed 8-hour sessions; 5 wrong passcodes lock a name for 5 minutes; unknown names take as long as wrong passcodes'],
        ['Signed audit log', 'Every approved change adds a chained, HMAC-signed entry: who, what, when, and the fingerprint of each file written'],
        ['Tamper detection', 'Every knowledge file is compared with the log. A file changed, deleted or added outside the app is named in a red alert'],
        ['Document scanner', 'Runs before the LLM reads a pasted document. Instruction-override text is blocked; softer signs are shown to the approver'],
        ['Fact checks', 'LLM text containing an ID or amount that is not in its input is discarded'],
        ['Security events', 'Blocked documents, tampering, lockouts, refused actions and detector failures, each with severity and action. HIGH and CRITICAL events are also sent to the configured channels'],
        ['API hardening', 'Security headers, HSTS behind HTTPS, an origin allowlist, no-store responses, and a request ID on every response'],
      ]} />
    </Doc>
  )
}

function Integrations() {
  return (
    <Doc id="integrations" title="Integrations">
      <p>
        ClaimShield Nexus sits beside an existing claims or case-management system rather than replacing it. It reads claim extracts,
        and hands cases back through standard formats and events.
      </p>
      <Table head={['Direction', 'How', 'Use']} rows={[
        ['In', 'Claim, provider and reference extracts as CSV, scored by the pipeline', 'A nightly or weekly extract from the claims warehouse'],
        ['Out', <code>GET /api/cases/{'{id}'}/fhir</code>, 'FHIR ExplanationOfBenefit for case-management and audit systems'],
        ['Out', <code>GET /api/queue/export</code>, 'The ranked queue as CSV, same order and capacity line as the app'],
        ['Out', 'Slack, Microsoft Teams, signed webhooks', 'Events as they happen: verdicts, withdrawn precedents, approved sources and patterns, security alerts'],
        ['Both', 'The REST API', 'Every screen in the app is built from it; see the API reference'],
      ]} />
      <h3>Slack, Microsoft Teams and webhooks</h3>
      <p>Set any of these in <code>.env</code> and restart the API. With none set, nothing is sent.</p>
      <pre tabIndex="0">{`SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
TEAMS_WEBHOOK_URL=https://...  # Teams Workflows: "Post to a channel when a webhook request is received"
WEBHOOK_URLS=https://case-mgmt.example.org/hooks/csn,https://siem.example.org/ingest
WEBHOOK_SECRET=a-long-random-string
APP_BASE_URL=https://siu.example.org
NOTIFY_EVENTS=verdict.recorded,security.alert   # optional; default all`}</pre>
      <p>
        Generic webhooks receive a JSON envelope (<code>id</code>, <code>type</code>, <code>occurred_at</code>, <code>region</code>, <code>schema: csn.event.v1</code>, <code>data</code>, <code>link</code>)
        with headers <code>X-CSN-Event</code>, <code>X-CSN-Delivery</code> and <code>X-CSN-Timestamp</code>. When a secret is set, <code>X-CSN-Signature</code> is
        <code>sha256=</code> HMAC-SHA256 of <code>timestamp.body</code>; receivers should check it and reject old timestamps.
      </p>
      <p>
        Only HTTPS addresses are accepted, apart from localhost. Delivery runs in the background with 3 retries, so a slow receiver never delays an
        investigator. An admin can see the channels and the last 50 deliveries at <code>GET /api/integrations</code> and send a test with <code>POST /api/integrations/test</code>.
      </p>
    </Doc>
  )
}

function Operations() {
  return (
    <Doc id="operations" title="Deployment and operations">
      <p>
        <code>cloudflare/Dockerfile</code> builds the API image for any Docker host. The React build is static and is served next to the API or
        by the included Cloudflare Worker, which forwards <code>/api/*</code> to the API.
      </p>
      <Table head={['Endpoint', 'For']} rows={[
        [<code>GET /api/health/live</code>, 'Liveness probe: the process answers'],
        [<code>GET /api/health/ready</code>, 'Readiness probe: both regions load and the database opens; 503 otherwise'],
        [<code>GET /api/health</code>, 'Detectors, result age, LLM reachability and knowledge integrity, for people and monitors'],
      ]} />
      <Table head={['Setting', 'Meaning']} rows={[
        [<code>AUTH_SECRET</code>, 'Signs sessions and the audit log. Created at first registration; rotate with python -m backend.app.auth rotate-secret'],
        [<code>AUTH_DB</code>, 'Path of the accounts and audit database; default data/app.db'],
        [<code>CORS_ORIGINS</code>, 'Browser origins allowed to call the API from another site; default the local dev servers'],
        [<code>LOG_FORMAT</code>, 'json (default): one JSON line per request with its request ID; off: uvicorn\'s own log'],
        [<code>LLM_BASE_URL</code>, 'Any OpenAI-compatible endpoint, with LLM_MODEL and, for hosted ones, LLM_API_KEY'],
        [<code>SLACK_WEBHOOK_URL</code>, 'And the other integration settings above'],
      ]} />
      <p>Every response carries <code>X-Request-ID</code>; send your own to trace one request across systems.</p>
    </Doc>
  )
}

function Regions() {
  return (
    <Doc id="regions" title="Regions">
      <p>
        A US and India switch changes every page; the API takes <code>region=us|in</code> on every route and defaults to <code>us</code>.
        The US polices the procedure-code line; India polices the hospital admission.
      </p>
      <Table head={['', 'United States', 'India (PM-JAY)']} rows={[
        ['Data', 'CMS-style provider claims', 'PM-JAY-style hospital admissions'],
        ['Rules', 'Duplicate claims, impossible travel, NCCI bundling pairs, CMS unit limits, visit-level drift', 'Overlapping admissions, claims after death, package mismatch, ICU-rate drift, stays above norm, admissions above bed strength, empanelment, camp clusters'],
        ['Network', 'Shared members, referral loops, common ownership', 'The same, plus agent links naming the agent, villages and card operator'],
        ['Queue', 'Three tiers', 'Actionable cases first, then a watch list that is monitored, not opened'],
        ['Currency', 'Dollars', 'Rupees in lakh and crore'],
      ]} />
    </Doc>
  )
}

function ApiReference() {
  const [spec, setSpec] = useState(undefined)
  useEffect(() => { api.openapi().then(setSpec).catch(() => setSpec(null)) }, [])
  const groups = {}
  if (spec) {
    for (const [path, ops] of Object.entries(spec.paths)) {
      for (const [verb, op] of Object.entries(ops)) {
        const tag = op.tags?.[0] || 'other'
        const auth = (op.parameters || []).some((p) => p.in === 'header' && p.name.toLowerCase() === 'authorization')
        const params = (op.parameters || []).filter((p) => p.in === 'query' || p.in === 'path').map((p) => p.name)
        ;(groups[tag] = groups[tag] || []).push({ path, verb, summary: op.description || op.summary || '', auth, params })
      }
    }
  }
  return (
    <Doc id="api" title="API reference">
      <p>Read live from this server's OpenAPI spec. Interactive docs are at <code>/docs</code> on the API server.</p>
      {spec === undefined && <span className="sk sk-line" />}
      {spec === null && <p className="muted">The API did not answer, so the reference cannot be shown. Start the API and reload.</p>}
      {Object.entries(groups).map(([tag, routes]) => (
        <div key={tag}>
          <h3 className="cap">{tag}</h3>
          {routes.map((r) => (
            <div key={r.verb + r.path} className="route">
              <span className={`verb ${r.verb}`}>{r.verb}</span>
              <code>{r.path}{r.auth && <span className="lock">Sign-in</span>}</code>
              {r.summary && <p>{r.summary.split('\n')[0]}</p>}
              {r.params.length > 0 && <small>Parameters: <span className="id">{r.params.join(', ')}</span></small>}
            </div>
          ))}
        </div>
      ))}
    </Doc>
  )
}

function Limits() {
  return (
    <Doc id="limits" title="Honest limits">
      <ul>
        <li>All data is synthetic. Prices and the visit-level mix are approximations.</li>
        <li>Calibration uses injected labels in place of audited outcomes. The prediction target is future rule flags, not proven fraud.</li>
        <li>Results measure recovery of scenarios the dataset injected itself; they are not evidence of performance on real claims.</li>
        <li>AuditNext costs and starting accuracies are assumptions; no comparison experiment has been run.</li>
        <li>Patterns learned from documents have no detection rule yet.</li>
        <li>The regulatory pages and policies are short summaries written for this prototype, not legal advice.</li>
        <li>The audit log's signing key is stored on the same machine as the data, and the document scanner is keyword-based. Both are one layer of defence, not a guarantee.</li>
        <li>No medical-necessity judgment is made.</li>
      </ul>
      <h3>What production would add</h3>
      <p>
        Single sign-on in place of local accounts; the signing key in a vault and the audit log in write-once storage; a managed database in place
        of CSV files and SQLite; encryption at rest; real record intake per case; scheduled pipeline runs with alerting; and validation on audited SIU outcomes.
      </p>
    </Doc>
  )
}
