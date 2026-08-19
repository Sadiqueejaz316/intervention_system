import type { ReactNode } from 'react'

import { useDomainConfig } from '@/hooks/queries'

export function AuthCard({
  title,
  subtitle,
  children,
  footer,
}: {
  title: string
  subtitle: string
  children: ReactNode
  footer?: ReactNode
}) {
  const { data: config } = useDomainConfig()

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <section className="hidden flex-col justify-between bg-brand-600 p-10 text-white lg:flex">
        <div className="flex items-center gap-2">
          <span className="grid size-9 place-items-center rounded-lg bg-white/15 font-bold">
            IS
          </span>
          <span className="font-semibold">
            {config?.domain_name ?? 'Intervention System'}
          </span>
        </div>

        <div className="max-w-md">
          <h2 className="text-3xl font-semibold leading-tight">
            From report to resolution, with everyone in the loop.
          </h2>
          <p className="mt-3 text-white/80">
            Issues are reported, queued by urgency, dispatched to the right
            {' '}
            {(config?.worker_label ?? 'worker').toLowerCase()}, and tracked through to
            closure — with a full timeline behind every step.
          </p>

          <ol className="mt-8 space-y-2 text-sm text-white/85">
            {['Open', 'Assigned', 'In progress', 'Resolved', 'Closed'].map(
              (step, index) => (
                <li key={step} className="flex items-center gap-3">
                  <span className="grid size-6 shrink-0 place-items-center rounded-full bg-white/15 text-xs font-semibold">
                    {index + 1}
                  </span>
                  {step}
                </li>
              ),
            )}
          </ol>
        </div>

        <p className="text-xs text-white/60">Secured with JWT authentication.</p>
      </section>

      <section className="flex items-center justify-center p-6">
        <div className="w-full max-w-sm">
          <h1 className="text-2xl font-semibold tracking-tight text-ink">{title}</h1>
          <p className="mt-1 mb-6 text-sm text-muted">{subtitle}</p>

          {children}

          {footer && <div className="mt-6">{footer}</div>}
        </div>
      </section>
    </div>
  )
}
