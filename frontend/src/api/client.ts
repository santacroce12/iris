import type {
  Camera,
  CameraCreate,
  CapabilityCheck,
  ConnectionReport,
  LiveUrls,
  OperationLog,
  StreamType,
  VideoProfile,
} from './types'

export class ApiError extends Error {
  readonly status: number
  readonly code: string

  constructor(status: number, code: string, message: string) {
    super(message)
    this.status = status
    this.code = code
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, {
    ...init,
    headers: init?.body ? { 'Content-Type': 'application/json', ...init.headers } : init?.headers,
  })
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new ApiError(
      response.status,
      body.error_code ?? 'http_error',
      body.message ?? body.detail?.[0]?.msg ?? `HTTP ${response.status}`,
    )
  }
  return response.status === 204 ? (undefined as T) : response.json()
}

const json = (body: unknown) => JSON.stringify(body)

export const api = {
  cameras: () => request<Camera[]>('/cameras'),
  camera: (id: string) => request<Camera>(`/cameras/${id}`),
  createCamera: (data: CameraCreate) =>
    request<Camera>('/cameras', { method: 'POST', body: json(data) }),
  deleteCamera: (id: string) => request<void>(`/cameras/${id}`, { method: 'DELETE' }),
  testConnection: (id: string) =>
    request<ConnectionReport>(`/cameras/${id}/connection-test`, { method: 'POST' }),
  profiles: (id: string) => request<VideoProfile[]>(`/cameras/${id}/profiles`),
  refreshProfiles: (id: string) =>
    request<VideoProfile[]>(`/cameras/${id}/profiles/refresh`, { method: 'POST' }),
  startLive: (id: string, stream: StreamType) =>
    request<LiveUrls>(`/cameras/${id}/live?stream=${stream}`, { method: 'POST' }),
  capabilities: (id: string) => request<CapabilityCheck[]>(`/cameras/${id}/capabilities`),
  operations: (id: string) => request<OperationLog[]>(`/cameras/${id}/operations`),
  snapshotUrl: (id: string) => `/api/cameras/${id}/snapshot?t=${Date.now()}`,
}
