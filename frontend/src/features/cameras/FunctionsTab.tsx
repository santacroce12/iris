import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, Power, RefreshCw, Save } from 'lucide-react'
import { useState } from 'react'

import { api } from '@/api/client'
import type { ImageSettings, MotionDetection, Osd } from '@/api/types'
import { protocolMeta } from '@/components/status'
import { Button, Card, Field, cn } from '@/components/ui'

/** Las funciones comunes solo se resuelven por ISAPI u ONVIF: RTSP no aplica acá (es video, no
 * datos), así que esta pantalla usa un tipo más chico que el `Protocol` general de la plataforma. */
type ProtocoloFunciones = 'isapi' | 'onvif'

/** Funciones comunes, leídas y escritas por ISAPI y por ONVIF, lado a lado.
 *
 * Es la pantalla que muestra en carne propia la asimetría que documenta la tesis: la escritura
 * de OSD, imagen y movimiento hoy solo existe por ISAPI (el driver ONVIF de este trabajo no
 * implementa esos `Set*`, ver `backend/app/drivers/onvif/system.py`), así que el panel ONVIF
 * queda en modo lectura para esas tres funciones y lo dice explícitamente en vez de ocultarlo. */
export function FunctionsTab({ cameraId }: { cameraId: string }) {
  const isapi = useFunctions(cameraId, 'isapi')
  const onvif = useFunctions(cameraId, 'onvif')

  return (
    <div className="space-y-4">
      <p className="max-w-3xl text-sm text-muted">
        Las mismas funciones, leídas por los dos protocolos de esta cámara. La edición de OSD,
        imagen y detección de movimiento solo está implementada por ISAPI — el panel ONVIF muestra
        lo que esa cámara declara, pero esta plataforma no lo modifica por ahí (ver capítulo 7,
        §7.4 de la tesis).
      </p>
      <div className="grid gap-4 lg:grid-cols-2">
        <ProtocoloPanel cameraId={cameraId} protocol="isapi" query={isapi} editable />
        <ProtocoloPanel cameraId={cameraId} protocol="onvif" query={onvif} editable={false} />
      </div>
    </div>
  )
}

function useFunctions(cameraId: string, protocol: ProtocoloFunciones) {
  return useQuery({
    queryKey: ['functions', cameraId, protocol],
    queryFn: () => api.functions(cameraId, protocol),
    retry: false,
  })
}

function ProtocoloPanel({
  cameraId,
  protocol,
  query,
  editable,
}: {
  cameraId: string
  protocol: ProtocoloFunciones
  query: ReturnType<typeof useFunctions>
  editable: boolean
}) {
  const queryClient = useQueryClient()
  const invalidar = () => {
    queryClient.invalidateQueries({ queryKey: ['functions', cameraId, 'isapi'] })
    queryClient.invalidateQueries({ queryKey: ['functions', cameraId, 'onvif'] })
  }

  const sync = useMutation({
    mutationFn: () => api.syncTime(cameraId, protocol),
    onSuccess: invalidar,
  })
  const reboot = useMutation({
    mutationFn: () => api.reboot(cameraId, protocol),
  })

  return (
    <Card className="space-y-4 p-4">
      <div className="flex items-center justify-between">
        <span className={cn('font-mono text-sm font-semibold', protocolMeta[protocol].text)}>
          {protocolMeta[protocol].label}
        </span>
        <Button
          variant="ghost"
          className="size-8 px-0"
          aria-label="Releer"
          loading={query.isFetching}
          onClick={() => query.refetch()}
        >
          <RefreshCw className="size-3.5" />
        </Button>
      </div>

      {query.isLoading && <div className="h-40 animate-pulse rounded-lg bg-surface-2/60" />}

      {query.error && (
        <p className="flex items-center gap-2 rounded-lg border border-bad/25 bg-bad/5 px-3 py-2 text-xs text-bad">
          <AlertTriangle className="size-3.5 shrink-0" /> {query.error.message}
        </p>
      )}

      {query.data && (
        <div className="space-y-4">
          {query.data.status && (
            <Seccion titulo="Estado">
              <Dato etiqueta="Encendida hace">{formatUptime(query.data.status.uptime_s)}</Dato>
              <Dato etiqueta="CPU">{formatPercent(query.data.status.cpu_percent)}</Dato>
              <Dato etiqueta="Memoria">{formatPercent(query.data.status.memory_percent)}</Dato>
            </Seccion>
          )}
          {query.data.errors.status && <Error mensaje={query.data.errors.status} campo="Estado" />}

          <Seccion
            titulo="Hora"
            accion={
              <Button
                className="h-7 px-2 text-xs"
                loading={sync.isPending}
                onClick={() => sync.mutate()}
              >
                Sincronizar
              </Button>
            }
          >
            {query.data.time ? (
              <>
                <Dato etiqueta="Hora local">{query.data.time.local_time ?? '—'}</Dato>
                <Dato etiqueta="Huso">{query.data.time.timezone ?? '—'}</Dato>
                <Dato etiqueta="Modo">{query.data.time.mode ?? '—'}</Dato>
              </>
            ) : (
              query.data.errors.time && <Error mensaje={query.data.errors.time} campo="Hora" />
            )}
            {sync.error && <Error mensaje={sync.error.message} campo="Sincronización" />}
            {sync.isSuccess && <p className="text-xs text-ok">Sincronizada.</p>}
          </Seccion>

          <OsdSeccion
            osd={query.data.osd}
            error={query.data.errors.osd}
            editable={editable}
            cameraId={cameraId}
            onSaved={invalidar}
          />

          <ImagenSeccion
            imagen={query.data.image}
            error={query.data.errors.image}
            editable={editable}
            cameraId={cameraId}
            onSaved={invalidar}
          />

          <MovimientoSeccion
            motion={query.data.motion}
            error={query.data.errors.motion}
            editable={editable}
            cameraId={cameraId}
            onSaved={invalidar}
          />

          <div className="border-t border-line pt-3">
            <Button
              variant="danger"
              icon={<Power className="size-3.5" />}
              loading={reboot.isPending}
              onClick={() => {
                if (confirm(`¿Reiniciar la cámara por ${protocolMeta[protocol].label}?`)) {
                  reboot.mutate()
                }
              }}
            >
              Reiniciar por {protocolMeta[protocol].label}
            </Button>
            {reboot.error && <Error mensaje={reboot.error.message} campo="Reinicio" />}
            {reboot.isSuccess && <p className="mt-2 text-xs text-ok">Reinicio enviado.</p>}
          </div>
        </div>
      )}
    </Card>
  )
}

function Seccion({
  titulo,
  accion,
  children,
}: {
  titulo: string
  accion?: React.ReactNode
  children: React.ReactNode
}) {
  return (
    <div className="space-y-1.5 border-t border-line/60 pt-3 first:border-0 first:pt-0">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-medium tracking-wide text-muted uppercase">{titulo}</h3>
        {accion}
      </div>
      <div className="space-y-1">{children}</div>
    </div>
  )
}

function Dato({ etiqueta, children }: { etiqueta: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-muted">{etiqueta}</span>
      <span className="font-mono text-xs">{children}</span>
    </div>
  )
}

function Error({ mensaje, campo }: { mensaje: string; campo: string }) {
  return (
    <p className="flex items-start gap-1.5 text-xs text-bad">
      <AlertTriangle className="mt-0.5 size-3 shrink-0" />
      <span>
        <span className="font-medium">{campo}:</span> {mensaje}
      </span>
    </p>
  )
}

function formatUptime(segundos: number | null): string {
  if (segundos == null) return '—'
  const dias = Math.floor(segundos / 86400)
  const horas = Math.floor((segundos % 86400) / 3600)
  return dias > 0 ? `${dias} d ${horas} h` : `${horas} h`
}

function formatPercent(valor: number | null): string {
  return valor == null ? '—' : `${valor} %`
}

function OsdSeccion({
  osd,
  error,
  editable,
  cameraId,
  onSaved,
}: {
  osd: Osd | null
  error?: string
  editable: boolean
  cameraId: string
  onSaved: () => void
}) {
  const guardar = useMutation({
    mutationFn: (valores: Osd) =>
      api.setOsd(cameraId, {
        show_name: valores.show_name ?? undefined,
        show_date: valores.show_date ?? undefined,
        name: valores.name ?? undefined,
      }),
    onSuccess: onSaved,
  })

  return (
    <Seccion titulo="Texto sobre la imagen (OSD)">
      {!osd && error && <Error mensaje={error} campo="OSD" />}
      {osd && !editable && (
        <>
          <Dato etiqueta="Nombre">{osd.name || '—'}</Dato>
          <Dato etiqueta="Muestra nombre">{osd.show_name ? 'sí' : 'no'}</Dato>
          <Dato etiqueta="Muestra fecha">{osd.show_date ? 'sí' : 'no'}</Dato>
        </>
      )}
      {osd && editable && (
        // key: remonta el formulario con los valores nuevos cada vez que llega una lectura
        // distinta (incluida la que sigue a un guardado exitoso), sin sincronizar con un efecto.
        <OsdForm
          key={JSON.stringify(osd)}
          inicial={osd}
          guardando={guardar.isPending}
          onGuardar={(valores) => guardar.mutate(valores)}
        />
      )}
      {guardar.error && <Error mensaje={guardar.error.message} campo="Guardar OSD" />}
      {guardar.isSuccess && <p className="text-xs text-ok">Guardado y verificado.</p>}
    </Seccion>
  )
}

function OsdForm({
  inicial,
  guardando,
  onGuardar,
}: {
  inicial: Osd
  guardando: boolean
  onGuardar: (valores: Osd) => void
}) {
  const [valores, setValores] = useState(inicial)
  return (
    <div className="space-y-2 pt-1">
      <Field
        label="Nombre en pantalla"
        maxLength={32}
        value={valores.name ?? ''}
        onChange={(e) => setValores({ ...valores, name: e.target.value })}
      />
      <div className="flex flex-wrap items-center gap-4 pt-1 text-sm">
        <label className="flex items-center gap-1.5">
          <input
            type="checkbox"
            checked={valores.show_name ?? false}
            onChange={(e) => setValores({ ...valores, show_name: e.target.checked })}
          />
          Mostrar nombre
        </label>
        <label className="flex items-center gap-1.5">
          <input
            type="checkbox"
            checked={valores.show_date ?? false}
            onChange={(e) => setValores({ ...valores, show_date: e.target.checked })}
          />
          Mostrar fecha
        </label>
        <Button
          className="ml-auto h-7 px-2 text-xs"
          icon={<Save className="size-3" />}
          loading={guardando}
          onClick={() => onGuardar(valores)}
        >
          Guardar
        </Button>
      </div>
    </div>
  )
}

const CAMPOS_IMAGEN: { clave: keyof ImageSettings; etiqueta: string }[] = [
  { clave: 'brightness', etiqueta: 'Brillo' },
  { clave: 'contrast', etiqueta: 'Contraste' },
  { clave: 'saturation', etiqueta: 'Saturación' },
  { clave: 'sharpness', etiqueta: 'Nitidez' },
]

function ImagenSeccion({
  imagen,
  error,
  editable,
  cameraId,
  onSaved,
}: {
  imagen: ImageSettings | null
  error?: string
  editable: boolean
  cameraId: string
  onSaved: () => void
}) {
  const guardar = useMutation({
    mutationFn: (valores: ImageSettings) =>
      api.setImage(cameraId, {
        brightness: valores.brightness ?? undefined,
        contrast: valores.contrast ?? undefined,
        saturation: valores.saturation ?? undefined,
        sharpness: valores.sharpness ?? undefined,
      }),
    onSuccess: onSaved,
  })

  return (
    <Seccion titulo="Ajustes de imagen">
      {!imagen && error && <Error mensaje={error} campo="Imagen" />}
      {imagen && !editable && (
        <div className="grid grid-cols-2 gap-x-4">
          {CAMPOS_IMAGEN.map((c) => (
            <Dato key={c.clave} etiqueta={c.etiqueta}>
              {imagen[c.clave] ?? '—'}
            </Dato>
          ))}
        </div>
      )}
      {imagen && editable && (
        <ImagenForm
          key={JSON.stringify(imagen)}
          inicial={imagen}
          guardando={guardar.isPending}
          onGuardar={(valores) => guardar.mutate(valores)}
        />
      )}
      {guardar.error && <Error mensaje={guardar.error.message} campo="Guardar imagen" />}
      {guardar.isSuccess && <p className="text-xs text-ok">Guardado y verificado.</p>}
    </Seccion>
  )
}

function ImagenForm({
  inicial,
  guardando,
  onGuardar,
}: {
  inicial: ImageSettings
  guardando: boolean
  onGuardar: (valores: ImageSettings) => void
}) {
  const [valores, setValores] = useState(inicial)
  return (
    <div className="space-y-2 pt-1">
      <div className="grid grid-cols-2 gap-2">
        {CAMPOS_IMAGEN.map((c) => (
          <Field
            key={c.clave}
            label={c.etiqueta}
            type="number"
            min={0}
            max={100}
            value={valores[c.clave] ?? ''}
            onChange={(e) =>
              setValores({
                ...valores,
                [c.clave]: e.target.value === '' ? null : Number(e.target.value),
              })
            }
          />
        ))}
      </div>
      <Button
        className="h-7 px-2 text-xs"
        icon={<Save className="size-3" />}
        loading={guardando}
        onClick={() => onGuardar(valores)}
      >
        Guardar
      </Button>
    </div>
  )
}

function MovimientoSeccion({
  motion,
  error,
  editable,
  cameraId,
  onSaved,
}: {
  motion: MotionDetection | null
  error?: string
  editable: boolean
  cameraId: string
  onSaved: () => void
}) {
  const guardar = useMutation({
    mutationFn: (valores: MotionDetection) =>
      api.setMotion(cameraId, {
        enabled: valores.enabled ?? undefined,
        sensitivity: valores.sensitivity ?? undefined,
      }),
    onSuccess: onSaved,
  })

  return (
    <Seccion titulo="Detección de movimiento">
      {!motion && !error && (
        <p className="text-xs text-muted">
          Solo se puede *saber que existe* por ONVIF, no leer su estado (§3.3 del marco teórico).
        </p>
      )}
      {!motion && error && <Error mensaje={error} campo="Movimiento" />}
      {motion && !editable && (
        <>
          <Dato etiqueta="Activada">{motion.enabled ? 'sí' : 'no'}</Dato>
          <Dato etiqueta="Sensibilidad">{motion.sensitivity ?? '—'}</Dato>
        </>
      )}
      {motion && editable && (
        <MovimientoForm
          key={JSON.stringify(motion)}
          inicial={motion}
          guardando={guardar.isPending}
          onGuardar={(valores) => guardar.mutate(valores)}
        />
      )}
      {guardar.error && <Error mensaje={guardar.error.message} campo="Guardar movimiento" />}
      {guardar.isSuccess && <p className="text-xs text-ok">Guardado y verificado.</p>}
    </Seccion>
  )
}

function MovimientoForm({
  inicial,
  guardando,
  onGuardar,
}: {
  inicial: MotionDetection
  guardando: boolean
  onGuardar: (valores: MotionDetection) => void
}) {
  const [valores, setValores] = useState(inicial)
  return (
    <div className="flex items-center gap-4 pt-1 text-sm">
      <label className="flex items-center gap-1.5">
        <input
          type="checkbox"
          checked={valores.enabled ?? false}
          onChange={(e) => setValores({ ...valores, enabled: e.target.checked })}
        />
        Activada
      </label>
      <Field
        label="Sensibilidad"
        type="number"
        min={0}
        max={100}
        className="w-32"
        value={valores.sensitivity ?? ''}
        onChange={(e) =>
          setValores({
            ...valores,
            sensitivity: e.target.value === '' ? null : Number(e.target.value),
          })
        }
      />
      <Button
        className="mt-4 h-7 px-2 text-xs"
        icon={<Save className="size-3" />}
        loading={guardando}
        onClick={() => onGuardar(valores)}
      >
        Guardar
      </Button>
    </div>
  )
}
