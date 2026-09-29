import { useEffect, useRef, useState } from 'react'

import type { Rule } from '@/api/types'
import { cn } from '@/components/ui'

type Point = [number, number]

/** Radio del manejador en pixeles: cómodo de agarrar con el mouse sin tapar la imagen. */
const RADIO = 7

interface Props {
  snapshotUrl: string
  rules: Rule[]
  selectedId: string | null
  /** Puntos que se están editando (0..1, origen arriba a la izquierda). */
  draft: Point[]
  drawing: boolean
  maxPoints: number
  onChange: (points: Point[]) => void
  onSelect: (rule: Rule) => void
}

export function RuleCanvas({
  snapshotUrl,
  rules,
  selectedId,
  draft,
  drawing,
  maxPoints,
  onChange,
  onSelect,
}: Props) {
  const boxRef = useRef<HTMLDivElement>(null)
  const [size, setSize] = useState({ width: 0, height: 0 })
  // En una referencia y no en estado: el pointermove puede llegar antes de que React
  // aplique el setState del pointerdown, y el arrastre se perdía.
  const dragging = useRef<number | null>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    const box = boxRef.current
    if (!box) return
    const observer = new ResizeObserver(([entry]) => {
      const { width, height } = entry.contentRect
      setSize({ width, height })
    })
    observer.observe(box)
    return () => observer.disconnect()
  }, [])

  const toPixels = ([x, y]: Point): Point => [x * size.width, y * size.height]

  function fromEvent(event: { clientX: number; clientY: number }): Point {
    const box = boxRef.current!.getBoundingClientRect()
    const x = (event.clientX - box.left) / box.width
    const y = (event.clientY - box.top) / box.height
    return [Math.min(1, Math.max(0, x)), Math.min(1, Math.max(0, y))]
  }

  function handleClick(event: React.MouseEvent) {
    if (!drawing || draft.length >= maxPoints) return
    onChange([...draft, fromEvent(event)])
  }

  function startDrag(index: number, event: React.PointerEvent) {
    event.stopPropagation()
    event.preventDefault()
    ;(event.target as Element).setPointerCapture(event.pointerId)
    dragging.current = index
  }

  function handleMove(event: React.PointerEvent) {
    if (dragging.current === null) return
    const siguiente = [...draft]
    siguiente[dragging.current] = fromEvent(event)
    onChange(siguiente)
  }

  const cerrado = draft.length > 2

  return (
    <div
      ref={boxRef}
      className={cn(
        'relative overflow-hidden rounded-xl border border-line bg-black',
        drawing && draft.length < maxPoints ? 'cursor-crosshair' : 'cursor-default',
      )}
      onClick={handleClick}
      onPointerMove={handleMove}
      onPointerUp={() => {
        dragging.current = null
      }}
    >
      {failed ? (
        <div className="flex aspect-video items-center justify-center text-sm text-muted">
          No se pudo traer la imagen de la cámara
        </div>
      ) : (
        <img
          src={snapshotUrl}
          alt="Vista de la cámara"
          className="block w-full select-none"
          draggable={false}
          onError={() => setFailed(true)}
        />
      )}

      <svg
        className="absolute inset-0 size-full"
        width={size.width}
        height={size.height}
        style={{ touchAction: 'none' }}
      >
        {/* Las demás reglas, apagadas, para no perder el contexto de la escena. */}
        {rules
          .filter((r) => r.configured && r.external_id !== selectedId)
          .map((regla) => (
            <Shape
              key={`${regla.kind}-${regla.external_id}`}
              points={regla.points.map(toPixels)}
              closed={regla.points.length > 2}
              className="cursor-pointer"
              stroke={regla.enabled ? 'rgb(148 163 184 / 0.75)' : 'rgb(100 116 139 / 0.45)'}
              onClick={(event) => {
                event.stopPropagation()
                onSelect(regla)
              }}
            />
          ))}

        {draft.length > 0 && (
          <>
            <Shape points={draft.map(toPixels)} closed={cerrado} stroke="var(--color-accent)" />
            {draft.map((punto, indice) => {
              const [x, y] = toPixels(punto)
              return (
                <circle
                  key={indice}
                  cx={x}
                  cy={y}
                  r={RADIO}
                  className="cursor-grab fill-accent stroke-bg active:cursor-grabbing"
                  strokeWidth={2}
                  onPointerDown={(event) => startDrag(indice, event)}
                />
              )
            })}
            {/* En una línea, el primer punto es A: marca de qué lado se cruza. */}
            {draft.length === 2 && <Etiqueta points={draft.map(toPixels)} />}
          </>
        )}
      </svg>
    </div>
  )
}

function Shape({
  points,
  closed,
  stroke,
  className,
  onClick,
}: {
  points: Point[]
  closed: boolean
  stroke: string
  className?: string
  onClick?: (event: React.MouseEvent) => void
}) {
  const d = points.map(([x, y]) => `${x},${y}`).join(' ')
  const Tag = closed ? 'polygon' : 'polyline'
  return (
    <Tag
      points={d}
      fill={closed ? 'rgb(56 189 248 / 0.12)' : 'none'}
      stroke={stroke}
      strokeWidth={2}
      strokeLinejoin="round"
      className={className}
      onClick={onClick}
    />
  )
}

function Etiqueta({ points }: { points: Point[] }) {
  const [[ax, ay], [bx, by]] = points
  return (
    <>
      <text x={ax} y={ay - 12} className="fill-accent text-[11px] font-semibold">
        A
      </text>
      <text x={bx} y={by - 12} className="fill-accent text-[11px] font-semibold">
        B
      </text>
    </>
  )
}
