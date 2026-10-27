import type {
  ChatResponse,
  DocumentOut,
  HealthResponse,
  PipelineInfo,
  ProviderStatus,
  TraceSummary,
} from '../types/api'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api/v1'

type RequestOptions = RequestInit & {
  timeoutMs?: number
}

function errorMessageFromPayload(data: unknown, fallback: string) {
  if (!data || typeof data !== 'object') return fallback
  const payload = data as { error?: unknown; detail?: unknown; message?: unknown }
  if (typeof payload.error === 'string') return payload.error
  if (typeof payload.detail === 'string') return payload.detail
  if (typeof payload.message === 'string') return payload.message
  if (Array.isArray(payload.detail)) {
    const messages = payload.detail
      .map((item) => {
        if (!item || typeof item !== 'object') return ''
        const detail = item as { msg?: unknown }
        return typeof detail.msg === 'string' ? detail.msg : ''
      })
      .filter(Boolean)
    if (messages.length) return messages.join('; ')
  }
  return fallback
}

async function request<T>(path: string, init?: RequestOptions): Promise<T> {
  const { timeoutMs = 30000, ...fetchInit } = init ?? {}
  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs)
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...fetchInit,
      signal: controller.signal,
      headers:
        fetchInit.body instanceof FormData
          ? fetchInit.headers
          : { 'Content-Type': 'application/json', ...fetchInit.headers },
    })
    const text = await response.text()
    const data = text ? JSON.parse(text) : null
    if (!response.ok) {
      throw new Error(errorMessageFromPayload(data, `Request failed with ${response.status}`))
    }
    return data as T
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') {
      throw new Error('Request timed out. The backend may still be checking the model provider; try again in a moment.', {
        cause: err,
      })
    }
    throw err
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
      timeoutMs: 120000,
      body: JSON.stringify({
        question,
        strategy,
        document_ids: documentIds,
        top_k: topK,
      }),
    }),
  traces: () => request<TraceSummary[]>('/traces'),
}

