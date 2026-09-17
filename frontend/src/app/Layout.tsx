import { Activity, Cctv, Grid3x3, ScanEye } from 'lucide-react'
import { NavLink, Outlet } from 'react-router'

import { cn } from '@/components/ui'

const nav = [
  { to: '/', label: 'Cámaras', icon: Cctv, end: true },
  { to: '/eventos', label: 'Eventos', icon: Activity },
  { to: '/matriz', label: 'Matriz', icon: Grid3x3 },
]

export function Layout() {
  return (
    <div className="flex h-full flex-col md:flex-row">
      <aside className="flex shrink-0 items-center gap-1 border-b border-line bg-surface/60 px-3 py-2 md:w-60 md:flex-col md:items-stretch md:border-r md:border-b-0 md:px-4 md:py-6">
        <div className="mr-3 flex items-center gap-2.5 md:mr-0 md:mb-8 md:px-2">
          <div className="grid size-8 place-items-center rounded-lg bg-accent/15 text-accent ring-1 ring-accent/30">
            <ScanEye className="size-4.5" />
          </div>
          <div className="leading-tight">
            <p className="font-semibold tracking-tight">Vigía</p>
            <p className="hidden text-[11px] text-muted md:block">ISAPI · ONVIF · RTSP</p>
          </div>
        </div>
        <nav className="flex gap-1 md:flex-col">
          {nav.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition',
                  isActive
                    ? 'bg-surface-2 text-fg ring-1 ring-line'
                    : 'text-muted hover:bg-surface-2/60 hover:text-fg',
                )
              }
            >
              <Icon className="size-4" />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <p className="mt-auto hidden px-2 text-[11px] leading-relaxed text-muted/70 md:block">
          Plataforma unificada de cámaras IP
          <br />
          Tesis · Luca Santacroce
        </p>
      </aside>
      <main className="min-w-0 flex-1 overflow-y-auto">
        <div className="mx-auto max-w-7xl px-4 py-6 md:px-8 md:py-8">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
