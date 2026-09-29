import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Download, Grid3x3, RefreshCw } from 'lucide-react'
import { Fragment, useState } from 'react'

import { api } from '@/api/client'
import type { Matrix, MatrixCell, Protocol, SupportLevel } from '@/api/types'
import { protocolMeta } from '@/components/status'
import { Badge, Button, Card, EmptyState, cn } from '@/components/ui'

/** Lo que se muestra en cada celda. El borde punteado marca que no se verificó. */
const CELDA: Record<SupportLevel, { texto: string; clase: string; titulo: string }> = {
  supported: { texto: '✓', clase: 'bg-ok/15 text-ok border-ok/30', titulo: 'Respondió' },
  partial: { texto: '~', clase: 'bg-warn/15 text-warn border-warn/30', titulo: 'Parcial' },
  unsupported: {
    texto: '✕',
    clase: 'bg-bad/10 text-bad/80 border-bad/25',
    titulo: 'La cámara contestó que no la soporta',
  },
  unverified: {
    texto: '·',
    clase: 'border-dashed border-line text-muted/60',
    titulo: 'No se pudo comprobar',
  },
  error: { texto: '!', clase: 'bg-bad/15 text-bad border-bad/30', titulo: 'Error al llamarla' },
}

export function MatrixPage() {
  const queryClient = useQueryClient()
  const { data, isLoading } = useQuery({ queryKey: ['matrix'], queryFn: api.matrix })
  const [detalle, setDetalle] = useState<{ fila: string; celda: MatrixCell } | null>(null)

  const detectar = useMutation({
    mutationFn: (cameraId: string) => api.detect(cameraId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['matrix'] }),
  })

  if (isLoading) return <div className="h-96 animate-pulse rounded-xl bg-surface" />
  if (!data || data.cameras.length === 0) {
    return (
      <EmptyState icon={<Grid3x3 className="size-8" />} title="Todavía no hay cámaras">
        Agregá una cámara y corré la detección para llenar la matriz.
      </EmptyState>
    )
  }

  const grupos = [...new Set(data.rows.map((f) => f.group))]

  return (
    <div className="space-y-5">
      <header className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight">Matriz de compatibilidad</h1>
        <p className="max-w-3xl text-sm text-muted">
          Cada función, intentada por cada protocolo. El punto clave no es solo qué anda, sino{' '}
          <strong className="text-fg">cómo se sabe</strong>: una celda llena significa que se llamó
          a la función y respondió; una punteada, que no se pudo comprobar.
        </p>
      </header>

      <div className="flex flex-wrap items-center gap-2">
        {data.cameras.map((camara) => (
          <Button
            key={camara.id}
            icon={<RefreshCw className="size-3.5" />}
            loading={detectar.isPending && detectar.variables === camara.id}
            onClick={() => detectar.mutate(camara.id)}
          >
            Detectar en {camara.name}
          </Button>
        ))}
        <Button icon={<Download className="size-3.5" />} onClick={() => descargarCsv(data)}>
          Exportar CSV
        </Button>
      </div>

      <Card className="overflow-x-auto">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-b border-line">
              <th className="sticky left-0 bg-surface px-3 py-2 text-left font-medium text-muted">
                Función
              </th>
              {data.cameras.map((camara) => (
                <th
                  key={camara.id}
                  colSpan={3}
                  className="border-l border-line px-3 py-2 text-center"
                >
                  <div className="truncate font-medium">{camara.name}</div>
                  <div className="font-mono text-[11px] text-muted">
                    {camara.model ?? camara.host}
                  </div>
                </th>
              ))}
            </tr>
            <tr className="border-b border-line text-[11px]">
              <th className="sticky left-0 bg-surface" />
              {data.cameras.flatMap((camara) =>
                (['isapi', 'onvif', 'rtsp'] as Protocol[]).map((p) => (
                  <th
                    key={`${camara.id}-${p}`}
                    className={cn(
                      'px-2 py-1 font-mono font-normal',
                      protocolMeta[p].text,
                      p === 'isapi' && 'border-l border-line',
                    )}
                  >
                    {protocolMeta[p].label}
                  </th>
                )),
              )}
            </tr>
          </thead>
          <tbody>
            {grupos.map((grupo) => (
              <Fragment key={grupo}>
                <tr className="bg-surface-2/40">
                  <td
                    colSpan={1 + data.cameras.length * 3}
                    className="px-3 py-1 text-[11px] font-medium uppercase tracking-wide text-muted"
                  >
                    {grupo}
                  </td>
                </tr>
                {data.rows
                  .filter((f) => f.group === grupo)
                  .map((fila) => (
                    <tr key={fila.code} className="border-b border-line/60 last:border-0">
                      <td className="sticky left-0 bg-surface px-3 py-1.5">
                        <div>{fila.label}</div>
                        <div className="font-mono text-[10px] text-muted">{fila.code}</div>
                      </td>
                      {data.cameras.flatMap((camara) =>
                        (['isapi', 'onvif', 'rtsp'] as Protocol[]).map((protocolo) => {
                          const celda = fila.cells.find(
                            (c) => c.camera_id === camara.id && c.protocol === protocolo,
                          )
                          const aplica = fila.protocols.includes(protocolo)
                          return (
                            <td
                              key={`${camara.id}-${protocolo}`}
                              className={cn(
                                'px-2 py-1.5 text-center',
                                protocolo === 'isapi' && 'border-l border-line',
                              )}
                            >
                              {!aplica && !celda ? (
                                <span className="text-muted/30">—</span>
                              ) : (
                                <Celda
                                  celda={celda}
                                  onClick={() =>
                                    celda && setDetalle({ fila: fila.label, celda })
                                  }
                                />
                              )}
                            </td>
                          )
                        }),
                      )}
                    </tr>
                  ))}
              </Fragment>
            ))}
          </tbody>
        </table>
      </Card>

      <div className="flex flex-wrap items-center gap-3 text-xs text-muted">
        {Object.entries(CELDA).map(([nivel, meta]) => (
          <span key={nivel} className="inline-flex items-center gap-1.5">
            <span
              className={cn(
                'inline-flex size-5 items-center justify-center rounded border font-mono',
                meta.clase,
              )}
            >
              {meta.texto}
            </span>
            {meta.titulo}
          </span>
        ))}
        <span className="inline-flex items-center gap-1.5">
          <Badge tone="accent">v</Badge> verificada llamándola
        </span>
        <span className="inline-flex items-center gap-1.5">
          <Badge>d</Badge> solo declarada por la cámara
        </span>
      </div>

      {detalle && (
        <Card className="space-y-2 p-4">
          <div className="flex items-center justify-between">
            <h2 className="font-medium">
              {detalle.fila} · {protocolMeta[detalle.celda.protocol].label}
            </h2>
            <button className="text-xs text-muted hover:text-fg" onClick={() => setDetalle(null)}>
              cerrar
            </button>
          </div>
          <div className="flex flex-wrap gap-3 text-xs text-muted">
            <span>{CELDA[detalle.celda.level].titulo}</span>
            <span>
              {detalle.celda.source === 'verified'
                ? 'verificada con una llamada real'
                : 'declarada por la cámara'}
            </span>
            {detalle.celda.latency_ms != null && (
              <span className="font-mono">{Math.round(detalle.celda.latency_ms)} ms</span>
            )}
          </div>
          <pre className="max-h-64 overflow-auto rounded-lg bg-bg p-3 font-mono text-[11px] text-muted">
            {JSON.stringify(detalle.celda.evidence, null, 2)}
          </pre>
        </Card>
      )}
    </div>
  )
}

function Celda({ celda, onClick }: { celda?: MatrixCell; onClick: () => void }) {
  const meta = CELDA[celda?.level ?? 'unverified']
  return (
    <button
      onClick={onClick}
      title={`${meta.titulo}${celda?.source === 'verified' ? ' (verificada)' : ' (declarada)'}`}
      className={cn(
        'relative inline-flex size-6 items-center justify-center rounded border font-mono text-xs transition hover:brightness-125',
        meta.clase,
      )}
    >
      {meta.texto}
      {celda?.source === 'verified' && (
        <span className="absolute -right-0.5 -top-0.5 size-1.5 rounded-full bg-accent" />
      )}
    </button>
  )
}

function descargarCsv(matriz: Matrix) {
  const filas = [['funcion', 'codigo', 'grupo', 'camara', 'protocolo', 'nivel', 'fuente', 'ms']]
  for (const fila of matriz.rows) {
    for (const celda of fila.cells) {
      const camara = matriz.cameras.find((c) => c.id === celda.camera_id)
      filas.push([
        fila.label,
        fila.code,
        fila.group,
        camara?.name ?? celda.camera_id,
        celda.protocol,
        celda.level,
        celda.source ?? '',
        celda.latency_ms != null ? String(Math.round(celda.latency_ms)) : '',
      ])
    }
  }
  const csv = filas.map((f) => f.map((v) => `"${v.replaceAll('"', '""')}"`).join(',')).join('\n')
  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }))
  const enlace = document.createElement('a')
  enlace.href = url
  enlace.download = `matriz-compatibilidad-${new Date().toISOString().slice(0, 10)}.csv`
  enlace.click()
  URL.revokeObjectURL(url)
}
