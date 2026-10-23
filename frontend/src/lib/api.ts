import type {
  ChatResponse,
  DocumentOut,
  HealthResponse,
  PipelineInfo,
  ProviderStatus,
  TraceSummary,
} from '../types/api'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api/v1'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), 30000)
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      signal: controller.signal,
      headers:
        init?.body instanceof FormData
          ? init.headers
          : { 'Content-Type': 'application/json', ...init?.headers },
    })
    const text = await response.text()
    const data = text ? JSON.parse(text) : null
    if (!response.ok) {
      throw new Error(data?.error ?? `Request failed with ${response.status}`)
    }
    return data as T
  } finally {
    window.clearTimeout(timeout)
  }
}

export const api = {
  health: () => request<HealthResponse>('/health'),
  providers: () => request<ProviderStatus>('/providers/status'),
  pipelines: () => request<PipelineInfo[]>('/pipelines'),
  documents: () => request<DocumentOut[]>('/documents'),
  uploadDocument: (file: File) => {
    const body = new FormData()
    body.append('file', file)
    return request<DocumentOut>('/documents', { method: 'POST', body })
  },
  deleteDocument: (id: string) => request<{ status: string }>(`/documents/${id}`, { method: 'DELETE' }),
  chat: (question: string, strategy: string, documentIds: string[], topK: number) =>
    request<ChatResponse>('/chat', {
      method: 'POST',
      body: JSON.stringify({
        question,
        strategy,
        document_ids: documentIds,
        top_k: topK,
      }),
    }),
  traces: () => request<TraceSummary[]>('/traces'),
}

