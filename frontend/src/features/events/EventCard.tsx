import { Clock, Layers, Target } from 'lucide-react'

import { api } from '@/api/client'
import type { CameraEvent } from '@/api/types'
import { Badge, cn } from '@/components/ui'
import { durationLabel, eventMeta, sinceLabel, targetLabel } from '@/features/events/eventTypes'

export function EventCard({
  evento,
  camara,
  seleccionado,
  onClick,
}: {
  evento: CameraEvent
  camara?: string
  seleccionado: boolean
  onClick: () => void
}) {
  const meta = eventMeta(evento.type)
  const Icon = meta.icon
  const enCurso = evento.state !== 'ended'
  const foto = evento.media[0]
  const objetivo = targetLabel(evento.target_type)

  return (
    <button
      onClick={onClick}
      className={cn(
        'flex w-full items-center gap-4 rounded-xl border bg-surface p-3 text-left transition',
        seleccionado ? 'border-accent/60 ring-1 ring-accent/40' : 'border-line hover:border-muted/40',
      )}
    >
      {foto ? (
        <img
          src={api.eventPictureUrl(evento.id, foto.id)}
          alt=""
          loading="lazy"
          className="h-14 w-24 shrink-0 rounded-lg object-cover"
        />
      ) : (
        <div className={cn('grid h-14 w-14 shrink-0 place-items-center rounded-lg border', meta.className)}>
          <Icon className="size-6" />
        </div>
      )}

      <div className="min-w-0 flex-1 space-y-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-medium">{meta.label}</span>
          {enCurso ? (
            <Badge tone="bad" className="py-0">
              <span className="size-1.5 animate-pulse rounded-full bg-bad" /> en curso
            </Badge>
          ) : null}
          {evento.rule_ref && (
            <span className="font-mono text-[11px] text-muted">regla {evento.rule_ref}</span>
          )}
        </div>
        <p className="truncate text-sm text-muted">{camara ?? 'Cámara'}</p>
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted">
          <span className="inline-flex items-center gap-1" title={new Date(evento.occurred_at).toLocaleString()}>
            <Clock className="size-3" /> {sinceLabel(evento.occurred_at)} ·{' '}
            {durationLabel(evento.occurred_at, evento.ended_at)}
          </span>
          {evento.hits > 1 && (
            <span className="inline-flex items-center gap-1" title="Avisos de la cámara agrupados en este episodio">
              <Layers className="size-3" /> ×{evento.hits}
            </span>
          )}
          {objetivo && (
            <span className="inline-flex items-center gap-1">
              <Target className="size-3" /> {objetivo}
            </span>
          )}
        </div>
      </div>

      <span className="hidden shrink-0 font-mono text-xs text-muted sm:block">
        {new Date(evento.occurred_at).toLocaleTimeString()}
      </span>
    </button>
  )
}
