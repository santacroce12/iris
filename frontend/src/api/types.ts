export type Protocol = 'isapi' | 'onvif' | 'rtsp'
export type CameraStatus = 'unknown' | 'online' | 'degraded' | 'offline' | 'auth_error'
export type SupportLevel = 'supported' | 'partial' | 'unsupported' | 'unverified' | 'error'
export type NetworkMode = 'lan' | 'vpn'
export type StreamType = 'main' | 'sub' | 'other'

export interface Camera {
  id: string
  name: string
  host: string
  http_port: number
  use_https: boolean
  verify_tls: boolean
  rtsp_port: number
  onvif_port: number
  channel: number
  username: string
  onvif_username: string | null
  network_mode: NetworkMode
  vendor: string | null
  model: string | null
  serial: string | null
  firmware: string | null
  mac: string | null
  vca_mode: string | null
  status: CameraStatus
  last_seen_at: string | null
  listen_events: boolean
  created_at: string
}

export interface CameraCreate {
  name: string
  host: string
  http_port: number
  use_https: boolean
  rtsp_port: number
  onvif_port: number
  channel: number
  username: string
  password: string
  onvif_username?: string | null
  onvif_password?: string | null
  network_mode: NetworkMode
}

/** PATCH: solo viajan los campos presentes; contraseñas ausentes = conservar las guardadas. */
export type CameraUpdate = Partial<CameraCreate>

export interface ProtocolCheck {
  ok: boolean
  latency_ms: number
  error_code: string | null
  message: string | null
  details: Record<string, unknown>
}

export interface ConnectionReport {
  status: CameraStatus
  isapi: ProtocolCheck
  onvif: ProtocolCheck
  rtsp: ProtocolCheck
}

export interface VideoProfile {
  id: string
  protocol: Protocol
  token: string
  name: string | null
  stream_type: StreamType
  codec: string | null
  width: number | null
  height: number | null
  fps: number | null
  bitrate_kbps: number | null
  rtsp_path: string | null
}

export interface LiveUrls {
  path: string
  webrtc: string
  whep: string
  hls: string
}

export interface EventMedia {
  id: string
  kind: string
  mime: string
  bytes: number
}

/** Un evento es un episodio: duró de occurred_at a ended_at y la cámara avisó `hits` veces. */
export interface CameraEvent {
  id: string
  camera_id: string
  protocol: Protocol
  raw_type: string
  type: string
  state: string | null
  channel: number | null
  occurred_at: string
  ended_at: string | null
  received_at: string
  hits: number
  rule_ref: string | null
  target_type: string | null
  payload: Record<string, unknown> | null
  media: EventMedia[]
}

/** Lo que llega por SSE cuando un episodio se abre o se actualiza. */
export interface LiveEvent {
  id: string
  camera_id: string
  type: string
  raw_type: string
  state: string | null
  channel: number | null
  occurred_at: string
  ended_at: string | null
  hits: number
  rule_ref: string | null
  target_type: string | null
  pictures: number
}

export interface ListenerState {
  camera_id: string
  status: string
  connected_since: string | null
  alerts_received: number
  episodes_saved: number
  open_episodes: number
  last_error: string | null
}

export interface EventFilters {
  camera_id?: string
  type?: string
  target_type?: string
  since?: string
  until?: string
  limit?: number
}

export interface CapabilityCheck {
  capability_code: string
  protocol: Protocol
  level: SupportLevel
  source: 'declared' | 'verified'
  evidence: Record<string, unknown> | null
  latency_ms: number | null
  checked_at: string
}

export interface OperationLog {
  id: string
  capability_code: string
  protocol: Protocol
  operation: string
  http_status: number | null
  success: boolean
  latency_ms: number | null
  error_code: string | null
  detail: Record<string, unknown> | null
  created_at: string
}
