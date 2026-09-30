import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, Eraser, History, Pencil, Save, ShieldAlert, Spline } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'

import { ApiError, api } from '@/api/client'
import type { Camera, Rule, RuleKind, RuleKindInfo, RulePatch } from '@/api/types'
import { Badge, Button, Card, EmptyState, cn } from '@/components/ui'
import { RuleCanvas } from '@/features/rules/RuleCanvas'

type Point = [number, number]

const KIND_LABELS: Record<RuleKind, string> = {
  line: 'Cruce de línea',
  field: 'Intrusión',
  entrance: 'Entrada a zona',
  exiting: 'Salida de zona',
  ai_zone: 'Zona de IA',
  parking_space: 'Plaza',
}

const DIRECTION_LABELS: Record<string, string> = {
  any: 'Cualquiera',
  'a-b': 'A → B',
  'b-a': 'B → A',
}

const TARGET_LABELS: Record<string, string> = {
  human: 'Persona',
  vehicle: 'Vehículo',
  others: 'Otros',
}

/** Las tres familias de analítica encontradas, cada una con su formato y su forma de activarse.
 * Cuál responde lo decide el modo de VCA del equipo, que es excluyente (ver tesis §7.2.2). */
const FAMILY_META: Record<string, { nombre: string; formato: string; descripcion: string }> = {
  smart: {
    nombre: 'ISAPI Smart',
    formato: 'XML, 0–1000',
    descripcion:
      'Analítica clásica. El interruptor activa el tipo de regla entero, no cada regla: es así en la cámara.',
  },
  aiop: {
    nombre: 'AI Open Platform',
    formato: 'JSON, 0–1',
    descripcion:
      'La analítica la define la app de IA instalada en la cámara. Cada regla se activa por separado.',
  },
  parking: {
    nombre: 'ISAPI Parking',
    formato: 'JSON, 0–1, polígonos de 4 puntos',
    descripcion:
      'Reconocimiento de plazas de estacionamiento. Cada plaza es un cuadrilátero y un solo interruptor activa toda la función. La cámara rechaza plazas que se superpongan.',
  },
}

export function RulesTab({ camera }: { camera: Camera }) {
  const queryClient = useQueryClient()
  const { data, error, isLoading } = useQuery({
    queryKey: ['rules', camera.id],
    queryFn: () => api.rules(camera.id),
    retry: false,
  })

  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [selectedKind, setSelectedKind] = useState<RuleKind | null>(null)
  const [draft, setDraft] = useState<Point[]>([])
  const [drawing, setDrawing] = useState(false)
  const [patch, setPatch] = useState<RulePatch>({})
  const snapshotUrl = useMemo(() => api.snapshotUrl(camera.id), [camera.id])

  const rules = data?.rules ?? []
  const kinds = data?.kinds ?? []
  const selected = rules.find((r) => r.external_id === selectedId && r.kind === selectedKind)
  const kindInfo = kinds.find((k) => k.kind === selectedKind)

  // Al cargar, se abre la primera regla que tenga geometría. Depende solo de `data`: si
  // dependiera de la selección, volvería a abrir la primera cada vez que el usuario cambia.
  useEffect(() => {
    if (selectedId || rules.length === 0) return
    seleccionar(rules.find((r) => r.configured) ?? rules[0])
  }, [data])

  function seleccionar(regla: Rule) {
    setSelectedId(regla.external_id)
    setSelectedKind(regla.kind)
    setDraft(regla.points)
    setPatch({})
    setDrawing(false)
  }

  const guardar = useMutation({
    mutationFn: () => {
      const cambios: RulePatch = { ...patch }
      if (JSON.stringify(draft) !== JSON.stringify(selected?.points)) cambios.points = draft
      return api.patchRule(camera.id, selected!.kind, selected!.external_id, cambios)
    },
    onSuccess: (regla) => {
      queryClient.invalidateQueries({ queryKey: ['rules', camera.id] })
      queryClient.invalidateQueries({ queryKey: ['backups', camera.id] })
      seleccionar(regla)
    },
  })

  if (isLoading) return <div className="h-96 animate-pulse rounded-xl bg-surface" />
  if (error) {
    return (
      <EmptyState icon={<ShieldAlert className="size-8" />} title="No se pudieron leer las reglas">
        {error instanceof ApiError ? error.message : 'Error desconocido'}
      </EmptyState>
    )
  }
  if (!data || data.family === 'none' || rules.length === 0) {
    return (
      <EmptyState icon={<Spline className="size-8" />} title="Sin reglas de analítica">
        {data?.note ?? 'Esta cámara no expone reglas por ninguna de las dos familias conocidas.'}
      </EmptyState>
    )
  }

  const maxPoints = kindInfo?.max_points ?? 10
  const minPoints = kindInfo?.min_points ?? 2
  const puntosListos = draft.length >= minPoints
  const hayCambios =
    Object.keys(patch).length > 0 || JSON.stringify(draft) !== JSON.stringify(selected?.points)

  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
      <div className="space-y-3">
        <RuleCanvas
          snapshotUrl={snapshotUrl}
          rules={rules}
          selectedId={selectedId}
          draft={draft}
          drawing={drawing}
          maxPoints={maxPoints}
          onChange={setDraft}
          onSelect={seleccionar}
        />

        <div className="flex flex-wrap items-center gap-2">
          <Button
            variant={drawing ? 'primary' : 'secondary'}
            icon={<Pencil className="size-4" />}
            onClick={() => {
              setDrawing(!drawing)
              if (!drawing) setDraft([])
            }}
          >
            {drawing ? `Marcando puntos (${draft.length}/${maxPoints})` : 'Dibujar de nuevo'}
          </Button>
          <Button
            icon={<Eraser className="size-4" />}
            onClick={() => setDraft(selected?.points ?? [])}
            disabled={!hayCambios}
          >
            Descartar
          </Button>
          {drawing && puntosListos && (
            <Button icon={<Check className="size-4" />} onClick={() => setDrawing(false)}>
              Listo
            </Button>
          )}
          <span className="text-xs text-muted">
            {drawing
              ? `Hacé clic sobre la imagen: ${minPoints === maxPoints ? minPoints : `${minPoints} a ${maxPoints}`} puntos.`
              : 'Arrastrá los puntos para mover la regla.'}
          </span>
        </div>

        {guardar.error instanceof ApiError && (
          <Card className="border-bad/40 bg-bad/5 p-3 text-sm text-bad">
            {guardar.error.code === 'verification_failed' ? (
              <>
                <strong>La cámara no aplicó el cambio.</strong> Respondió que sí, pero al releer el
                recurso seguía como antes. {guardar.error.message}
              </>
            ) : (
              guardar.error.message
            )}
          </Card>
        )}
        {guardar.isSuccess && !hayCambios && (
          <Card className="border-ok/40 bg-ok/5 p-3 text-sm text-ok">
            Guardado y verificado: se releyó el recurso y la cámara tiene lo que se pidió.
          </Card>
        )}
      </div>

      <div className="space-y-4">
        <FamilyCard family={data.family} note={data.note} kinds={kinds} />

        <Card className="divide-y divide-line">
          {rules.map((regla) => {
            const activa = regla.external_id === selectedId && regla.kind === selectedKind
            return (
              <button
                key={`${regla.kind}-${regla.external_id}`}
                onClick={() => seleccionar(regla)}
                className={cn(
                  'flex w-full items-center justify-between gap-2 px-3 py-2 text-left text-sm transition',
                  activa ? 'bg-surface-2 text-fg' : 'text-muted hover:text-fg',
                )}
              >
                <span className="truncate">
                  {regla.name ?? `${KIND_LABELS[regla.kind]} ${regla.external_id}`}
                  {!regla.configured && <span className="ml-1.5 text-xs text-muted">(vacía)</span>}
                </span>
                <Ocupacion regla={regla} />
                <Badge tone={regla.enabled ? 'ok' : 'neutral'}>
                  {regla.enabled ? 'activa' : 'apagada'}
                </Badge>
              </button>
            )
          })}
        </Card>

        {selected && kindInfo && (
          <RuleForm
            rule={selected}
            info={kindInfo}
            patch={patch}
            onPatch={(cambio) => setPatch({ ...patch, ...cambio })}
          />
        )}

        <Button
          variant="primary"
          className="w-full"
          icon={<Save className="size-4" />}
          loading={guardar.isPending}
          disabled={!hayCambios || !puntosListos}
          onClick={() => guardar.mutate()}
        >
          Guardar en la cámara
        </Button>

        <BackupsCard cameraId={camera.id} />
      </div>
    </div>
  )
}

/** Solo las plazas de parking traen ocupación en vivo; el resto de las familias no la tiene. */
function Ocupacion({ regla }: { regla: Rule }) {
  const ocupada = regla.extra?.ocupada
  if (typeof ocupada !== 'boolean') return null
  const segundos = regla.extra?.segundos_estacionado
  const hace =
    typeof segundos === 'number' && segundos > 0 ? ` · ${Math.round(segundos / 60)} min` : ''
  return (
    <Badge tone={ocupada ? 'warn' : 'ok'}>{ocupada ? `ocupada${hace}` : 'libre'}</Badge>
  )
}

function FamilyCard({
  family,
  note,
  kinds,
}: {
  family: string
  note: string | null
  kinds: RuleKindInfo[]
}) {
  const meta = FAMILY_META[family] ?? FAMILY_META.smart
  return (
    <Card className="space-y-2 p-3 text-xs">
      <div className="flex items-center gap-2">
        <Badge tone="accent">{meta.nombre}</Badge>
        <span className="text-muted">{meta.formato}</span>
      </div>
      <p className="text-muted">{meta.descripcion}</p>
      {note && <p className="text-warn">{note}</p>}
      <div className="flex flex-wrap gap-1">
        {kinds.map((k) => (
          <Badge key={k.kind} tone={k.enabled ? 'ok' : 'neutral'}>
            {KIND_LABELS[k.kind]} {k.max_rules > 1 && `·${k.max_rules}`}
          </Badge>
        ))}
      </div>
    </Card>
  )
}

function RuleForm({
  rule,
  info,
  patch,
  onPatch,
}: {
  rule: Rule
  info: RuleKindInfo
  patch: RulePatch
  onPatch: (cambio: RulePatch) => void
}) {
  const enabled = patch.enabled ?? rule.enabled
  const sensitivity = patch.sensitivity ?? rule.sensitivity ?? 50
  const direction = patch.direction ?? rule.direction ?? 'any'
  const target = patch.target ?? rule.target

  return (
    <Card className="space-y-3 p-3">
      <label className="flex items-center justify-between gap-2 text-sm">
        <span>
          {info.toggle_per_rule ? 'Regla activa' : 'Tipo de regla activo'}
          {!info.toggle_per_rule && (
            <span className="block text-[11px] text-muted">Afecta a todas las de este tipo</span>
          )}
        </span>
        <input
          type="checkbox"
          checked={enabled}
          onChange={(e) => onPatch({ enabled: e.target.checked })}
          className="size-4 accent-[var(--color-accent)]"
        />
      </label>

      {rule.sensitivity !== null && (
        <label className="block space-y-1 text-sm">
          <span className="flex justify-between text-xs text-muted">
            <span>Sensibilidad</span>
            <span className="font-mono text-fg">{sensitivity}</span>
          </span>
          <input
            type="range"
            min={1}
            max={100}
            value={sensitivity}
            onChange={(e) => onPatch({ sensitivity: Number(e.target.value) })}
            className="w-full accent-[var(--color-accent)]"
          />
        </label>
      )}

      {info.directions.length > 0 && (
        <label className="block space-y-1">
          <span className="text-xs text-muted">Dirección del cruce</span>
          <select
            value={direction}
            onChange={(e) => onPatch({ direction: e.target.value })}
            className="h-9 w-full rounded-lg border border-line bg-bg px-2 text-sm outline-none focus:border-accent"
          >
            {info.directions.map((d) => (
              <option key={d} value={d}>
                {DIRECTION_LABELS[d] ?? d}
              </option>
            ))}
          </select>
        </label>
      )}

      {info.targets.length > 0 && (
        <div className="space-y-1">
          <span className="text-xs text-muted">Qué detecta</span>
          <div className="flex flex-wrap gap-1.5">
            {info.targets.map((t) => {
              const activo = target.includes(t)
              return (
                <button
                  key={t}
                  onClick={() =>
                    onPatch({
                      target: activo ? target.filter((x) => x !== t) : [...target, t],
                    })
                  }
                  className={cn(
                    'rounded-md border px-2 py-0.5 text-xs transition',
                    activo
                      ? 'border-accent/30 bg-accent/10 text-accent'
                      : 'border-line text-muted hover:text-fg',
                  )}
                >
                  {TARGET_LABELS[t] ?? t}
                </button>
              )
            })}
          </div>
        </div>
      )}

      {rule.extra.confidence !== undefined && (
        <p className="text-[11px] text-muted">
          Confianza mínima {String(rule.extra.confidence)}/1000 · intervalo entre avisos{' '}
          {String(rule.extra.trigger_interval_s)} s
        </p>
      )}
    </Card>
  )
}

function BackupsCard({ cameraId }: { cameraId: string }) {
  const queryClient = useQueryClient()
  const { data } = useQuery({
    queryKey: ['backups', cameraId],
    queryFn: () => api.backups(cameraId),
  })
  const restaurar = useMutation({
    mutationFn: (id: string) => api.restoreBackup(cameraId, id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['rules', cameraId] }),
  })

  if (!data || data.length === 0) return null
  return (
    <Card className="space-y-2 p-3">
      <div className="flex items-center gap-1.5 text-xs font-medium text-muted">
        <History className="size-3.5" /> Respaldos antes de escribir
      </div>
      <ul className="space-y-1">
        {data.slice(0, 5).map((backup) => (
          <li key={backup.id} className="flex items-center justify-between gap-2 text-xs">
            <span className="truncate font-mono text-muted" title={backup.resource}>
              {backup.resource.replace('/ISAPI/', '')}
            </span>
            <button
              onClick={() => restaurar.mutate(backup.id)}
              className="shrink-0 text-accent hover:underline"
            >
              restaurar
            </button>
          </li>
        ))}
      </ul>
    </Card>
  )
}
