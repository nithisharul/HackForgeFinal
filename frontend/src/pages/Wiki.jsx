import { useEffect, useState } from 'react'
import { api, getSession } from '../api/client.js'
import SignIn from '../components/SignIn.jsx'
import Accounts from '../components/Accounts.jsx'
import Security from '../components/Security.jsx'
import { Loading, Markdown } from '../components/bits.jsx'

const REF_GROUPS = [['rules', 'Business rules'], ['data', 'Data definitions'], ['process', 'Runbooks'],
  ['system', 'Technical docs'], ['regulatory', 'Regulatory material']]

export default function Wiki({ name }) {
  const [pages, setPages] = useState(null)
  const [page, setPage] = useState(null)
  const [lint, setLint] = useState(null)
  const [error, setError] = useState(null)
  const [tick, setTick] = useState(0)
  const [openRef, setOpenRef] = useState({})
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
        {REF_GROUPS.map(([g, label]) => {
          const list = pages[g] || []
          if (list.length === 0) return null
          const isOpen = openRef[g] ?? list.includes(name)
          return [
            <h4 key={g}>
              <button type="button" aria-expanded={isOpen} onClick={() => setOpenRef((o) => ({ ...o, [g]: !isOpen }))}
                style={{ all: 'unset', cursor: 'pointer' }}>{isOpen ? '▾' : '▸'} {label} ({list.length})</button>
            </h4>,
            ...(isOpen ? list.map((p) => link(p, p.replace(/^(data|runbook|system)_/, '').replace(/_/g, ' '))) : []),
          ]
        })}
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
        <Accounts />
        <Security tick={tick} />
        <Ask onFiled={refresh} />
        <AddSource onSaved={refresh} patterns={pages.patterns} />
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

function AddSource({ onSaved, patterns = [] }) {
  const [open, setOpen] = useState(false)
  const [title, setTitle] = useState('')
  const [text, setText] = useState('')
  const [preview, setPreview] = useState(null)
  const [saved, setSaved] = useState(null)
  const [, setAuthTick] = useState(0)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [choice, setChoice] = useState('new') // new | existing | none
  const [target, setTarget] = useState('')
  const body = { title, text }
  const ready = title.trim().length >= 3 && text.trim().length >= 40

  const run = (fn, payload, then) => {
    setBusy(true); setError(null)
    fn(payload).then(then).catch((e) => setError(e.message)).finally(() => setBusy(false))
  }
  const np = preview?.proposal.new_pattern
  const notes = preview ? preview.proposal.pattern_notes.filter((n) => (n.note || '').trim()) : []
  const existing = patterns.filter((p) => !np || p !== np.id)
  const addTo = target || existing[0] || ''
  const merged = np && choice === 'existing' && addTo
    ? { pattern: addTo, note: `Related scheme, ${np.title}: ${np.definition}${np.signals.length ? ` Signals: ${np.signals.join('; ')}` : ''}` }
    : null
  const finalProposal = () => ({
    ...preview.proposal,
    pattern_notes: merged ? [...notes, merged] : notes,
    new_pattern: np && choice === 'new' ? np : null,
  })
  const changeList = () => {
    let list = preview.changes.map((c) => `${c.action} ${c.page}`)
    if (np && choice !== 'new') list = list.filter((x) => !x.endsWith(` ${np.id}`))
    if (merged && !list.some((x) => x.endsWith(` ${addTo}`))) list.push(`update ${addTo}`)
    return list.join(', ')
  }
  if (!open) return <button className="btn add" onClick={() => setOpen(true)}>+ Add a source document</button>

  return (
    <section className="card">
      <h3>Add a source document<small>the brain reads it and proposes page updates</small></h3>
      {saved ? (
        <p>Saved as <a className="wikilink" href={`#/brain/${saved.source_id}`}>{saved.source_id}</a>. Pages updated:{' '}
          {saved.changes.map((c) => c.page).join(', ')}.
          {saved.new_pattern_id && <> New pattern created: <a className="wikilink" href={`#/brain/${saved.new_pattern_id}`}>{saved.new_pattern_id}</a>.</>}</p>
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
                {notes.map((n, i) => (
                  <li key={i}><a className="wikilink" href={`#/brain/${n.pattern}`}>{n.pattern}</a>: {n.note}</li>
                ))}
              </ul>
              {preview.proposal.new_pattern && (
                <div className="newpattern">
                  <h4>New pattern proposed</h4>
                  <p>This document describes a scheme that is not in the library.</p>
                  <p><strong>{preview.proposal.new_pattern.title}</strong> ({preview.proposal.new_pattern.id}): {preview.proposal.new_pattern.definition}</p>
                  {preview.proposal.new_pattern.signals.length > 0 && (
                    <ul className="plain">
                      {preview.proposal.new_pattern.signals.map((x, i) => <li key={i}>Possible signal: {x}</li>)}
                    </ul>
                  )}
                  <label className="check">
                    <input type="radio" name="np" checked={choice === 'new'} onChange={() => setChoice('new')} />
                    Create this as a new pattern page
                  </label>
                  <label className="check">
                    <input type="radio" name="np" checked={choice === 'existing'} onChange={() => setChoice('existing')} />
                    Add it to an existing pattern instead:
                    <select value={addTo} onChange={(e) => { setTarget(e.target.value); setChoice('existing') }}>
                      {existing.map((p) => <option key={p} value={p}>{p.replace(/_/g, ' ')}</option>)}
                    </select>
                  </label>
                  <label className="check">
                    <input type="radio" name="np" checked={choice === 'none'} onChange={() => setChoice('none')} />
                    Neither: only save the document
                  </label>
                  {choice === 'new' && <small>It will be marked "knowledge only" until a detection rule is written for it.</small>}
                  {choice === 'existing' && <small>No new pattern is created. The scheme is added as a note on the {addTo.replace(/_/g, ' ')} page, citing this document.</small>}
                </div>
              )}
              {preview.security && preview.security.findings.length > 0 && (
                <div className="notice error" role="alert">
                  <strong>Document scanner: review before approving.</strong>
                  <ul className="plain">
                    {preview.security.findings.map((f, i) => <li key={i}>This text {f.message}: "{f.excerpt}"</li>)}
                  </ul>
                </div>
              )}
              {preview.security && preview.security.findings.length === 0 && <p className="sec-ok">Document scanner: no instruction-like text found.</p>}
              <h4>Pages that will change</h4>
              <p>{changeList()}</p>
              <SignIn onChange={() => setAuthTick((n) => n + 1)} />
              <button className="btn primary" disabled={!getSession() || busy}
                onClick={() => run(api.addSource, { ...body, proposal: finalProposal() }, (r) => { setSaved(r); onSaved() })}>Approve and save</button>
              <button className="btn" onClick={() => setPreview(null)}>Edit</button>
            </div>
          )}
        </>
      )}
    </section>
  )
}
