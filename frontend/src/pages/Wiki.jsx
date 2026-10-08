import { useEffect, useState } from 'react'
import { api, getSession } from '../api/client.js'
import SignIn from '../components/SignIn.jsx'
import { Loading, Markdown } from '../components/bits.jsx'

export default function Wiki({ name }) {
  const [pages, setPages] = useState(null)
  const [page, setPage] = useState(null)
  const [lint, setLint] = useState(null)
  const [error, setError] = useState(null)
  const [tick, setTick] = useState(0)
  const refresh = () => setTick((t) => t + 1)

  useEffect(() => {
    api.wikiPages().then(setPages).catch((e) => setError(e.message))
    api.wikiLint().then(setLint).catch(() => {})
  }, [name, tick])
  useEffect(() => {
    setPage(null)
    api.wikiPage(name).then(setPage).catch((e) => setError(e.message))
  }, [name, tick])

  if (!pages || !page) return <Loading error={error} what="the Second Brain" onRetry={() => { setError(null); refresh() }} />
  const live = pages.cases.filter((c) => c.startsWith('CASE-'))
  const link = (p, label) => <a key={p} className={name === p ? 'on' : ''} aria-current={name === p ? 'page' : undefined} href={`#/brain/${p}`}>{label || p}</a>

  return (
    <div className="wiki">
      <aside aria-label="Second Brain pages">
        <span className={`llm ${pages.llm.enabled ? 'on' : 'off'}`}>
          {pages.llm.enabled ? `LLM connected: ${pages.llm.model}` : 'No LLM connected: template mode'}
        </span>
        {link('index', 'Index')}
        {link('log', 'Change log')}
        <h4>Patterns</h4>
        {pages.patterns.map((p) => link(p, p.replace(/_/g, ' ')))}
        <h4>Networks</h4>
        {pages.networks.map((p) => link(p))}
        <h4>Sources ({pages.sources.length})</h4>
        {pages.sources.length === 0 && <small>No documents added yet.</small>}
        {pages.sources.map((p) => link(p))}
        <h4>Kept answers ({pages.notes.length})</h4>
        {pages.notes.map((p) => link(p))}
        <h4>Learned from this team ({live.length})</h4>
        {live.length === 0 && <small>No verdicts recorded yet.</small>}
        {live.map((p) => link(p))}
        <h4>Health check</h4>
        {lint && (
          <div className="lint">
            <small>{lint.pages} pages, {lint.cases} closed cases</small>
            {lint.issues.length === 0 && <small>No issues.</small>}
            {lint.issues.map((i, k) => (
              <p key={k} className={`lint-${i.level}`}>
                <a className="wikilink" href={`#/brain/${i.page}`}>{i.page}</a>: {i.issue}
              </p>
            ))}
          </div>
        )}
      </aside>
      <div className="col">
        <Ask onFiled={refresh} />
        <AddSource onSaved={refresh} />
        <article className="card">
          {page.meta && Object.keys(page.meta).length > 0 && (
            <p className="meta">
              {Object.entries(page.meta).map(([k, v]) => <span key={k}><b>{k}</b> {v}</span>)}
            </p>
          )}
          <Markdown text={page.body} />
          {page.backlinks.length > 0 && (
            <p className="trail">
              Linked from: {page.backlinks.map((b, i) => (
                <span key={b}>{i > 0 && ', '}<a className="wikilink" href={`#/brain/${b}`}>{b}</a></span>
              ))}
            </p>
          )}
        </article>
      </div>
    </div>
  )
}

function Ask({ onFiled }) {
  const [q, setQ] = useState('')
  const [busy, setBusy] = useState(false)
  const [res, setRes] = useState(null)
  const [error, setError] = useState(null)
  const [filed, setFiled] = useState(null)
  const [, setAuthTick] = useState(0)

  const submit = (e) => {
    e.preventDefault()
    if (q.trim().length < 5) return
    setBusy(true); setError(null); setRes(null); setFiled(null)
    api.ask(q).then(setRes).catch((err) => setError(err.message)).finally(() => setBusy(false))
  }
  const keep = () =>
    api.fileNote({ question: res.question, answer: res.answer })
      .then((r) => { setFiled(r.note_id); onFiled() }).catch((err) => setError(err.message))

  return (
    <section className="card">
      <h3>Ask the Second Brain<small>answers come only from wiki pages, with citations</small></h3>
      <form className="ask" onSubmit={submit}>
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="e.g. What have we learned about referral rings?" />
        <button className="btn primary" disabled={busy || q.trim().length < 5}>{busy ? 'Reading…' : 'Ask'}</button>
      </form>
      {error && <p className="notice error" role="alert">{error}</p>}
      {res && (
        <div className="answer">
          <Markdown text={res.answer} />
          <p className="trail">
            Read: {res.pages_read.map((n, i) => (
              <span key={n}>{i > 0 && ' → '}<a className="wikilink" href={`#/brain/${n}`}>{n}</a></span>
            ))}
            {res.unknown_citations.length > 0 && `. Removed ${res.unknown_citations.length} citation(s) to pages that do not exist.`}
          </p>
          {res.mode === 'llm' && !filed && (
            <div className="ask">
              <SignIn onChange={() => setAuthTick((n) => n + 1)} />
              <button className="btn" disabled={!getSession()} onClick={keep}>Keep this answer as a page</button>
            </div>
          )}
          {filed && <p>Saved as <a className="wikilink" href={`#/brain/${filed}`}>{filed}</a>.</p>}
        </div>
      )}
    </section>
  )
}

function AddSource({ onSaved }) {
  const [open, setOpen] = useState(false)
  const [title, setTitle] = useState('')
  const [text, setText] = useState('')
  const [preview, setPreview] = useState(null)
  const [saved, setSaved] = useState(null)
  const [, setAuthTick] = useState(0)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const body = { title, text }
  const ready = title.trim().length >= 3 && text.trim().length >= 40

  const run = (fn, payload, then) => {
    setBusy(true); setError(null)
    fn(payload).then(then).catch((e) => setError(e.message)).finally(() => setBusy(false))
  }
  if (!open) return <button className="btn add" onClick={() => setOpen(true)}>+ Add a source document</button>

  return (
    <section className="card">
      <h3>Add a source document<small>the brain reads it and proposes page updates</small></h3>
      {saved ? (
        <p>Saved as <a className="wikilink" href={`#/brain/${saved.source_id}`}>{saved.source_id}</a>. Pages updated:{' '}
          {saved.changes.map((c) => c.page).join(', ')}.</p>
      ) : (
        <>
          <label className="field">Title
            <input value={title} onChange={(e) => { setTitle(e.target.value); setPreview(null) }} />
          </label>
          <label className="field">Document text (policy, bulletin, audit memo)
            <textarea rows="5" value={text} onChange={(e) => { setText(e.target.value); setPreview(null) }} />
          </label>
          {error && <p className="notice error" role="alert">{error}</p>}
          {!preview && <button className="btn" disabled={!ready || busy} onClick={() => run(api.previewSource, body, setPreview)}>{busy ? 'Reading…' : 'Read and preview changes'}</button>}
          {preview && (
            <div className="diff">
              <h4>Proposed by {preview.proposal.written_by === 'llm' ? 'the LLM' : 'template (no LLM connected)'}</h4>
              <p>{preview.proposal.summary}</p>
              <ul className="plain">
                {preview.proposal.pattern_notes.map((n, i) => (
                  <li key={i}><a className="wikilink" href={`#/brain/${n.pattern}`}>{n.pattern}</a>: {n.note}</li>
                ))}
              </ul>
              <h4>Pages that will change</h4>
              <p>{preview.changes.map((c) => `${c.action} ${c.page}`).join(', ')}</p>
              <SignIn onChange={() => setAuthTick((n) => n + 1)} />
              <button className="btn primary" disabled={!getSession() || busy}
                onClick={() => run(api.addSource, { ...body, proposal: preview.proposal }, (r) => { setSaved(r); onSaved() })}>Approve and save</button>
              <button className="btn" onClick={() => setPreview(null)}>Edit</button>
            </div>
          )}
        </>
      )}
    </section>
  )
}
