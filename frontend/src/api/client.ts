import type {
  Camera,
  DeviceTime,
  CameraCreate,
  CameraEvent,
  CameraUpdate,
  EventFilters,
  ListenerState,
  CameraFunctions,
  CapabilityCheck,
  ConfigBackup,
  ConnectionReport,
  ImageSettings,
  LiveUrls,
  Matrix,
  MotionDetection,
  OperationLog,
  Osd,
  Recording,
  Rule,
  RuleKind,
  RulePatch,
  RuleSet,
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
  updateCamera: (id: string, data: CameraUpdate) =>
    request<Camera>(`/cameras/${id}`, { method: 'PATCH', body: json(data) }),
  deleteCamera:(id: string) => request<void>(`/cameras/${id}`, { method: 'DELETE' }),
  testConnection: (id: string) =>
    request<ConnectionReport>(`/cameras/${id}/connection-test`, { method: 'POST' }),
  profiles: (id: string) => request<VideoProfile[]>(`/cameras/${id}/profiles`),
  refreshProfiles: (id: string) =>
    request<VideoProfile[]>(`/cameras/${id}/profiles/refresh`, { method: 'POST' }),
  startLive: (id: string, stream: StreamType) =>
    request<LiveUrls>(`/cameras/${id}/live?stream=${stream}`, { method: 'POST' }),
  capabilities: (id: string) => request<CapabilityCheck[]>(`/cameras/${id}/capabilities`),
  recording: (id: string, stream: StreamType = 'main') =>
    request<Recording>(`/cameras/${id}/recording?stream=${stream}`),
  setRecording: (id: string, enabled: boolean, stream: StreamType = 'main') =>
    request<Recording>(`/cameras/${id}/recording?enabled=${enabled}&stream=${stream}`, {
      method: 'POST',
    }),
  operations: (id: string) => request<OperationLog[]>(`/cameras/${id}/operations`),
  rules: (id: string) => request<RuleSet>(`/cameras/${id}/rules`),
  patchRule: (id: string, kind: RuleKind, ruleId: string, patch: RulePatch) =>
    request<Rule>(`/cameras/${id}/rules/${kind}/${ruleId}`, {
      method: 'PATCH',
      body: json(patch),
    }),
  backups: (id: string) => request<ConfigBackup[]>(`/cameras/${id}/backups`),

  matrix: () => request<Matrix>('/matrix'),
  detect: (id: string) =>
    request<{ status: string }>(`/cameras/${id}/capabilities/detect`, { method: 'POST' }),
  functions: (id: string, protocol: 'isapi' | 'onvif' = 'isapi') =>
    request<CameraFunctions>(`/cameras/${id}/functions?protocol=${protocol}`),
  setOsd: (id: string, patch: Partial<Osd>) =>
    request<Osd>(`/cameras/${id}/functions/osd`, { method: 'PATCH', body: json(patch) }),
  setImage: (id: string, patch: Partial<ImageSettings>) =>
    request<ImageSettings>(`/cameras/${id}/functions/image`, {
      method: 'PATCH',
      body: json(patch),
    }),
  setMotion: (id: string, patch: Partial<MotionDetection>) =>
    request<MotionDetection>(`/cameras/${id}/functions/motion`, {
      method: 'PATCH',
      body: json(patch),
    }),
  syncTime: (id: string, protocol: 'isapi' | 'onvif' = 'isapi') =>
    request<DeviceTime>(`/cameras/${id}/functions/time/sync?protocol=${protocol}`, {
      method: 'POST',
    }),
  reboot: (id: string, protocol: 'isapi' | 'onvif' = 'isapi') =>
    request<Record<string, unknown>>(
      `/cameras/${id}/functions/reboot?confirm=true&protocol=${protocol}`,
      { method: 'POST' },
    ),
  restoreBackup: (id: string, backupId: string) =>
    request<void>(`/cameras/${id}/backups/${backupId}/restore`, { method: 'POST' }),
  snapshotUrl: (id: string) => `/api/cameras/${id}/snapshot?t=${Date.now()}`,

  events: (filters: EventFilters = {}) => {
    const query = new URLSearchParams(
      Object.entries(filters).filter(([, v]) => v !== undefined && v !== '') as [string, string][],
    )
    return request<CameraEvent[]>(`/events?${query}`)
  },
  eventPictureUrl: (eventId: string, mediaId: string) =>
    `/api/events/${eventId}/media/${mediaId}`,
  listeners: () => request<ListenerState[]>('/listeners'),
  startListener: (cameraId: string) =>
    request<ListenerState>(`/cameras/${cameraId}/listener`, { method: 'POST' }),
  stopListener: (cameraId: string) =>
    request<void>(`/cameras/${cameraId}/listener`, { method: 'DELETE' }),
}
