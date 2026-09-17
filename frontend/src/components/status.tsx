import type { CameraStatus, Protocol, SupportLevel } from '@/api/types'
import { Badge, cn } from '@/components/ui'

export const PROTOCOLS: Protocol[] = ['isapi', 'onvif', 'rtsp']

export const protocolMeta: Record<Protocol, { label: string; text: string; bg: string; hint: string }> = {
  isapi: { label: 'ISAPI', text: 'text-isapi', bg: 'bg-isapi', hint: 'API propietaria Hikvision' },
  onvif: { label: 'ONVIF', text: 'text-onvif', bg: 'bg-onvif', hint: 'Estándar de interoperabilidad' },
  rtsp: { label: 'RTSP', text: 'text-rtsp', bg: 'bg-rtsp', hint: 'Transporte de video' },
}

const statusMeta: Record<CameraStatus, { label: string; tone: 'ok' | 'warn' | 'bad' | 'neutral' }> = {
  online: { label: 'En línea', tone: 'ok' },
  degraded: { label: 'Parcial', tone: 'warn' },
  offline: { label: 'Sin conexión', tone: 'bad' },
  auth_error: { label: 'Credenciales', tone: 'bad' },
  unknown: { label: 'Sin probar', tone: 'neutral' },
}

export function StatusBadge({ status }: { status: CameraStatus }) {
  const meta = statusMeta[status]
  return (
    <Badge tone={meta.tone}>
      <span
        className={cn(
          'size-1.5 rounded-full',
          { ok: 'bg-ok', warn: 'bg-warn', bad: 'bg-bad', neutral: 'bg-muted' }[meta.tone],
          status === 'online' && 'animate-pulse',
        )}
      />
      {meta.label}
    </Badge>
  )
}

export const levelMeta: Record<SupportLevel, { label: string; className: string }> = {
  supported: { label: 'Soportada', className: 'bg-ok/15 text-ok border-ok/30' },
  partial: { label: 'Parcial', className: 'bg-warn/15 text-warn border-warn/30' },
  unsupported: { label: 'No soportada', className: 'bg-surface-2 text-muted border-line' },
  unverified: { label: 'Sin verificar', className: 'bg-surface-2 text-muted/70 border-dashed border-line' },
  error: { label: 'Error', className: 'bg-bad/15 text-bad border-bad/30' },
}

/** Luz de protocolo: verde si respondió, roja si falló, gris si nunca se probó. */
export function ProtocolLight({ protocol, level }: { protocol: Protocol; level?: SupportLevel }) {
  const meta = protocolMeta[protocol]
  const dot =
    level === 'supported'
      ? 'bg-ok shadow-[0_0_8px] shadow-ok/60'
      : level === 'error' || level === 'unsupported'
        ? 'bg-bad'
        : 'bg-line'
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-md border border-line bg-bg/60 px-2 py-1 font-mono text-[11px]"
      title={`${meta.hint}: ${level ? levelMeta[level].label : 'sin probar'}`}
    >
      <span className={cn('size-2 rounded-full', dot)} />
      <span className={meta.text}>{meta.label}</span>
    </span>
  )
}
