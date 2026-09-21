import { FileCode, ImageOff, MousePointerClick } from 'lucide-react'

import { api } from '@/api/client'
import type { CameraEvent } from '@/api/types'
import { protocolMeta } from '@/components/status'
import { Card, EmptyState, cn } from '@/components/ui'
import { durationLabel, eventMeta, targetLabel } from '@/features/events/eventTypes'

/** Panel lateral: el evento normalizado y, abajo, lo que mandó la cámara tal cual. */
export function EventDetail({ evento, camara }: { evento: CameraEvent | null; camara?: string }) {
  if (!evento) {
    return (
      <div className="hidden lg:block">
        <EmptyState icon={<MousePointerClick className="size-7" />} title="Elegí un evento">
          Vas a ver su foto, los datos normalizados y el mensaje original de la cámara.
        </EmptyState>
      </div>
    )
  }

  const meta = eventMeta(evento.type)
  const Icon = meta.icon
  const filas: [string, string | number | null][] = [
    ['Cámara', camara ?? evento.camera_id],
    ['Inicio', new Date(evento.occurred_at).toLocaleString()],
    ['Fin', evento.ended_at ? new Date(evento.ended_at).toLocaleString() : 'en curso'],
    ['Duración', durationLabel(evento.occurred_at, evento.ended_at)],
    ['Avisos agrupados', evento.hits],
    ['Canal', evento.channel],
    ['Regla', evento.rule_ref],
    ['Objetivo', targetLabel(evento.target_type)],
    ['Tipo original', evento.raw_type],
  ]

  return (
    <Card className="h-fit overflow-hidden lg:sticky lg:top-6">
      <div className={cn('flex items-center gap-3 border-b px-4 py-3', meta.className)}>
        <Icon className="size-5" />
        <div>
          <p className="font-semibold">{meta.label}</p>
          <p className={cn('font-mono text-[11px]', protocolMeta[evento.protocol].text)}>
            vía {protocolMeta[evento.protocol].label} · alertStream
          </p>
        </div>
      </div>

      {evento.media.length ? (
        <div className="grid grid-cols-2 gap-1 bg-bg p-1">
          {evento.media.map((m) => (
            <a key={m.id} href={api.eventPictureUrl(evento.id, m.id)} target="_blank" rel="noreferrer">
              <img
                src={api.eventPictureUrl(evento.id, m.id)}
                alt="Foto del evento"
                className="aspect-video w-full rounded object-cover"
              />
            </a>
          ))}
        </div>
      ) : (
        <p className="flex items-center gap-2 border-b border-line bg-bg px-4 py-3 text-xs text-muted">
          <ImageOff className="size-4" /> La cámara no adjuntó foto a este evento.
        </p>
      )}

      <dl className="divide-y divide-line/60 text-sm">
        {filas
          .filter(([, v]) => v !== null && v !== undefined && v !== '')
          .map(([k, v]) => (
            <div key={k} className="flex justify-between gap-4 px-4 py-2">
              <dt className="text-muted">{k}</dt>
              <dd className="text-right font-mono text-xs">{v}</dd>
            </div>
          ))}
      </dl>

      {evento.payload && (
        <details className="border-t border-line">
          <summary className="flex cursor-pointer items-center gap-2 px-4 py-3 text-xs text-muted select-none">
            <FileCode className="size-4" /> Mensaje original de la cámara
          </summary>
          <pre className="max-h-72 overflow-auto bg-bg px-4 py-3 font-mono text-[11px] leading-relaxed text-muted">
            {JSON.stringify(evento.payload, null, 2)}
          </pre>
        </details>
      )}
    </Card>
  )
}
