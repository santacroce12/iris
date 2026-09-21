import { useQuery } from '@tanstack/react-query'
import { X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router'

import { api } from '@/api/client'
import type { LiveEvent } from '@/api/types'
import { cn } from '@/components/ui'
import { useEventStream } from '@/features/events/EventStream'
import { eventMeta } from '@/features/events/eventTypes'

const DURACION_MS = 7000
const MAX_VISIBLES = 3

/**
 * Aviso emergente en cualquier pantalla, solo para episodios de analítica que recién empiezan.
 * El movimiento no avisa: dispara todo el tiempo y taparía la interfaz.
 */
export function LiveToasts() {
  const { ultimo } = useEventStream()
  const [avisos, setAvisos] = useState<LiveEvent[]>([])
  const navigate = useNavigate()
  const { data: camaras = [] } = useQuery({ queryKey: ['cameras'], queryFn: api.cameras })

  useEffect(() => {
    if (!ultimo || !eventMeta(ultimo.type).analytic) return
    if (ultimo.hits > 1 || ultimo.state === 'ended') return // solo el comienzo del episodio
    setAvisos((prev) => [ultimo, ...prev.filter((a) => a.id !== ultimo.id)].slice(0, MAX_VISIBLES))
    const id = ultimo.id
    const timer = window.setTimeout(() => setAvisos((prev) => prev.filter((a) => a.id !== id)), DURACION_MS)
    return () => window.clearTimeout(timer)
  }, [ultimo])

  if (!avisos.length) return null
  return (
    <div className="pointer-events-none fixed right-4 bottom-4 z-50 flex w-[min(360px,calc(100vw-2rem))] flex-col gap-2">
      {avisos.map((a) => {
        const meta = eventMeta(a.type)
        const Icon = meta.icon
        const camara = camaras.find((c) => c.id === a.camera_id)?.name ?? 'Cámara'
        return (
          <div
            key={a.id}
            className="pointer-events-auto flex items-start gap-3 rounded-xl border border-line bg-surface p-3 shadow-2xl shadow-black/50"
          >
            <div className={cn('grid size-9 shrink-0 place-items-center rounded-lg border', meta.className)}>
              <Icon className="size-4" />
            </div>
            <button className="min-w-0 flex-1 text-left" onClick={() => navigate('/eventos')}>
              <p className="text-sm font-medium">{meta.label}</p>
              <p className="truncate text-xs text-muted">
                {camara}
                {a.rule_ref ? ` · regla ${a.rule_ref}` : ''}
              </p>
            </button>
            <button
              aria-label="Cerrar aviso"
              className="text-muted hover:text-fg"
              onClick={() => setAvisos((prev) => prev.filter((x) => x.id !== a.id))}
            >
              <X className="size-4" />
            </button>
          </div>
        )
      })}
    </div>
  )
}
