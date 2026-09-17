import { useQuery } from '@tanstack/react-query'
import { Cctv, Plus, VideoOff } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router'

import { api } from '@/api/client'
import type { Camera, Protocol, SupportLevel } from '@/api/types'
import { PROTOCOLS, ProtocolLight, StatusBadge } from '@/components/status'
import { Badge, Button, Card, EmptyState } from '@/components/ui'
import { AddCameraDialog } from '@/features/cameras/AddCameraDialog'

/** Nivel de conectividad por protocolo según la última prueba de conexión. */
export function useConnectivity(cameraId: string) {
  return useQuery({
    queryKey: ['capabilities', cameraId],
    queryFn: () => api.capabilities(cameraId),
    select: (checks) => {
      const code: Record<Protocol, string> = {
        isapi: 'device.info',
        onvif: 'device.info',
        rtsp: 'media.live',
      }
      return Object.fromEntries(
        PROTOCOLS.map((p) => [
          p,
          checks.find((c) => c.protocol === p && c.capability_code === code[p])?.level,
        ]),
      ) as Record<Protocol, SupportLevel | undefined>
    },
  })
}

function CameraCard({ camera }: { camera: Camera }) {
  const { data: levels } = useConnectivity(camera.id)
  const [snapshotFailed, setSnapshotFailed] = useState(false)
  const reachable = levels?.isapi === 'supported'

  return (
    <Link to={`/camaras/${camera.id}`} className="group">
      <Card className="overflow-hidden transition group-hover:border-accent/40">
        <div className="relative aspect-video bg-bg">
          {reachable && !snapshotFailed ? (
            <img
              src={api.snapshotUrl(camera.id)}
              alt={`Vista de ${camera.name}`}
              loading="lazy"
              onError={() => setSnapshotFailed(true)}
              className="size-full object-cover opacity-90 transition group-hover:opacity-100"
            />
          ) : (
            <div className="grid size-full place-items-center text-muted/40">
              <VideoOff className="size-8" />
            </div>
          )}
          <div className="absolute top-3 left-3">
            <StatusBadge status={camera.status} />
          </div>
          {camera.network_mode === 'vpn' && (
            <Badge tone="accent" className="absolute top-3 right-3">
              VPN
            </Badge>
          )}
        </div>
        <div className="space-y-3 p-4">
          <div>
            <p className="truncate font-medium">{camera.name}</p>
            <p className="truncate font-mono text-xs text-muted">
              {camera.model ?? 'Modelo sin detectar'} · {camera.host}
            </p>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {PROTOCOLS.map((p) => (
              <ProtocolLight key={p} protocol={p} level={levels?.[p]} />
            ))}
          </div>
        </div>
      </Card>
    </Link>
  )
}

export function CamerasPage() {
  const [adding, setAdding] = useState(false)
  const { data: cameras, isLoading, error } = useQuery({
    queryKey: ['cameras'],
    queryFn: api.cameras,
  })

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Cámaras</h1>
          <p className="text-sm text-muted">
            Cada cámara se prueba por las tres APIs: ISAPI, ONVIF y RTSP.
          </p>
        </div>
        <Button variant="primary" icon={<Plus className="size-4" />} onClick={() => setAdding(true)}>
          Agregar cámara
        </Button>
      </header>

      {error && (
        <p className="rounded-lg border border-bad/30 bg-bad/10 px-4 py-3 text-sm text-bad">
          No se pudo contactar al backend: {error.message}
        </p>
      )}

      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className="aspect-[4/3] animate-pulse rounded-xl bg-surface" />
          ))}
        </div>
      ) : cameras?.length ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {cameras.map((camera) => (
            <CameraCard key={camera.id} camera={camera} />
          ))}
        </div>
      ) : (
        !error && (
          <EmptyState icon={<Cctv className="size-8" />} title="Todavía no hay cámaras">
            Agregá una Hikvision con su IP y credenciales. La plataforma detecta el modelo y prueba
            cada protocolo automáticamente.
          </EmptyState>
        )
      )}

      <AddCameraDialog open={adding} onClose={() => setAdding(false)} />
    </div>
  )
}
