import { useQueryClient } from '@tanstack/react-query'
import { createContext, type ReactNode, useContext, useEffect, useRef, useState } from 'react'

import type { LiveEvent } from '@/api/types'

type Estado = 'conectando' | 'en_vivo' | 'desconectado'

interface EventStreamValue {
  estado: Estado
  /** Últimos episodios recibidos (nuevos o actualizados), el más reciente primero. */
  recientes: LiveEvent[]
  /** Se incrementa con cada mensaje: sirve para disparar efectos (avisos, contadores). */
  ultimo: LiveEvent | null
}

const MAX_RECIENTES = 200

const Ctx = createContext<EventStreamValue>({ estado: 'conectando', recientes: [], ultimo: null })

/** Una sola conexión SSE para toda la app: el feed y los avisos la comparten. */
export function EventStreamProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  const [estado, setEstado] = useState<Estado>('conectando')
  const [recientes, setRecientes] = useState<LiveEvent[]>([])
  const [ultimo, setUltimo] = useState<LiveEvent | null>(null)
  const invalidar = useRef<number | undefined>(undefined)

  useEffect(() => {
    let fuente: EventSource | undefined
    let reintento: number | undefined
    let espera = 1000
    let activo = true

    const conectar = () => {
      fuente = new EventSource('/api/events/stream')
      fuente.onopen = () => {
        espera = 1000
        setEstado('en_vivo')
        // Lo ocurrido mientras estuvo caído se trae del historial.
        queryClient.invalidateQueries({ queryKey: ['events'] })
      }
      fuente.onerror = () => {
        if (fuente?.readyState !== EventSource.CLOSED) {
          setEstado('conectando') // el navegador reintenta solo
          return
        }
        // Si el backend respondió con error (p. ej. todavía arrancando), EventSource no
        // reintenta nunca más: hay que volver a crearlo, con espera creciente.
        setEstado('desconectado')
        if (activo) reintento = window.setTimeout(conectar, espera)
        espera = Math.min(espera * 2, 15000)
      }
      fuente.addEventListener('camera-event', (mensaje) => {
        const evento: LiveEvent = JSON.parse((mensaje as MessageEvent).data)
        setUltimo(evento)
        // Un episodio se actualiza varias veces (más avisos, cierre): se reemplaza, no se duplica.
        setRecientes((prev) =>
          [evento, ...prev.filter((e) => e.id !== evento.id)].slice(0, MAX_RECIENTES),
        )
        // El historial se refresca agrupado, no una vez por mensaje.
        window.clearTimeout(invalidar.current)
        invalidar.current = window.setTimeout(
          () => queryClient.invalidateQueries({ queryKey: ['events'] }),
          1500,
        )
      })
    }

    conectar()
    return () => {
      activo = false
      window.clearTimeout(reintento)
      window.clearTimeout(invalidar.current)
      fuente?.close()
    }
  }, [queryClient])

  return <Ctx.Provider value={{ estado, recientes, ultimo }}>{children}</Ctx.Provider>
}

export function useEventStream() {
  return useContext(Ctx)
}
