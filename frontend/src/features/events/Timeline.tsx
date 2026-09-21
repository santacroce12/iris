import { useMemo } from 'react'

import type { CameraEvent } from '@/api/types'
import { eventMeta } from '@/features/events/eventTypes'

const COLUMNAS = 48

/** Histograma simple: cuántos episodios hubo en cada franja del rango elegido. */
export function Timeline({ eventos, desde }: { eventos: CameraEvent[]; desde: string }) {
  const { franjas, maximo, inicio, paso } = useMemo(() => {
    const inicio = new Date(desde).getTime()
    const paso = Math.max(1, (Date.now() - inicio) / COLUMNAS)
    const franjas = Array.from({ length: COLUMNAS }, () => ({ analitica: 0, otros: 0 }))
    for (const e of eventos) {
      const i = Math.floor((new Date(e.occurred_at).getTime() - inicio) / paso)
      if (i < 0 || i >= COLUMNAS) continue
      if (eventMeta(e.type).analytic) franjas[i].analitica += 1
      else franjas[i].otros += 1
    }
    const maximo = Math.max(1, ...franjas.map((f) => f.analitica + f.otros))
    return { franjas, maximo, inicio, paso }
  }, [eventos, desde])

  const hora = (ms: number) =>
    new Date(ms).toLocaleString([], { hour: '2-digit', minute: '2-digit', day: '2-digit', month: '2-digit' })

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-xs text-muted">
        <span>Actividad en el rango</span>
        <span className="flex gap-3">
          <span className="inline-flex items-center gap-1.5">
            <span className="size-2 rounded-sm bg-accent" /> analítica
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="size-2 rounded-sm bg-isapi/60" /> movimiento y técnicos
          </span>
        </span>
      </div>
      <div className="flex h-20 items-end gap-px">
        {franjas.map((f, i) => {
          const total = f.analitica + f.otros
          return (
            <div
              key={i}
              className="flex h-full flex-1 flex-col justify-end"
              title={`${hora(inicio + i * paso)} — ${total} episodios`}
            >
              {f.otros > 0 && <div className="bg-isapi/60" style={{ height: `${(f.otros / maximo) * 100}%` }} />}
              {f.analitica > 0 && (
                <div className="rounded-t-sm bg-accent" style={{ height: `${(f.analitica / maximo) * 100}%` }} />
              )}
              {total === 0 && <div className="h-px bg-line" />}
            </div>
          )
        })}
      </div>
      <div className="flex justify-between font-mono text-[10px] text-muted">
        <span>{hora(inicio)}</span>
        <span>ahora</span>
      </div>
    </div>
  )
}
