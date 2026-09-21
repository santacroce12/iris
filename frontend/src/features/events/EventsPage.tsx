import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Activity, BellRing, Filter, Radio, RadioTower } from 'lucide-react'
import { useMemo, useState } from 'react'

import { api } from '@/api/client'
import type { Camera, CameraEvent, EventFilters, ListenerState, LiveEvent } from '@/api/types'
import { Badge, Button, Card, EmptyState, cn } from '@/components/ui'
import { EventCard } from '@/features/events/EventCard'
import { EventDetail } from '@/features/events/EventDetail'
import { useEventStream } from '@/features/events/EventStream'
import { EVENT_TYPES, eventMeta } from '@/features/events/eventTypes'
import { Timeline } from '@/features/events/Timeline'

const RANGOS = [
  { id: '1h', label: 'Última hora', ms: 3_600_000 },
  { id: '24h', label: '24 horas', ms: 86_400_000 },
  { id: '7d', label: '7 días', ms: 7 * 86_400_000 },
] as const
type Rango = (typeof RANGOS)[number]['id']

/** Lo que llega por SSE trae menos campos que el historial: se completa lo mínimo. */
function desdeVivo(e: LiveEvent): CameraEvent {
  return { ...e, protocol: 'isapi', received_at: e.occurred_at, payload: null, media: [] }
}

export function EventsPage() {
  const [camara, setCamara] = useState('')
  const [tipo, setTipo] = useState('')
  const [rango, setRango] = useState<Rango>('24h')
  const [soloAnalitica, setSoloAnalitica] = useState(false)
  const [seleccionado, setSeleccionado] = useState<string | null>(null)
  const { estado, recientes } = useEventStream()

  const since = useMemo(() => {
    const ms = RANGOS.find((r) => r.id === rango)!.ms
    return new Date(Date.now() - ms).toISOString()
    // Se recalcula al cambiar el rango; el feed en vivo cubre lo que pase después.
  }, [rango])

  const filtros: EventFilters = { camera_id: camara || undefined, type: tipo || undefined, since, limit: 300 }
  const { data: historial = [], isLoading } = useQuery({
    queryKey: ['events', filtros],
    queryFn: () => api.events(filtros),
  })
  const { data: camaras = [] } = useQuery({ queryKey: ['cameras'], queryFn: api.cameras })
  const nombres = useMemo(() => Object.fromEntries(camaras.map((c) => [c.id, c.name])), [camaras])

  // Historial + lo que llegó en vivo, sin duplicar: la versión en vivo manda en hits y estado.
  const eventos = useMemo(() => {
    const porId = new Map(historial.map((e) => [e.id, e]))
    for (const vivo of recientes) {
      if (camara && vivo.camera_id !== camara) continue
      if (tipo && vivo.type !== tipo) continue
      if (vivo.occurred_at < since) continue
      const previo = porId.get(vivo.id)
      porId.set(vivo.id, previo ? { ...previo, ...vivo, media: previo.media } : desdeVivo(vivo))
    }
    let lista = [...porId.values()].sort((a, b) => b.occurred_at.localeCompare(a.occurred_at))
    if (soloAnalitica) lista = lista.filter((e) => eventMeta(e.type).analytic)
    return lista
  }, [historial, recientes, camara, tipo, since, soloAnalitica])

  const conteo = useMemo(() => {
    const porTipo = new Map<string, { episodios: number; avisos: number }>()
    for (const e of eventos) {
      const c = porTipo.get(e.type) ?? { episodios: 0, avisos: 0 }
      porTipo.set(e.type, { episodios: c.episodios + 1, avisos: c.avisos + e.hits })
    }
    return [...porTipo.entries()].sort((a, b) => b[1].episodios - a[1].episodios)
  }, [eventos])
  const totalAvisos = eventos.reduce((s, e) => s + e.hits, 0)
  const detalle = eventos.find((e) => e.id === seleccionado) ?? null

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-semibold tracking-tight">Eventos</h1>
            <LiveIndicator estado={estado} />
          </div>
          <p className="text-sm text-muted">
            Cada fila es un episodio: los avisos repetidos de la cámara se agrupan en uno.
          </p>
        </div>
      </header>

      <ListenersBar camaras={camaras} />

      <div className="grid gap-3 sm:grid-cols-3">
        <Stat label="Episodios" valor={eventos.length} />
        <Stat label="Avisos recibidos" valor={totalAvisos} />
        <Stat
          label="Compresión"
          valor={eventos.length ? `${(totalAvisos / eventos.length).toFixed(1)}×` : '—'}
          hint="avisos por episodio guardado"
        />
      </div>

      {conteo.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {conteo.map(([t, c]) => {
            const meta = eventMeta(t)
            const Icon = meta.icon
            const activo = tipo === t
            return (
              <button
                key={t}
                onClick={() => setTipo(activo ? '' : t)}
                className={cn(
                  'inline-flex items-center gap-2 rounded-lg border px-3 py-1.5 text-sm transition',
                  meta.className,
                  activo ? 'ring-2 ring-accent' : 'opacity-90 hover:opacity-100',
                )}
              >
                <Icon className="size-4" />
                {meta.label}
                <span className="font-mono text-xs opacity-80">{c.episodios}</span>
              </button>
            )
          })}
        </div>
      )}

      <Card className="p-4">
        <Timeline eventos={eventos} desde={since} />
      </Card>

      <div className="flex flex-wrap items-center gap-3">
        <Filter className="size-4 text-muted" />
        <select
          value={camara}
          onChange={(e) => setCamara(e.target.value)}
          className="h-9 rounded-lg border border-line bg-surface px-3 text-sm"
        >
          <option value="">Todas las cámaras</option>
          {camaras.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
        <select
          value={tipo}
          onChange={(e) => setTipo(e.target.value)}
          className="h-9 rounded-lg border border-line bg-surface px-3 text-sm"
        >
          <option value="">Todos los tipos</option>
          {Object.entries(EVENT_TYPES).map(([id, meta]) => (
            <option key={id} value={id}>
              {meta.label}
            </option>
          ))}
        </select>
        <div className="flex rounded-lg border border-line p-0.5">
          {RANGOS.map((r) => (
            <button
              key={r.id}
              onClick={() => setRango(r.id)}
              className={cn(
                'rounded-md px-3 py-1.5 text-sm transition',
                rango === r.id ? 'bg-surface-2 text-fg' : 'text-muted hover:text-fg',
              )}
            >
              {r.label}
            </button>
          ))}
        </div>
        <label className="flex items-center gap-2 text-sm text-muted">
          <input
            type="checkbox"
            checked={soloAnalitica}
            onChange={(e) => setSoloAnalitica(e.target.checked)}
            className="accent-accent"
          />
          Solo analítica (ocultar movimiento y técnicos)
        </label>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_380px]">
        <div className="space-y-2">
          {isLoading ? (
            [0, 1, 2, 3].map((i) => <div key={i} className="h-20 animate-pulse rounded-xl bg-surface" />)
          ) : eventos.length ? (
            eventos.map((e) => (
              <EventCard
                key={e.id}
                evento={e}
                camara={nombres[e.camera_id]}
                seleccionado={e.id === seleccionado}
                onClick={() => setSeleccionado(e.id)}
              />
            ))
          ) : (
            <EmptyState icon={<BellRing className="size-8" />} title="Sin eventos en este rango">
              Activá el oyente de una cámara (arriba) y los eventos van a aparecer acá en el momento.
            </EmptyState>
          )}
        </div>
        <EventDetail evento={detalle} camara={detalle ? nombres[detalle.camera_id] : undefined} />
      </div>
    </div>
  )
}

function LiveIndicator({ estado }: { estado: 'conectando' | 'en_vivo' | 'desconectado' }) {
  if (estado === 'en_vivo')
    return (
      <Badge tone="ok">
        <span className="size-1.5 animate-pulse rounded-full bg-ok" /> En vivo
      </Badge>
    )
  return <Badge tone={estado === 'desconectado' ? 'bad' : 'warn'}>{estado === 'desconectado' ? 'Sin conexión' : 'Conectando…'}</Badge>
}

function Stat({ label, valor, hint }: { label: string; valor: number | string; hint?: string }) {
  return (
    <Card className="px-4 py-3">
      <p className="text-xs text-muted">{label}</p>
      <p className="font-mono text-2xl font-semibold">{valor}</p>
      {hint && <p className="text-[11px] text-muted/80">{hint}</p>}
    </Card>
  )
}

function ListenersBar({ camaras }: { camaras: Camera[] }) {
  const queryClient = useQueryClient()
  const { data: oyentes = [] } = useQuery({
    queryKey: ['listeners'],
    queryFn: api.listeners,
    refetchInterval: 5000,
  })
  const porCamara = new Map<string, ListenerState>(oyentes.map((o) => [o.camera_id, o]))
  const alternar = useMutation({
    mutationFn: async ({ id, encender }: { id: string; encender: boolean }) => {
      if (encender) await api.startListener(id)
      else await api.stopListener(id)
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['listeners'] })
      queryClient.invalidateQueries({ queryKey: ['cameras'] })
    },
  })

  if (!camaras.length) return null
  return (
    <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
      {camaras.map((c) => {
        const oyente = porCamara.get(c.id)
        const escuchando = c.listen_events
        const conectado = oyente?.status === 'conectado'
        return (
          <Card key={c.id} className="flex items-center gap-3 px-4 py-3">
            <div
              className={cn(
                'grid size-9 shrink-0 place-items-center rounded-lg',
                conectado ? 'bg-ok/10 text-ok' : escuchando ? 'bg-warn/10 text-warn' : 'bg-surface-2 text-muted',
              )}
            >
              {conectado ? <RadioTower className="size-4" /> : <Radio className="size-4" />}
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">{c.name}</p>
              <p className="truncate text-xs text-muted" title={oyente?.last_error ?? undefined}>
                {!escuchando
                  ? 'Sin escuchar eventos'
                  : conectado
                    ? `${oyente.alerts_received} avisos → ${oyente.episodes_saved} episodios`
                    : (oyente?.last_error ?? 'Conectando…')}
              </p>
            </div>
            <Button
              variant={escuchando ? 'ghost' : 'secondary'}
              className="h-8 shrink-0"
              icon={<Activity className="size-3.5" />}
              loading={alternar.isPending && alternar.variables?.id === c.id}
              onClick={() => alternar.mutate({ id: c.id, encender: !escuchando })}
            >
              {escuchando ? 'Pausar' : 'Escuchar'}
            </Button>
          </Card>
        )
      })}
    </div>
  )
}
