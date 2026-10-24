export type HealthResponse = {
  status: string
  app: string
  environment: string
  database: string
  groq_configured: boolean
  langsmith_configured: boolean
  configured_secret_names: string[]
  checked_at: string
}

export type DocumentOut = {
  id: string
  filename: string
  content_type: string
  status: string
  size_bytes: number
  content_hash: string
  chunk_count: number
  error: string | null
  created_at: string
  updated_at: string
}

export type Citation = {
  source_id: string
  document_id: string
  filename: string
  page: number | null
  section: string | null
  chunk_id: string
  quote: string
}

export type RetrievedChunk = {
  chunk_id: string
  document_id: string
  filename: string
  text: string
  score: number
  dense_score: number | null
  lexical_score: number | null
  page: number | null
  section: string | null
}

export type TraceEvent = {
  node: string
  status: string
  message: string
  metadata: Record<string, unknown>
  elapsed_ms: number | null
}

export type ChatResponse = {
  run_id: string
  strategy: string
  answer: string
  citations: Citation[]
  retrieved_chunks: RetrievedChunk[]
  verdict: string
  metrics: Record<string, unknown>
  trace: TraceEvent[]
  usage: Record<string, unknown>
  warnings: string[]
}

export type PipelineInfo = {
  id: string
  name: string
  status: 'implemented' | 'experimental' | 'planned'
  description: string
  uses_langgraph: boolean
}

export type ProviderStatus = {
  llm: Record<string, unknown>
  embeddings: Record<string, unknown>
  vector_store: Record<string, unknown>
  x_api: Record<string, unknown>
  langsmith: Record<string, unknown>
}

export type TraceSummary = {
  id: string
  question: string
  strategy: string
  verdict: string
  metrics: Record<string, unknown>
  created_at: string
}

