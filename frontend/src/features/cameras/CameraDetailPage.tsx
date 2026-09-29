import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeft,
  Camera as CameraIcon,
  ImageOff,
  Loader2,
  Pencil,
  Play,
  PlugZap,
  RefreshCw,
  Trash2,
} from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'

import { api } from '@/api/client'
import type { Camera, ConnectionReport, StreamType } from '@/api/types'
import { PROTOCOLS, ProtocolLight, StatusBadge, levelMeta, protocolMeta } from '@/components/status'
import { Badge, Button, Card, EmptyState, cn } from '@/components/ui'
import { CameraFormDialog } from '@/features/cameras/CameraFormDialog'
import { useConnectivity } from '@/features/cameras/CamerasPage'
import { LivePlayer } from '@/features/live/LivePlayer'
import { RecordingPanel } from '@/features/live/RecordingPanel'
import { RulesTab } from '@/features/rules/RulesTab'

const tabs = ['Vivo', 'Reglas', 'Perfiles', 'Capacidades', 'Registro'] as const
type Tab = (typeof tabs)[number]

export function CameraDetailPage() {
  const { cameraId = '' } = useParams()
  const [tab, setTab] = useState<Tab>('Vivo')
  const [editing, setEditing] = useState(false)
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  const { data: camera, error } = useQuery({
    queryKey: ['camera', cameraId],
    queryFn: () => api.camera(cameraId),
  })
  const { data: levels } = useConnectivity(cameraId)

  const test = useMutation({
    mutationFn: () => api.testConnection(cameraId),
    onSettled: () => queryClient.invalidateQueries(),
  })
  const remove = useMutation({
    mutationFn: () => api.deleteCamera(cameraId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cameras'] })
      navigate('/')
    },
  })

  if (error) {
    return (
      <EmptyState icon={<CameraIcon className="size-8" />} title="Cámara no encontrada">
        <Link to="/" className="text-accent">
          Volver al listado
        </Link>
      </EmptyState>
    )
  }
  if (!camera) return <div className="h-64 animate-pulse rounded-xl bg-surface" />

  return (
    <div className="space-y-6">
      <Link to="/" className="inline-flex items-center gap-1.5 text-sm text-muted hover:text-fg">
        <ArrowLeft className="size-4" /> Cámaras
      </Link>

      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-2xl font-semibold tracking-tight">{camera.name}</h1>
            <StatusBadge status={camera.status} />
            {camera.network_mode === 'vpn' && <Badge tone="accent">VPN</Badge>}
          </div>
          <p className="font-mono text-xs text-muted">
            {[camera.vendor, camera.model, camera.firmware, camera.host].filter(Boolean).join(' · ')}
          </p>
          <div className="flex flex-wrap gap-1.5">
            {PROTOCOLS.map((p) => (
              <ProtocolLight key={p} protocol={p} level={levels?.[p]} />
            ))}
          </div>
        </div>
        <div className="flex gap-2">
          <Button
            variant="primary"
            icon={<PlugZap className="size-4" />}
            loading={test.isPending}
            onClick={() => test.mutate()}
          >
            Probar conexión
          </Button>
          <Button
            icon={<Pencil className="size-4" />}
            onClick={() => {
              test.reset() // el resultado anterior puede no valer para los datos nuevos
              setEditing(true)
            }}
          >
            <span className="sr-only sm:not-sr-only">Editar</span>
          </Button>
          <Button
            variant="danger"
            icon={<Trash2 className="size-4" />}
            loading={remove.isPending}
            onClick={() => confirm(`¿Eliminar "${camera.name}"?`) && remove.mutate()}
          >
            <span className="sr-only sm:not-sr-only">Eliminar</span>
          </Button>
        </div>
      </header>

      {test.data && <ConnectionResult report={test.data} />}

      <CameraFormDialog open={editing} onClose={() => setEditing(false)} camera={camera} />

      <div className="flex gap-1 border-b border-line">
        {tabs.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={cn(
              '-mb-px border-b-2 px-4 py-2.5 text-sm transition',
              tab === t ? 'border-accent text-fg' : 'border-transparent text-muted hover:text-fg',
            )}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === 'Vivo' && <LiveTab camera={camera} />}
      {tab === 'Reglas' && <RulesTab camera={camera} />}
      {tab === 'Perfiles' && <ProfilesTab cameraId={camera.id} />}
      {tab === 'Capacidades' && <CapabilitiesTab cameraId={camera.id} />}
      {tab === 'Registro' && <OperationsTab cameraId={camera.id} />}
    </div>
  )
}

function ConnectionResult({ report }: { report: ConnectionReport }) {
  return (
    <div className="grid gap-3 sm:grid-cols-3">
      {PROTOCOLS.map((p) => {
        const check = report[p]
        return (
          <Card key={p} className={cn('p-4', check.ok ? 'border-ok/30' : 'border-bad/30')}>
            <div className="flex items-center justify-between">
              <span className={cn('font-mono text-sm font-semibold', protocolMeta[p].text)}>
                {protocolMeta[p].label}
              </span>
              <span className="font-mono text-xs text-muted">{Math.round(check.latency_ms)} ms</span>
            </div>
            <p className={cn('mt-1 text-sm', check.ok ? 'text-ok' : 'text-bad')}>
              {check.ok ? 'Respondió correctamente' : check.message}
            </p>
          </Card>
        )
      })}
    </div>
  )
}

function LiveTab({ camera }: { camera: Camera }) {
  const [stream, setStream] = useState<StreamType>('sub')
  const [snapshotKey, setSnapshotKey] = useState(0)
  const live = useMutation({ mutationFn: (s: StreamType) => api.startLive(camera.id, s) })

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
      <div className="space-y-3">
        {live.data ? (
          <LivePlayer urls={live.data} onRetry={() => live.mutate(stream)} />
        ) : (
          <div className="grid aspect-video place-items-center rounded-xl border border-line bg-black">
            <div className="flex flex-col items-center gap-3">
              <Button
                variant="primary"
                icon={<Play className="size-4" />}
                loading={live.isPending}
                onClick={() => live.mutate(stream)}
              >
                Ver en vivo
              </Button>
              {live.error && <p className="text-sm text-bad">{live.error.message}</p>}
            </div>
          </div>
        )}
        <div className="flex items-center gap-2 text-sm">
          <span className="text-muted">Stream:</span>
          {(['sub', 'main'] as StreamType[]).map((s) => (
            <Button
              key={s}
              variant={stream === s ? 'secondary' : 'ghost'}
              className="h-8"
              onClick={() => {
                setStream(s)
                if (live.data) live.mutate(s)
              }}
            >
              {s === 'main' ? 'Principal (máx. calidad)' : 'Secundario (liviano)'}
            </Button>
          ))}
        </div>
        <p className="text-xs text-muted">
          Cámara → RTSP → MediaMTX → WebRTC en el navegador. Las credenciales nunca salen del
          backend.
        </p>
        <RecordingPanel cameraId={camera.id} stream={stream} />
      </div>

      <Card className="h-fit overflow-hidden">
        <div className="flex items-center justify-between border-b border-line px-4 py-3">
          <div>
            <p className="text-sm font-medium">Snapshot</p>
            <p className="font-mono text-[11px] text-isapi">ISAPI /Streaming/channels/101/picture</p>
          </div>
          <Button
            variant="ghost"
            className="size-8 px-0"
            aria-label="Nueva captura"
            onClick={() => setSnapshotKey((k) => k + 1)}
          >
            <RefreshCw className="size-4" />
          </Button>
        </div>
        <Snapshot key={snapshotKey} cameraId={camera.id} />
      </Card>
    </div>
  )
}

function Snapshot({ cameraId }: { cameraId: string }) {
  const [state, setState] = useState<'loading' | 'ok' | 'failed'>('loading')
  const [src] = useState(() => api.snapshotUrl(cameraId))
  return (
    <div className="relative grid aspect-video place-items-center bg-bg">
      {state !== 'failed' && (
        <img
          src={src}
          alt="Snapshot"
          onLoad={() => setState('ok')}
          onError={() => setState('failed')}
          className={cn('absolute inset-0 size-full object-cover', state !== 'ok' && 'opacity-0')}
        />
      )}
      {state === 'loading' && <Loader2 className="size-5 animate-spin text-muted" />}
      {state === 'failed' && (
        <p className="flex items-center gap-2 text-xs text-muted">
          <ImageOff className="size-4" /> Sin imagen: la cámara no respondió
        </p>
      )}
    </div>
  )
}

function ProfilesTab({ cameraId }: { cameraId: string }) {
  const queryClient = useQueryClient()
  const { data: profiles } = useQuery({
    queryKey: ['profiles', cameraId],
    queryFn: () => api.profiles(cameraId),
  })
  const refresh = useMutation({
    mutationFn: () => api.refreshProfiles(cameraId),
    onSuccess: (data) => {
      queryClient.setQueryData(['profiles', cameraId], data)
      queryClient.invalidateQueries({ queryKey: ['capabilities', cameraId] })
    },
  })

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <p className="text-sm text-muted">
          Los mismos streams vistos por ISAPI y por ONVIF: sirve para comparar qué detalle expone
          cada protocolo.
        </p>
        <Button
          icon={<RefreshCw className="size-4" />}
          loading={refresh.isPending}
          onClick={() => refresh.mutate()}
        >
          Leer perfiles
        </Button>
      </div>
      {profiles?.length ? (
        <DataTable
          head={['Protocolo', 'Token', 'Tipo', 'Códec', 'Resolución', 'FPS', 'Bitrate', 'Ruta RTSP']}
          rows={profiles.map((p) => [
            <span className={cn('font-mono font-semibold', protocolMeta[p.protocol].text)}>
              {protocolMeta[p.protocol].label}
            </span>,
            p.token,
            p.stream_type,
            p.codec ?? '—',
            p.width ? `${p.width}×${p.height}` : '—',
            p.fps ?? '—',
            p.bitrate_kbps ? `${p.bitrate_kbps} kbps` : '—',
            <span className="font-mono text-xs">{p.rtsp_path}</span>,
          ])}
        />
      ) : (
        <EmptyState icon={<RefreshCw className="size-7" />} title="Sin perfiles leídos">
          Tocá “Leer perfiles” para consultarlos por ISAPI y ONVIF.
        </EmptyState>
      )}
    </div>
  )
}

function CapabilitiesTab({ cameraId }: { cameraId: string }) {
  const { data: checks } = useQuery({
    queryKey: ['capabilities', cameraId],
    queryFn: () => api.capabilities(cameraId),
  })
  if (!checks?.length) {
    return (
      <EmptyState icon={<PlugZap className="size-7" />} title="Sin capacidades registradas">
        Probá la conexión para empezar a construir la matriz de esta cámara.
      </EmptyState>
    )
  }
  return (
    <DataTable
      head={['Función', 'Protocolo', 'Nivel', 'Origen', 'Latencia', 'Verificada']}
      rows={checks.map((c) => [
        <span className="font-mono text-xs">{c.capability_code}</span>,
        <span className={cn('font-mono font-semibold', protocolMeta[c.protocol].text)}>
          {protocolMeta[c.protocol].label}
        </span>,
        <span
          className={cn('rounded-md border px-2 py-0.5 text-xs', levelMeta[c.level].className)}
          title={String(c.evidence?.message ?? '')}
        >
          {levelMeta[c.level].label}
        </span>,
        c.source === 'verified' ? 'Verificada' : 'Declarada',
        c.latency_ms != null ? `${Math.round(c.latency_ms)} ms` : '—',
        new Date(c.checked_at).toLocaleString(),
      ])}
    />
  )
}

function OperationsTab({ cameraId }: { cameraId: string }) {
  const { data: operations } = useQuery({
    queryKey: ['operations', cameraId],
    queryFn: () => api.operations(cameraId),
    refetchInterval: 5000,
  })
  return (
    <DataTable
      head={['Hora', 'Protocolo', 'Operación', 'Resultado', 'Latencia']}
      rows={(operations ?? []).map((o) => [
        <span className="font-mono text-xs">{new Date(o.created_at).toLocaleTimeString()}</span>,
        <span className={cn('font-mono font-semibold', protocolMeta[o.protocol].text)}>
          {protocolMeta[o.protocol].label}
        </span>,
        <span className="font-mono text-xs">{o.operation}</span>,
        o.success ? (
          <Badge tone="ok">OK</Badge>
        ) : (
          <span className="text-xs text-bad" title={String(o.detail?.message ?? '')}>
            {o.error_code}
            {o.http_status ? ` (${o.http_status})` : ''}
          </span>
        ),
        o.latency_ms != null ? `${Math.round(o.latency_ms)} ms` : '—',
      ])}
    />
  )
}

function DataTable({ head, rows }: { head: string[]; rows: React.ReactNode[][] }) {
  return (
    <Card className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-line text-left text-xs text-muted">
            {head.map((h) => (
              <th key={h} className="px-4 py-3 font-medium whitespace-nowrap">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((cells, i) => (
            <tr key={i} className="border-b border-line/60 last:border-0 hover:bg-surface-2/40">
              {cells.map((cell, j) => (
                <td key={j} className="px-4 py-2.5 whitespace-nowrap">
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  )
}
