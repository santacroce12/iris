import { Hourglass } from 'lucide-react'
import type { ReactNode } from 'react'

import { Badge, EmptyState } from '@/components/ui'

export function ComingSoon({
  title,
  phase,
  children,
}: {
  title: string
  phase: string
  children: ReactNode
}) {
  return (
    <div className="space-y-6">
      <header className="flex items-center gap-3">
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        <Badge tone="accent">{phase}</Badge>
      </header>
      <EmptyState icon={<Hourglass className="size-8" />} title="Todavía no implementado">
        {children}
      </EmptyState>
    </div>
  )
}
