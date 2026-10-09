import { useEffect, useRef, useState } from 'react'
import { api } from '../api/client.js'
import SignIn, { useSession } from '../components/SignIn.jsx'
import { Loading, Markdown, toast } from '../components/bits.jsx'
import { terms } from '../region.js'

export default function Wiki({ name }) {
  const [pages, setPages] = useState(null)
  const [page, setPage] = useState(null)
  const [lint, setLint] = useState(null)
  const [error, setError] = useState(null)
  const [tick, setTick] = useState(0)
  const [filter, setFilter] = useState('')
  const [adding, setAdding] = useState(false)
  const ask = useRef(null)
  const refresh = () => setTick((t) => t + 1)

  useEffect(() => {
    api.wikiPages().then(setPages).catch((e) => setError(e.message))
    api.wikiLint().then(setLint).catch(() => {})
  }, [name, tick])
  useEffect(() => {
    setPage(null)
    api.wikiPage(name).then(setPage).catch((e) => setError(e.message))
  }, [name, tick])
  // The command palette asks for the Ask dialog with a 'csn-ask' event, or a flag when it navigates here first.
  const [askPending, setAskPending] = useState(() => { try { const v = sessionStorage.getItem('csn-ask'); sessionStorage.removeItem('csn-ask'); return !!v } catch { return false } })
  useEffect(() => {
    const on = () => setAskPending(true)
    window.addEventListener('csn-ask', on)
    return () => window.removeEventListener('csn-ask', on)
  }, [])
  useEffect(() => { if (askPending && ask.current) { ask.current.showModal(); setAskPending(false) } })

  if (!pages || !page) return <Loading error={error} what="the Second Brain" onRetry={() => { setError(null); refresh() }} />
  const live = pages.cases.filter((c) => c.startsWith('CASE-'))
  const f = filter.trim().toLowerCase()
  const match = (p, label) => !f || `${p} ${label || ''}`.toLowerCase().includes(f)
  const link = (p, label) => match(p, label) && (
    <a key={p} className={name === p ? 'on' : ''} aria-current={name === p ? 'page' : undefined} href={`#/brain/${p}`}>{label || p}</a>
  )
  // Groups fold; short groups, the one holding the open page, and every group while filtering stay open.
  const group = (title, items, label, empty) => (
    <details className="nav-group" open={!!f || items.includes(name) || items.length <= 8}>
      <summary>{title} <span>{items.length}</span></summary>
      {items.length === 0 && <small>{empty}</small>}
      {items.map((p) => link(p, label?.(p)))}
    </details>
  )

  return (
    <>
    <header className="page-head">
      <div>
        <h1>Second Brain</h1>
        <p>Patterns, policies and closed cases, kept as linked pages. Every decision the team records is added here.</p>
      </div>
      <div className="page-actions">
        <button type="button" className="btn" onClick={() => setAdding(true)}>Add source document</button>
        <button type="button" className="btn primary" onClick={() => ask.current?.showModal()}>Ask a question</button>
      </div>
    </header>
    <div className="wiki">
      <aside aria-label="Second Brain pages">
        <span className={`llm ${pages.llm.enabled ? 'on' : 'off'}`}>
          {pages.llm.enabled ? `LLM connected: ${pages.llm.model}` : 'No LLM connected: template mode'}
        </span>
        <button type="button" className="ask-open" onClick={() => ask.current?.showModal()}>
          Ask the Second Brain
        </button>
        <input type="search" className="nav-filter" value={filter} onChange={(e) => setFilter(e.target.value)} placeholder="Filter pages" aria-label="Filter pages" />
        {link('index', 'Index')}
        {link('log', 'Change log')}
        {group('Patterns', pages.patterns, (p) => p.replace(/_/g, ' '))}
        {group('Networks', pages.networks)}
        {group('Sources', pages.sources, null, 'No documents added yet.')}
        {group('Kept answers', pages.notes, null, 'None yet.')}
        {group('Learned from this team', live, null, 'No verdicts recorded yet.')}
        <details className="nav-group">
          <summary>Health check {lint && <span className={lint.issues.length ? 'warn' : ''}>{lint.issues.length || 'OK'}</span>}</summary>
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
        </details>
      </aside>
      <div className="col">
        {adding && <AddSource onSaved={refresh} onClose={() => setAdding(false)} />}
        <article className="card reading">
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
      <dialog ref={ask} className="modal wide" aria-label="Ask the Second Brain"
        onClick={(e) => (e.target === ask.current || e.target.closest('a')) && ask.current.close()}>
        <div className="modal-body">
          <Ask onFiled={refresh} />
          <button type="button" className="modal-x" aria-label="Close" onClick={() => ask.current?.close()}>×</button>
        </div>
      </dialog>
    </div>
    </>
  )
}

function Ask({ onFiled }) {
  const [q, setQ] = useState('')
  const [busy, setBusy] = useState(false)
  const [res, setRes] = useState(null)
  const [error, setError] = useState(null)
  const [filed, setFiled] = useState(null)
  const session = useSession()

  const submit = (e) => {
    e.preventDefault()
    if (q.trim().length < 5) return
    setBusy(true); setError(null); setRes(null); setFiled(null)
    api.ask(q).then(setRes).catch((err) => setError(err.message)).finally(() => setBusy(false))
  }
  const keep = () =>
    api.fileNote({ question: res.question, answer: res.answer })
      .then((r) => { setFiled(r.note_id); onFiled(); toast(`Answer kept as ${r.note_id}`) }).catch((err) => setError(err.message))

  return (
    <section className="ask-panel">
      <h3>Ask the Second Brain</h3>
      <p className="hint">Answers come only from wiki pages, with citations.</p>
      <form className="ask" onSubmit={submit}>
        <input autoFocus aria-label="Question" value={q} onChange={(e) => setQ(e.target.value)} placeholder={`e.g. ${terms().ask}`} />
        <button className="btn primary" disabled={busy || q.trim().length < 5}>{busy ? 'Reading…' : 'Ask'}</button>
      </form>
      {error && <p className="notice error" role="alert">{error}</p>}
      {res && (
        <div className="answer">
          <Markdown text={res.answer} />
          <p className="trail">
            Pages read: {res.pages_read.map((n, i) => (
              <span key={n}>{i > 0 && ', '}<a className="wikilink" href={`#/brain/${n}`}>{n}</a></span>
            ))}
            {res.unknown_citations.length > 0 && `. Removed ${res.unknown_citations.length} citation(s) to pages that do not exist.`}
          </p>
          {res.mode === 'llm' && !filed && (
            <div className="keep">
              <SignIn />
              <button className="btn" disabled={!session} onClick={keep}>Keep this answer as a page</button>
            </div>
          )}
          {filed && <p>Saved as <a className="wikilink" href={`#/brain/${filed}`}>{filed}</a>.</p>}
        </div>
      )}
    </section>
  )
}

function AddSource({ onSaved, onClose }) {
  const [title, setTitle] = useState('')
  const [text, setText] = useState('')
  const [preview, setPreview] = useState(null)
  const [saved, setSaved] = useState(null)
  const session = useSession()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const body = { title, text }
  const ready = title.trim().length >= 3 && text.trim().length >= 40

  const run = (fn, payload, then) => {
    setBusy(true); setError(null)
    fn(payload).then(then).catch((e) => setError(e.message)).finally(() => setBusy(false))
  }

  return (
    <section className="card add-source">
      <h3>Add a source document<small>the brain reads it and proposes page updates</small></h3>
      <button type="button" className="modal-x" aria-label="Close" onClick={onClose}>×</button>
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
          {!preview && <div className="btn-row"><button className="btn primary" disabled={!ready || busy} onClick={() => run(api.previewSource, body, setPreview)}>{busy ? 'Reading…' : 'Read and preview changes'}</button></div>}
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
              <SignIn />
              <div className="btn-row">
                <button className="btn primary" disabled={!session || busy}
                  onClick={() => run(api.addSource, { ...body, proposal: preview.proposal }, (r) => { setSaved(r); onSaved(); toast(`Source saved as ${r.source_id}`) })}>Approve and save</button>
                <button className="btn" onClick={() => setPreview(null)}>Edit</button>
              </div>
            </div>
          )}
        </>
      )}
    </section>
  )
}
