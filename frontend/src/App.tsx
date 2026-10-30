import { useCallback, useEffect, useMemo, useState } from 'react'
import './App.css'
import { api } from './lib/api'
import type { ChatResponse, DocumentOut, HealthResponse, PipelineInfo, ProviderStatus, TraceSummary } from './types/api'

type NavItem = {
  id: string
  label: string
  icon: string
}

const navItems: NavItem[] = [
  { id: 'chat', label: 'Chat', icon: 'chat' },
  { id: 'hallucination', label: 'Hallucination', icon: 'shield' },
  { id: 'observability', label: 'Observability', icon: 'wave' },
  { id: 'metrics', label: 'Metrics', icon: 'bars' },
  { id: 'pipelines', label: 'Pipelines', icon: 'nodes' },
  { id: 'datasets', label: 'Datasets', icon: 'db' },
]

const fallbackQuestion = 'What are the main findings in these documents?'

function App() {
  const [activeView, setActiveView] = useState('chat')
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [providers, setProviders] = useState<ProviderStatus | null>(null)
  const [documents, setDocuments] = useState<DocumentOut[]>([])
  const [pipelines, setPipelines] = useState<PipelineInfo[]>([])
  const [traces, setTraces] = useState<TraceSummary[]>([])
  const [selectedDocuments, setSelectedDocuments] = useState<string[]>([])
  const [strategy, setStrategy] = useState('hybrid')
  const [topK, setTopK] = useState(5)
  const [question, setQuestion] = useState(fallbackQuestion)
  const [lastQuestion, setLastQuestion] = useState(fallbackQuestion)
  const [lastQuestionAt, setLastQuestionAt] = useState(() => new Date())
  const [lastAnswerAt, setLastAnswerAt] = useState(() => new Date())
  const [answer, setAnswer] = useState<ChatResponse | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [sending, setSending] = useState(false)
  const [now, setNow] = useState(() => new Date())

  const indexedDocuments = useMemo(() => documents.filter((document) => document.status === 'indexed'), [documents])
  const implementedPipelines = useMemo(() => pipelines.filter((pipeline) => pipeline.status !== 'planned'), [pipelines])
  const activeDocuments = selectedDocuments.length ? selectedDocuments : indexedDocuments.map((document) => document.id)
  const selectedPipeline = pipelines.find((pipeline) => pipeline.id === strategy)
  const sourceCount = answer?.citations.length ?? indexedDocuments.length

  const loadWorkspace = useCallback(async () => {
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
      setSelectedDocuments((current) => current.filter((id) => documentData.some((document) => document.id === id)))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not reach the backend')
    }
  }, [])

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadWorkspace()
    }, 0)
    return () => window.clearTimeout(timer)
  }, [loadWorkspace])

  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 30000)
    return () => window.clearInterval(timer)
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
    const submittedQuestion = question.trim()
    if (busy || sending || submittedQuestion.length < 2) return
    setBusy(true)
    setSending(true)
    setError('')
    setAnswer(null)
    setLastQuestion(submittedQuestion)
    setLastQuestionAt(new Date())
    setQuestion('')
    try {
      const response = await api.chat(submittedQuestion, strategy, activeDocuments, topK)
      setAnswer(response)
      setLastAnswerAt(new Date())
      setActiveView('chat')
      setTraces((current) => [
        {
          id: response.run_id,
          question: submittedQuestion,
          strategy: response.strategy,
          verdict: response.verdict,
          metrics: response.metrics,
          created_at: new Date().toISOString(),
        },
        ...current,
      ])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Chat request failed')
      setQuestion(submittedQuestion)
    } finally {
      setSending(false)
      setBusy(false)
    }
  }

  function toggleDocument(id: string) {
    setSelectedDocuments((current) => (current.includes(id) ? current.filter((item) => item !== id) : [...current, id]))
  }

  return (
    <div className="rag-shell">
      <header className="top-nav">
        <button className="brand" onClick={() => setActiveView('chat')} aria-label="RAGLab AI home">
          <span className="brand-cube" aria-hidden="true">
            <span />
            <span />
            <span />
          </span>
          <strong>RAGLab <em>AI</em></strong>
        </button>

        <nav className="main-tabs" aria-label="Primary navigation">
          {navItems.map((item) => (
            <button
              className={`nav-tab ${activeView === item.id ? 'active' : ''}`}
              key={item.id}
              onClick={() => setActiveView(item.id)}
            >
              <Icon name={item.icon} />
              {item.label}
              {item.id === 'hallucination' || item.id === 'observability' ? <span className="live-dot" /> : null}
            </button>
          ))}
        </nav>

        <div className="workspace-menu">
          <button className="workspace-pill">
            <span className={health?.status === 'ok' ? 'status-dot online' : 'status-dot'} />
            Local workspace
          </button>
          <button className="avatar-button">B</button>
        </div>
      </header>

      <div className="app-frame">
        <aside className="assistant-panel">
          <div className="assistant-hero">
            <div className="spark spark-one" />
            <div className="spark spark-two" />
            <Robot />
            <h1>Your RAG assistant</h1>
            <p>Grounded answers from your documents</p>
          </div>

          <label className="upload-card">
            <span className="file-icon">DOC</span>
            <span>
              <strong>Add your knowledge base</strong>
              <small>Drop PDF, TXT, DOCX or Markdown files</small>
            </span>
            <span className="upload-action">
              <Icon name="upload" />
              Upload documents
            </span>
            <input
              type="file"
              accept=".txt,.md,.markdown,.pdf,.html,.htm,.docx,.csv"
              onChange={(event) => void handleUpload(event.target.files?.[0])}
            />
          </label>

          <section className="side-section">
            <div className="section-heading">
              <strong>Uploaded documents</strong>
              <small>{documents.length} files</small>
            </div>
            <div className="document-stack">
              {documents.length === 0 ? (
                <div className="empty-docs">
                  <strong>No documents yet</strong>
                  <span>Upload a file to start indexing.</span>
                </div>
              ) : (
                documents.slice(0, 5).map((document) => (
                  <article className="document-row" key={document.id}>
                    <button
                      className={`doc-select ${selectedDocuments.includes(document.id) ? 'selected' : ''}`}
                      onClick={() => toggleDocument(document.id)}
                      aria-label={`Toggle ${document.filename}`}
                    >
                      <span className={`doc-file ${fileTone(document.filename)}`}>{fileLabel(document.filename)}</span>
                    </button>
                    <div>
                      <strong>{document.filename}</strong>
                      <small>{formatBytes(document.size_bytes)} | {document.chunk_count} chunks</small>
                    </div>
                    <span className={`mini-status ${document.status === 'indexed' ? 'good' : ''}`}>
                      {document.status === 'indexed' ? 'Indexed' : document.status}
                    </span>
                    <button className="row-menu" onClick={() => void handleDelete(document.id)} aria-label={`Delete ${document.filename}`}>
                      ...
                    </button>
                  </article>
                ))
              )}
            </div>
          </section>

          <section className="settings-panel">
            <div className="settings-title">
              <Icon name="gear" />
              <strong>Retrieval settings</strong>
            </div>
            <label>
              <span>Chunking strategy</span>
              <select value={strategy} onChange={(event) => setStrategy(event.target.value)}>
                {(implementedPipelines.length ? implementedPipelines : [{ id: 'hybrid', name: 'Hybrid RAG' }]).map((pipeline) => (
                  <option key={pipeline.id} value={pipeline.id}>{pipeline.name}</option>
                ))}
              </select>
            </label>
            <label>
              <span>Vector store</span>
              <select value="local" disabled>
                <option value="local">SQLite local adapter</option>
              </select>
            </label>
            <label>
              <span>Top K results</span>
              <input type="number" min={1} max={20} value={topK} onChange={(event) => setTopK(Number(event.target.value))} />
            </label>
            <button className="index-button" onClick={() => void loadWorkspace()} disabled={busy}>
              <Icon name="db" />
              Index documents
            </button>
          </section>
        </aside>

        <main className="content-panel">
          {error ? <div className="toast-error">{error}</div> : null}
          {busy ? <div className="busy-line" /> : null}

          {activeView === 'chat' ? (
            <section className="chat-workspace">
              <div className="chat-header">
                <div>
                  <h2><Icon name="chat" /> Chat with your knowledge base</h2>
                  <div className="chat-status-row">
                    <span className="ready-pill">
                      <span className={health?.status === 'ok' ? 'status-dot online' : 'status-dot'} />
                      {health?.status === 'ok' ? 'RAG pipeline ready' : 'Backend offline'}
                    </span>
                    <span className="source-note"><Icon name="db" /> {sourceCount} sources indexed</span>
                  </div>
                </div>
                <div className="chat-actions">
                  <button onClick={() => setAnswer(null)}><Icon name="trash" /> Clear chat</button>
                  <button onClick={() => setQuestion(fallbackQuestion)}><Icon name="plus" /> New conversation</button>
                </div>
              </div>

              <div className="chat-canvas">
                <div className="message-row user-row">
                  <div className="user-message">
                    <span className="avatar-small">B</span>
                    <span>{lastQuestion}</span>
                  </div>
                  <small title={formatAbsoluteTime(lastQuestionAt)}>{formatMessageTime(lastQuestionAt, now)}</small>
                </div>

                <div className="message-row assistant-row">
                  <Robot compact />
                  <article className="assistant-message">
                    {sending ? (
                      <ThinkingAnswer />
                    ) : answer ? (
                      <>
                        <FormattedAnswer text={answer.answer} />
                        {providerWarningMessages(answer.warnings).map((warning) => (
                          <small className="warning-line" key={warning}>{warning}</small>
                        ))}
                      </>
                    ) : (
                      <SeededAnswer strategy={selectedPipeline?.name ?? 'Hybrid RAG'} />
                    )}
                    <span className="message-time" title={formatAbsoluteTime(sending ? lastQuestionAt : lastAnswerAt)}>
                      {formatMessageTime(sending ? lastQuestionAt : lastAnswerAt, now)}
                    </span>
                  </article>
                </div>

                <section className="sources-strip">
                  <h3><Icon name="link" /> Sources</h3>
                  <div className="source-cards">
                    {answer?.citations.length ? (
                      answer.citations.slice(0, 3).map((citation) => (
                        <article className="source-card" key={citation.source_id}>
                          <span className="doc-file red">PDF</span>
                          <div>
                            <strong>{citation.filename}</strong>
                            <small>{citation.page ? `Page ${citation.page}` : citation.section ?? citation.chunk_id}</small>
                            <span className="mini-status good">Grounded</span>
                          </div>
                          <button aria-label={`Open ${citation.filename}`}>open</button>
                        </article>
                      ))
                    ) : indexedDocuments.length ? (
                      indexedDocuments.slice(0, 2).map((document) => (
                        <article className="source-card" key={document.id}>
                          <span className={`doc-file ${fileTone(document.filename)}`}>{fileLabel(document.filename)}</span>
                          <div>
                            <strong>{document.filename}</strong>
                            <small>{document.chunk_count} chunks</small>
                            <span className="mini-status good">Grounded</span>
                          </div>
                          <button aria-label={`Open ${document.filename}`}>open</button>
                        </article>
                      ))
                    ) : (
                      <article className="source-card empty-source">
                        <span className="doc-file blue">KB</span>
                        <div>
                          <strong>No sources indexed</strong>
                          <small>Upload documents to ground answers.</small>
                        </div>
                      </article>
                    )}
                  </div>
                </section>

                <form
                  className="composer"
                  onSubmit={(event) => {
                    event.preventDefault()
                    void askQuestion()
                  }}
                >
                  <Icon name="clip" />
                  <input value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Ask a question about your documents..." />
                  <button type="button" className="tune-button" onClick={() => setActiveView('pipelines')} aria-label="Open pipeline settings">
                    <Icon name="sliders" />
                  </button>
                  <button
                    type="submit"
                    className={`send-button ${sending ? 'sending' : ''}`}
                    disabled={busy || question.trim().length < 2}
                    aria-label={sending ? 'Sending question' : 'Send question'}
                  >
                    <Icon name="send" />
                    <span className="send-spinner" aria-hidden="true" />
                  </button>
                </form>
              </div>
            </section>
          ) : (
            <UtilityView
              activeView={activeView}
              documents={documents}
              health={health}
              pipelines={pipelines}
              providers={providers}
              traces={traces}
            />
          )}
        </main>
      </div>
    </div>
  )
}

function UtilityView({
  activeView,
  documents,
  health,
  pipelines,
  providers,
  traces,
}: {
  activeView: string
  documents: DocumentOut[]
  health: HealthResponse | null
  pipelines: PipelineInfo[]
  providers: ProviderStatus | null
  traces: TraceSummary[]
}) {
  if (activeView === 'pipelines') {
    return (
      <section className="utility-panel">
        <h2><Icon name="nodes" /> Pipelines</h2>
        <div className="pipeline-grid">
          {pipelines.map((pipeline) => (
            <article className="pipeline-card" key={pipeline.id}>
              <span className={`status-tag ${pipeline.status}`}>{pipeline.status}</span>
              <h3>{pipeline.name}</h3>
              <p>{pipeline.description}</p>
            </article>
          ))}
        </div>
      </section>
    )
  }

  if (activeView === 'datasets') {
    return (
      <section className="utility-panel">
        <h2><Icon name="db" /> Datasets</h2>
        <div className="metric-row">
          <Metric label="Indexed documents" value={documents.length.toString()} />
          <Metric label="Recorded runs" value={traces.length.toString()} />
          <Metric label="Backend" value={health?.status ?? 'offline'} />
        </div>
      </section>
    )
  }

  if (activeView === 'metrics') {
    return (
      <section className="utility-panel">
        <h2><Icon name="bars" /> Metrics</h2>
        <div className="metric-row">
          <Metric label="Runs" value={traces.length.toString()} />
          <Metric label="Provider" value={String(providers?.llm?.status ?? 'unknown')} />
          <Metric label="Vector store" value={String(providers?.vector_store?.provider ?? 'local')} />
        </div>
      </section>
    )
  }

  return (
    <section className="utility-panel">
      <h2><Icon name="wave" /> {activeView[0].toUpperCase() + activeView.slice(1)}</h2>
      <div className="trace-list">
        {traces.length ? traces.slice(0, 8).map((trace) => (
          <article className="trace-card" key={trace.id}>
            <strong>{trace.question}</strong>
            <small>{trace.strategy} | {trace.verdict} | {String(trace.metrics.latency_ms ?? 0)} ms</small>
          </article>
        )) : (
          <div className="empty-docs">
            <strong>No runs recorded</strong>
            <span>Ask a question to populate traces.</span>
          </div>
        )}
      </div>
    </section>
  )
}

function SeededAnswer({ strategy }: { strategy: string }) {
  const points = [
    ['RAG improves factual accuracy and reduces hallucinations', 'High-quality retrieval and reranking give the model grounded evidence.'],
    ['Hybrid retrieval performs best', 'Combining dense vectors with keyword search improves coverage for domain terms.'],
    ['Corrective RAG is effective', 'Weak evidence can trigger a bounded rewrite or fallback before answering.'],
    ['Evaluation is essential', 'Ragas, DeepEval, and custom metrics help compare faithfulness and citation coverage.'],
  ]
  return (
    <>
      <p>Based on the selected knowledge base, here are the main findings:</p>
      <ol>
        {points.map(([title, body]) => (
          <li key={title}>
            <strong>{title}</strong>
            <span> - {body}</span>
          </li>
        ))}
      </ol>
      <small className="strategy-note">{strategy} selected. Upload documents and send a question for live citations.</small>
    </>
  )
}

function ThinkingAnswer() {
  return (
    <div className="thinking-answer" aria-live="polite">
      <span />
      <div>
        <strong>Reading your sources</strong>
        <p>Retrieving relevant chunks and shaping the answer.</p>
      </div>
    </div>
  )
}

function FormattedAnswer({ text }: { text: string }) {
  const blocks = formatAnswerBlocks(text)
  if (!blocks.length) return <p>No answer was returned.</p>

  return (
    <div className="formatted-answer">
      {blocks.map((block, index) => {
        if (block.type === 'heading') {
          return <h4 key={`${block.type}-${index}`}>{block.text}</h4>
        }
        if (block.type === 'list') {
          return (
            <ul className={block.variant === 'sources' ? 'source-list' : undefined} key={`${block.type}-${index}`}>
              {block.items.map((item, itemIndex) => <li key={`${item}-${itemIndex}`}>{item}</li>)}
            </ul>
          )
        }
        if (block.type === 'source') {
          return <small className="answer-source" key={`${block.type}-${index}`}>{block.text}</small>
        }
        return <p key={`${block.type}-${index}`}>{block.text}</p>
      })}
    </div>
  )
}

type AnswerBlock =
  | { type: 'heading'; text: string }
  | { type: 'paragraph'; text: string }
  | { type: 'source'; text: string }
  | { type: 'list'; items: string[]; variant?: 'sources' }

function formatAnswerBlocks(text: string): AnswerBlock[] {
  const normalized = text
    .replace(/\r/g, '')
    .replace(/\s+\[(S\d+)\]/g, ' [$1]')
    .replace(/([.!?])\s+(?=(?:[-*]|\d+\.|\[[S]\d+\]))/g, '$1\n')
    .trim()

  const lines = normalized
    .split(/\n+/)
    .map((line) => line.replace(/\s+/g, ' ').trim())
    .filter(Boolean)

  const blocks: AnswerBlock[] = []
  let listItems: string[] = []
  let listVariant: 'sources' | undefined
  let currentSection = ''

  const flushList = () => {
    if (listItems.length) {
      blocks.push({ type: 'list', items: listItems, variant: listVariant })
      listItems = []
      listVariant = undefined
    }
  }

  for (const line of lines) {
    const heading = line.match(/^#{1,3}\s+(.+)$/)
    if (heading) {
      flushList()
      currentSection = cleanAnswerText(heading[1]).toLowerCase()
      blocks.push({ type: 'heading', text: cleanAnswerText(heading[1]) })
      continue
    }

    const bullet = line.match(/^(?:[-*]|\d+[.)])\s+(.+)$/)
    if (bullet) {
      listVariant = currentSection.includes('source') ? 'sources' : listVariant
      listItems.push(cleanAnswerText(bullet[1]))
      continue
    }

    flushList()
    const cleaned = cleanAnswerText(line)
    if (!cleaned) continue
    blocks.push(isSourceLine(cleaned) ? { type: 'source', text: cleaned } : { type: 'paragraph', text: cleaned })
  }

  flushList()
  return blocks
}

function cleanAnswerText(text: string) {
  return text
    .replace(/\s+([,.;:!?])/g, '$1')
    .replace(/\s{2,}/g, ' ')
    .trim()
}

function isSourceLine(text: string) {
  return text.startsWith('[S') || text.toLowerCase().startsWith('sources used:')
}

function providerWarningMessages(warnings: string[]) {
  const messages = warnings.map((warning) => {
    const lower = warning.toLowerCase()
    if (lower.includes('connecterror') || lower.includes('network error')) {
      return 'Groq is currently unreachable, so RAGLab used local extractive synthesis for this answer.'
    }
    if (lower.includes('rate limit')) {
      return 'Groq rate limit reached, so this answer used local extractive synthesis.'
    }
    if (lower.includes('api key') || lower.includes('rejected')) {
      return 'Groq credentials need attention. This answer used local extractive synthesis.'
    }
    return warning
  })
  return Array.from(new Set(messages))
}

function formatMessageTime(date: Date, now: Date) {
  const seconds = Math.max(0, Math.floor((now.getTime() - date.getTime()) / 1000))
  if (seconds < 45) return 'Just now'
  if (seconds < 90) return '1 min ago'
  if (seconds < 3600) return `${Math.floor(seconds / 60)} min ago`
  return date.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })
}

function formatAbsoluteTime(date: Date) {
  return date.toLocaleString([], {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

function Robot({ compact = false }: { compact?: boolean }) {
  return (
    <div className={compact ? 'robot compact' : 'robot'} aria-hidden="true">
      <span className="antenna" />
      <span className="ear left" />
      <span className="ear right" />
      <span className="face">
        <span />
        <span />
      </span>
    </div>
  )
}

function Icon({ name }: { name: string }) {
  return <span className={`icon icon-${name}`} aria-hidden="true" />
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <article className="metric-card">
      <small>{label}</small>
      <strong>{value}</strong>
    </article>
  )
}

function fileLabel(filename: string) {
  const extension = filename.split('.').pop()?.toUpperCase() ?? 'DOC'
  if (extension.length > 4) return extension.slice(0, 4)
  return extension
}

function fileTone(filename: string) {
  const extension = filename.split('.').pop()?.toLowerCase()
  if (extension === 'pdf') return 'red'
  if (extension === 'docx' || extension === 'doc') return 'blue'
  if (extension === 'md' || extension === 'markdown') return 'dark'
  return 'gold'
}

function formatBytes(value: number) {
  if (value < 1024) return `${value} B`
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`
  return `${(value / (1024 * 1024)).toFixed(1)} MB`
}

export default App
