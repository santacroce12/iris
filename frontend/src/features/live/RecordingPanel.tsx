import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Circle, Film, Square } from 'lucide-react'

import { api } from '@/api/client'
import type { StreamType } from '@/api/types'
import { Badge, Button, Card, cn } from '@/components/ui'

/** Grabación continua en MediaMTX: sirve como evidencia de las pruebas con la cámara real. */
export function RecordingPanel({ cameraId, stream }: { cameraId: string; stream: StreamType }) {
  const queryClient = useQueryClient()
  const clave = ['recording', cameraId, stream]
  const { data } = useQuery({
    queryKey: clave,
    queryFn: () => api.recording(cameraId, stream),
    refetchInterval: 15000,
    retry: false,
  })

  const cambiar = useMutation({
    mutationFn: (enabled: boolean) => api.setRecording(cameraId, enabled, stream),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: clave }),
  })

  const grabando = data?.recording ?? false
  const segmentos = data?.segments ?? []

  return (
    <Card className="space-y-3 p-3">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-sm">
          <Film className="size-4 text-muted" />
          <span>Grabación</span>
          {grabando && (
            <Badge tone="bad">
              <Circle className="size-2 animate-pulse fill-current" /> grabando
            </Badge>
          )}
        </div>
        <Button
          variant={grabando ? 'secondary' : 'primary'}
          className="h-8"
          loading={cambiar.isPending}
          icon={
            grabando ? <Square className="size-3.5" /> : <Circle className="size-3.5 fill-bad" />
          }
          onClick={() => cambiar.mutate(!grabando)}
        >
          {grabando ? 'Detener' : 'Grabar'}
        </Button>
      </div>

      <p className="text-[11px] text-muted">
        Mientras graba, la plataforma mantiene abierta la conexión con la cámara aunque nadie esté
        mirando. Queda en disco, en segmentos de 10 minutos.
      </p>

      {cambiar.error && <p className="text-xs text-bad">{cambiar.error.message}</p>}

      {segmentos.length > 0 && (
        <ul className="space-y-1 border-t border-line pt-2">
          {segmentos.slice(-5).map((segmento, indice) => (
            <li
              key={String(segmento.start ?? indice)}
              className={cn('flex items-center justify-between gap-2 font-mono text-[11px]')}
            >
              <span className="truncate text-muted">{formatearInicio(segmento.start)}</span>
            </li>
          ))}
          <li className="pt-1 text-[11px] text-muted">
            {segmentos.length} {segmentos.length === 1 ? 'segmento' : 'segmentos'} en total
          </li>
        </ul>
      )}
    </Card>
  )
}

function formatearInicio(valor: unknown): string {
  if (typeof valor !== 'string') return 'segmento'
  const fecha = new Date(valor)
  return Number.isNaN(fecha.getTime()) ? valor : fecha.toLocaleString('es-AR')
}
