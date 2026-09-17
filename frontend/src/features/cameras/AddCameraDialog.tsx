import { useMutation, useQueryClient } from '@tanstack/react-query'
import { type FormEvent, useState } from 'react'
import { useNavigate } from 'react-router'

import { api } from '@/api/client'
import type { CameraCreate, NetworkMode } from '@/api/types'
import { Button, Dialog, Field, cn } from '@/components/ui'

const initial: CameraCreate = {
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

export function AddCameraDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [form, setForm] = useState(initial)
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  const create = useMutation({
    mutationFn: async (data: CameraCreate) => {
      const camera = await api.createCamera({
        ...data,
        onvif_username: data.onvif_username || null,
        onvif_password: data.onvif_password || null,
      })
      // Se prueba enseguida para que la cámara aparezca con sus 3 luces cargadas.
      await api.testConnection(camera.id).catch(() => undefined)
      return camera
    },
    onSuccess: (camera) => {
      queryClient.invalidateQueries({ queryKey: ['cameras'] })
      setForm(initial)
      onClose()
      navigate(`/camaras/${camera.id}`)
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
    create.mutate(form)
  }

  return (
    <Dialog open={open} onClose={onClose} title="Agregar cámara">
      <form onSubmit={submit} className="space-y-5">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Nombre" required placeholder="Acceso vehicular" {...text('name')} />
          <Field label="Host / IP" required placeholder="192.168.1.64" {...text('host')} />
          <Field label="Usuario" required autoComplete="off" {...text('username')} />
          <Field
            label="Contraseña"
            type="password"
            required
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

        <details className="group rounded-lg border border-line px-4 py-3">
          <summary className="cursor-pointer text-sm text-muted select-none group-open:mb-4">
            Puertos, canal y usuario ONVIF
          </summary>
          <div className="grid gap-4 sm:grid-cols-4">
            <Field label="HTTP" type="number" {...text('http_port')} />
            <Field label="RTSP" type="number" {...text('rtsp_port')} />
            <Field label="ONVIF" type="number" {...text('onvif_port')} />
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
              hint="Hikvision usa un usuario aparte (Configuración → Red → Integración)."
              autoComplete="off"
              {...text('onvif_username')}
            />
            <Field
              label="Contraseña ONVIF"
              type="password"
              autoComplete="new-password"
              {...text('onvif_password')}
            />
          </div>
        </details>

        {create.error && (
          <p className="rounded-lg border border-bad/30 bg-bad/10 px-3 py-2 text-sm text-bad">
            {create.error.message}
          </p>
        )}

        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          <Button type="submit" variant="primary" loading={create.isPending}>
            {create.isPending ? 'Probando protocolos…' : 'Agregar y probar'}
          </Button>
        </div>
      </form>
    </Dialog>
  )
}
