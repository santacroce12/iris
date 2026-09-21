import type { LucideIcon } from 'lucide-react'
import {
  Activity,
  AudioLines,
  Car,
  Eye,
  Footprints,
  LogIn,
  LogOut,
  Luggage,
  MoveRight,
  PackageOpen,
  ShieldAlert,
  Siren,
  Sparkles,
  Users,
} from 'lucide-react'

interface EventMeta {
  label: string
  icon: LucideIcon
  /** Los eventos de analítica se destacan; los técnicos quedan en gris. */
  className: string
  analytic: boolean
}

const NEUTRO = 'text-muted bg-surface-2 border-line'

export const EVENT_TYPES: Record<string, EventMeta> = {
  line_crossing: { label: 'Cruce de línea', icon: MoveRight, className: 'text-rtsp bg-rtsp/10 border-rtsp/30', analytic: true },
  intrusion: { label: 'Intrusión', icon: ShieldAlert, className: 'text-bad bg-bad/10 border-bad/30', analytic: true },
  region_entrance: { label: 'Entra a zona', icon: LogIn, className: 'text-onvif bg-onvif/10 border-onvif/30', analytic: true },
  region_exiting: { label: 'Sale de zona', icon: LogOut, className: 'text-onvif bg-onvif/10 border-onvif/30', analytic: true },
  loitering: { label: 'Merodeo', icon: Footprints, className: 'text-warn bg-warn/10 border-warn/30', analytic: true },
  people_gathering: { label: 'Aglomeración', icon: Users, className: 'text-warn bg-warn/10 border-warn/30', analytic: true },
  unattended_baggage: { label: 'Objeto abandonado', icon: Luggage, className: 'text-warn bg-warn/10 border-warn/30', analytic: true },
  object_removal: { label: 'Objeto retirado', icon: PackageOpen, className: 'text-warn bg-warn/10 border-warn/30', analytic: true },
  ai_rule: { label: 'Regla de IA', icon: Sparkles, className: 'text-ok bg-ok/10 border-ok/30', analytic: true },
  face_capture: { label: 'Rostro', icon: Eye, className: 'text-ok bg-ok/10 border-ok/30', analytic: true },
  anpr: { label: 'Patente', icon: Car, className: 'text-ok bg-ok/10 border-ok/30', analytic: true },
  mixed_target: { label: 'Objetivo detectado', icon: Sparkles, className: 'text-ok bg-ok/10 border-ok/30', analytic: true },
  motion: { label: 'Movimiento', icon: Activity, className: 'text-isapi bg-isapi/10 border-isapi/30', analytic: false },
  tamper: { label: 'Sabotaje', icon: Siren, className: 'text-bad bg-bad/10 border-bad/30', analytic: false },
  scene_change: { label: 'Cambio de escena', icon: Activity, className: NEUTRO, analytic: false },
  defocus: { label: 'Desenfoque', icon: Eye, className: NEUTRO, analytic: false },
  audio_exception: { label: 'Audio anómalo', icon: Activity, className: NEUTRO, analytic: false },
  sound_classification: { label: 'Sonido clasificado', icon: AudioLines, className: 'text-ok bg-ok/10 border-ok/30', analytic: true },
  io: { label: 'Entrada de alarma', icon: Activity, className: NEUTRO, analytic: false },
}

export function eventMeta(type: string): EventMeta {
  return EVENT_TYPES[type] ?? { label: type, icon: Activity, className: NEUTRO, analytic: false }
}

export function targetLabel(target: string | null): string | null {
  if (!target) return null
  const nombres: Record<string, string> = { human: 'persona', vehicle: 'vehículo', others: 'otro' }
  return target
    .split(',')
    .map((t) => nombres[t.trim()] ?? t.trim())
    .filter(Boolean)
    .join(' + ')
}

/** "hace 5 s", "hace 3 min": el feed necesita tiempo relativo. */
export function sinceLabel(iso: string): string {
  const segundos = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 1000))
  if (segundos < 60) return `hace ${segundos} s`
  if (segundos < 3600) return `hace ${Math.floor(segundos / 60)} min`
  if (segundos < 86400) return `hace ${Math.floor(segundos / 3600)} h`
  return new Date(iso).toLocaleDateString()
}

export function durationLabel(desde: string, hasta: string | null): string {
  const fin = hasta ? new Date(hasta).getTime() : Date.now()
  const segundos = Math.max(1, Math.round((fin - new Date(desde).getTime()) / 1000))
  if (segundos < 60) return `${segundos} s`
  const minutos = Math.floor(segundos / 60)
  return `${minutos} min ${segundos % 60} s`
}
