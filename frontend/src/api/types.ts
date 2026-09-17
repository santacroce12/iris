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
