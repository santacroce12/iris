import { useMutation, useQueryClient } from '@tanstack/react-query'
import { type FormEvent, useState } from 'react'
import { useNavigate } from 'react-router'

import { api } from '@/api/client'
import type { Camera, CameraCreate, CameraUpdate, NetworkMode } from '@/api/types'
import { Button, Dialog, Field, cn } from '@/components/ui'

const empty: CameraCreate = {
  name: '',
  host: '',
  http_port: 80,
  use_https: false,
  rtsp_port: 554,
  onvif_port: 80,
  channel: 1,
  username: 'admin',
  password: '',
  onvif_username: '',
  onvif_password: '',
  network_mode: 'lan',
}

function fromCamera(camera: Camera): CameraCreate {
  return {
    name: camera.name,
    host: camera.host,
    http_port: camera.http_port,
    use_https: camera.use_https,
    rtsp_port: camera.rtsp_port,
    onvif_port: camera.onvif_port,
    channel: camera.channel,
    username: camera.username,
    // Las contraseñas nunca vienen del backend: en blanco significa "conservar".
    password: '',
    onvif_username: camera.onvif_username ?? '',
    onvif_password: '',
    network_mode: camera.network_mode,
  }
}

interface Props {
  open: boolean
  onClose: () => void
  camera?: Camera
}

/** Alta de cámara, o edición si se pasa `camera`. */
export function CameraFormDialog({ open, onClose, camera }: Props) {
  return (
    <Dialog open={open} onClose={onClose} title={camera ? 'Editar cámara' : 'Agregar cámara'}>
      {/* Montado solo mientras está abierto: cada apertura parte de los datos actuales. */}
      {open && <CameraForm onClose={onClose} camera={camera} />}
    </Dialog>
  )
}

function CameraForm({ onClose, camera }: Omit<Props, 'open'>) {
  const editing = Boolean(camera)
  const [form, setForm] = useState<CameraCreate>(() => (camera ? fromCamera(camera) : empty))
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  const save = useMutation({
    mutationFn: async (data: CameraCreate) => {
      let saved: Camera
      if (camera) {
        const update: CameraUpdate = { ...data, onvif_username: data.onvif_username || null }
        if (!data.password) delete update.password
        if (!data.onvif_password) delete update.onvif_password
        saved = await api.updateCamera(camera.id, update)
      } else {
        saved = await api.createCamera({
          ...data,
          onvif_username: data.onvif_username || null,
          onvif_password: data.onvif_password || null,
        })
      }
      // Si cambió cómo se llega a la cámara, se vuelve a probar para actualizar las 3 luces.
      if (saved.status === 'unknown') await api.testConnection(saved.id).catch(() => undefined)
      return saved
    },
    onSuccess: (saved) => {
      queryClient.invalidateQueries()
      onClose()
      if (!editing) navigate(`/camaras/${saved.id}`)
    },
  })

  const set = <K extends keyof CameraCreate>(key: K, value: CameraCreate[K]) =>
    setForm((f) => ({ ...f, [key]: value }))
  const text = (key: keyof CameraCreate) => ({
    value: String(form[key] ?? ''),
    onChange: (e: React.ChangeEvent<HTMLInputElement>) =>
      set(key, (e.target.type === 'number' ? Number(e.target.value) : e.target.value) as never),
  })

  const submit = (e: FormEvent) => {
    e.preventDefault()
    save.mutate(form)
  }

  const keepHint = editing ? 'Dejar en blanco para conservar la actual.' : undefined

  return (
    <form onSubmit={submit} className="space-y-5">
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Nombre" required placeholder="Acceso vehicular" {...text('name')} />
        <Field label="Host / IP" required placeholder="192.168.1.64" {...text('host')} />
        <Field label="Usuario" required autoComplete="off" {...text('username')} />
        <Field
          label="Contraseña"
          type="password"
          required={!editing}
          placeholder={editing ? '••••••••' : undefined}
          hint={keepHint}
          autoComplete="new-password"
          {...text('password')}
        />
      </div>

      <fieldset className="space-y-2">
        <legend className="text-xs font-medium text-muted">¿Cómo se llega a la cámara?</legend>
        <div className="grid grid-cols-2 gap-2">
          {(['lan', 'vpn'] as NetworkMode[]).map((mode) => (
            <button
              type="button"
              key={mode}
              onClick={() => set('network_mode', mode)}
              className={cn(
                'rounded-lg border px-3 py-2 text-left text-sm transition',
                form.network_mode === mode
                  ? 'border-accent bg-accent/10'
                  : 'border-line hover:border-muted/50',
              )}
            >
              <p className="font-medium">{mode === 'lan' ? 'Red local' : 'VPN'}</p>
              <p className="text-xs text-muted">
                {mode === 'lan' ? 'Misma red que esta PC' : 'Timeouts más tolerantes'}
              </p>
            </button>
          ))}
        </div>
      </fieldset>

      {/* Al editar se abre de entrada: suele ser lo que se viene a cambiar. */}
      <details className="group rounded-lg border border-line px-4 py-3" open={editing}>
        <summary className="cursor-pointer text-sm text-muted select-none group-open:mb-4">
          Puertos, canal y usuario ONVIF
        </summary>
        <div className="grid gap-4 sm:grid-cols-4">
          <Field label="HTTP" type="number" min={1} max={65535} {...text('http_port')} />
          <Field label="RTSP" type="number" min={1} max={65535} {...text('rtsp_port')} />
          <Field label="ONVIF" type="number" min={1} max={65535} {...text('onvif_port')} />
          <Field label="Canal" type="number" min={1} {...text('channel')} />
        </div>
        <label className="mt-4 flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={form.use_https}
            onChange={(e) => set('use_https', e.target.checked)}
            className="accent-accent"
          />
          Usar HTTPS para ISAPI
        </label>
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <Field
            label="Usuario ONVIF"
            hint="Hikvision usa un usuario aparte (Configuración → Red → Integración). Vacío = usar el principal."
            autoComplete="off"
            {...text('onvif_username')}
          />
          <Field
            label="Contraseña ONVIF"
            type="password"
            placeholder={editing && camera?.onvif_username ? '••••••••' : undefined}
            hint={editing && camera?.onvif_username ? keepHint : undefined}
            autoComplete="new-password"
            {...text('onvif_password')}
          />
        </div>
      </details>

      {save.error && (
        <p className="rounded-lg border border-bad/30 bg-bad/10 px-3 py-2 text-sm text-bad">
          {save.error.message}
        </p>
      )}

      <div className="flex justify-end gap-2">
        <Button type="button" variant="ghost" onClick={onClose}>
          Cancelar
        </Button>
        <Button type="submit" variant="primary" loading={save.isPending}>
          {save.isPending
            ? 'Guardando y probando…'
            : editing
              ? 'Guardar cambios'
              : 'Agregar y probar'}
        </Button>
      </div>
    </form>
  )
}
