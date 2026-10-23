import { useEffect, useMemo, useState } from 'react'
import './App.css'
import { api } from './lib/api'
import type { ChatResponse, DocumentOut, HealthResponse, PipelineInfo, ProviderStatus, TraceSummary } from './types/api'

function App() {
  const [activeView, setActiveView] = useState('overview')
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [providers, setProviders] = useState<ProviderStatus | null>(null)
  const [documents, setDocuments] = useState<DocumentOut[]>([])
  const [pipelines, setPipelines] = useState<PipelineInfo[]>([])
  const [traces, setTraces] = useState<TraceSummary[]>([])
  const [selectedDocuments, setSelectedDocuments] = useState<string[]>([])
  const [strategy, setStrategy] = useState('hybrid')
  const [topK, setTopK] = useState(5)
  const [question, setQuestion] = useState('What does this knowledge base say?')
  const [answer, setAnswer] = useState<ChatResponse | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const indexedDocuments = useMemo(() => documents.filter((document) => document.status === 'indexed'), [documents])
  const implementedPipelines = useMemo(() => pipelines.filter((pipeline) => pipeline.status !== 'planned'), [pipelines])

  async function loadWorkspace() {
    setError('')
    try {
      const [healthData, providerData, documentData, pipelineData, traceData] = await Promise.all([
        api.health(),
        api.providers(),
        api.documents(),
        api.pipelines(),
        api.traces(),
      ])
      setHealth(healthData)
      setProviders(providerData)
      setDocuments(documentData)
      setPipelines(pipelineData)
      setTraces(traceData)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not reach the backend')
    }
  }

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadWorkspace()
    }, 0)
    return () => window.clearTimeout(timer)
  }, [])

  async function handleUpload(file: File | undefined) {
    if (!file) return
    setBusy(true)
    setError('')
    try {
      const document = await api.uploadDocument(file)
      setDocuments((current) => [document, ...current.filter((item) => item.id !== document.id)])
      setSelectedDocuments((current) => (current.includes(document.id) ? current : [...current, document.id]))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setBusy(false)
    }
  }

  async function handleDelete(id: string) {
    setBusy(true)
    setError('')
    try {
      await api.deleteDocument(id)
      setDocuments((current) => current.filter((document) => document.id !== id))
      setSelectedDocuments((current) => current.filter((documentId) => documentId !== id))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Delete failed')
    } finally {
      setBusy(false)
    }
  }

  async function askQuestion() {
    setBusy(true)
    setError('')
    try {
      const response = await api.chat(question, strategy, selectedDocuments, topK)
      setAnswer(response)
      setActiveView('chat')
      setTraces((current) => [
        {
          id: response.run_id,
          question,
          strategy: response.strategy,
          verdict: response.verdict,
          metrics: response.metrics,
          created_at: new Date().toISOString(),
        },
        ...current,
      ])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Chat request failed')
    } finally {
      setBusy(false)
    }
  }

  function toggleDocument(id: string) {
    setSelectedDocuments((current) => (current.includes(id) ? current.filter((item) => item !== id) : [...current, id]))
  }

  const navItems = [
    ['overview', 'Overview'],
    ['sources', 'Sources'],
    ['chat', 'Chat'],
    ['pipelines', 'Pipelines'],
    ['traces', 'Traces'],
    ['evaluation', 'Evaluation'],
    ['settings', 'Settings'],
  ]

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-mark">
          <span className="brand-icon">RL</span>
          <div>
            <strong>RAGLab AI</strong>
            <small>Research workbench</small>
          </div>
        </div>
        <nav>
          {navItems.map(([id, label]) => (
            <button className={activeView === id ? 'active' : ''} key={id} onClick={() => setActiveView(id)}>
              {label}
            </button>
          ))}
        </nav>
        <div className="sidebar-status">
          <span className={health?.status === 'ok' ? 'dot ok' : 'dot'} />
          <div>
            <strong>{health?.status === 'ok' ? 'Backend online' : 'Backend offline'}</strong>
            <small>{providers?.llm?.status?.toString() ?? 'Provider status unknown'}</small>
          </div>
        </div>
      </aside>

      <main className="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">Evidence-first retrieval lab</p>
            <h1>{navItems.find(([id]) => id === activeView)?.[1]}</h1>
          </div>
          <div className="topbar-actions">
            <button onClick={() => void loadWorkspace()} disabled={busy}>Refresh</button>
            <label className="upload-button">
              Upload
              <input
                type="file"
                accept=".txt,.md,.markdown,.pdf,.html,.htm,.docx,.csv"
                onChange={(event) => void handleUpload(event.target.files?.[0])}
              />
            </label>
          </div>
        </header>

        {error ? <div className="alert">{error}</div> : null}
        {busy ? <div className="progress-bar" /> : null}

        {activeView === 'overview' ? (
          <section className="dashboard-grid">
            <Metric label="Documents" value={documents.length.toString()} detail={`${indexedDocuments.length} indexed`} />
            <Metric label="Runs" value={traces.length.toString()} detail="stored locally" />
            <Metric label="Strategies" value={pipelines.length.toString()} detail={`${implementedPipelines.length} runnable`} />
            <Metric label="Grok" value={health?.grok_configured ? 'Ready' : 'Fallback'} detail="secrets stay server-side" />
            <div className="wide-panel blueprint">
              <div className="phone-visual" aria-hidden="true">
                <div className="phone-header" />
                <div className="bubble right" />
                <div className="avatar" />
                <div className="bubble left" />
                <div className="phone-footer" />
              </div>
              <div>
                <p className="eyebrow">Reference-matched layout</p>
                <h2>Upload, retrieve, inspect, compare.</h2>
                <p>
                  This workspace keeps the screenshot's calm blue panel language while turning it into a dense RAG
                  operations surface with source status, strategy selection, citations, traces, and provider health.
                </p>
              </div>
            </div>
          </section>
        ) : null}

        {activeView === 'sources' ? (
          <section className="panel-list">
            {documents.length === 0 ? <Empty title="No documents indexed" detail="Upload TXT, Markdown, PDF, HTML, DOCX, or CSV to begin." /> : null}
            {documents.map((document) => (
              <article className="row-panel" key={document.id}>
                <input
                  type="checkbox"
                  checked={selectedDocuments.includes(document.id)}
                  onChange={() => toggleDocument(document.id)}
                  aria-label={`Select ${document.filename}`}
                />
                <div>
                  <strong>{document.filename}</strong>
                  <small>{document.chunk_count} chunks | {formatBytes(document.size_bytes)} | {document.status}</small>
                  {document.error ? <p className="error-text">{document.error}</p> : null}
                </div>
                <button onClick={() => void handleDelete(document.id)} disabled={busy}>Delete</button>
              </article>
            ))}
          </section>
        ) : null}

        {activeView === 'chat' ? (
          <section className="chat-layout">
            <div className="chat-main">
              <textarea value={question} onChange={(event) => setQuestion(event.target.value)} />
              <div className="control-row">
                <select value={strategy} onChange={(event) => setStrategy(event.target.value)}>
                  {implementedPipelines.map((pipeline) => (
                    <option key={pipeline.id} value={pipeline.id}>{pipeline.name}</option>
                  ))}
                </select>
                <label>
                  Top K
                  <input type="number" min={1} max={20} value={topK} onChange={(event) => setTopK(Number(event.target.value))} />
                </label>
                <button className="primary" onClick={() => void askQuestion()} disabled={busy || question.length < 2}>Ask</button>
              </div>
              <article className="answer-panel">
                <p className="eyebrow">{answer ? `${answer.strategy} | ${answer.verdict}` : 'Answer'}</p>
                <p>{answer?.answer ?? 'Ask a question to see grounded output with citations.'}</p>
                {answer?.warnings.map((warning) => <small className="warning" key={warning}>{warning}</small>)}
              </article>
            </div>
            <aside className="evidence-panel">
              <h2>Evidence</h2>
              {answer?.citations.length ? answer.citations.map((citation) => (
                <article className="citation-card" key={citation.source_id}>
                  <strong>{citation.source_id} | {citation.filename}</strong>
                  <p>{citation.quote}</p>
                  <small>{citation.page ? `Page ${citation.page}` : citation.section ?? citation.chunk_id}</small>
                </article>
              )) : <Empty title="No evidence yet" detail="Run a question after indexing documents." />}
            </aside>
          </section>
        ) : null}

        {activeView === 'pipelines' ? (
          <section className="pipeline-grid">
            {pipelines.map((pipeline) => (
              <article className="pipeline-card" key={pipeline.id}>
                <span className={`badge ${pipeline.status}`}>{pipeline.status}</span>
                <h2>{pipeline.name}</h2>
                <p>{pipeline.description}</p>
                <small>{pipeline.uses_langgraph ? 'LangGraph workflow' : 'Shared pipeline interface'}</small>
              </article>
            ))}
          </section>
        ) : null}

        {activeView === 'traces' ? (
          <section className="trace-grid">
            <div className="panel-list">
              {traces.length === 0 ? <Empty title="No runs recorded" detail="Chat runs will appear here." /> : null}
              {traces.map((trace) => (
                <article className="row-panel" key={trace.id}>
                  <div>
                    <strong>{trace.question}</strong>
                    <small>{trace.strategy} | {trace.verdict} | {String(trace.metrics.latency_ms ?? 0)} ms</small>
                  </div>
                </article>
              ))}
            </div>
            <div className="trace-timeline">
              {(answer?.trace ?? []).map((event) => (
                <article key={`${event.node}-${event.elapsed_ms}`}>
                  <span className={`dot ${event.status === 'ok' ? 'ok' : ''}`} />
                  <div>
                    <strong>{event.node}</strong>
                    <small>{event.message || `${Math.round(event.elapsed_ms ?? 0)} ms`}</small>
                  </div>
                </article>
              ))}
            </div>
          </section>
        ) : null}

        {activeView === 'evaluation' ? (
          <section className="wide-panel">
            <div>
              <p className="eyebrow">Deterministic metrics</p>
              <h2>Dataset and experiment APIs are ready.</h2>
              <p>
                The backend can create datasets and run strategy comparisons from actual RAG calls. The UI currently
                exposes the experiment status surface; full dataset editing is the next incremental screen.
              </p>
            </div>
          </section>
        ) : null}

        {activeView === 'settings' ? (
          <section className="settings-grid">
            {providers ? Object.entries(providers).map(([name, value]) => (
              <article className="settings-card" key={name}>
                <h2>{name.replace('_', ' ')}</h2>
                <pre>{JSON.stringify(value, null, 2)}</pre>
              </article>
            )) : <Empty title="Settings unavailable" detail="Start the backend and refresh." />}
          </section>
        ) : null}
      </main>
    </div>
  )
}

function Metric({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <article className="metric-card">
      <small>{label}</small>
      <strong>{value}</strong>
      <span>{detail}</span>
    </article>
  )
}

function Empty({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="empty-state">
      <strong>{title}</strong>
      <span>{detail}</span>
    </div>
  )
}

function formatBytes(value: number) {
  if (value < 1024) return `${value} B`
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`
  return `${(value / (1024 * 1024)).toFixed(1)} MB`
}

export default App
