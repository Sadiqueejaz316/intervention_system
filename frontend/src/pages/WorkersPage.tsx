import { useState } from 'react'

import {
  Chip,
  EmptyState,
  ErrorState,
  PageHeader,
  Skeleton,
} from '@/components/ui'
import { classes } from '@/lib/format'
import { skillLabel } from '@/lib/domain'
import { useDomainConfig, useWorkers } from '@/hooks/queries'

/** Dispatcher view: who is free, what they can do, and how loaded they are. */
export function WorkersPage() {
  const { data: config } = useDomainConfig()
  const [skill, setSkill] = useState('')
  const [availableOnly, setAvailableOnly] = useState(false)

  const {
    data: workers,
    isPending,
    error,
  } = useWorkers({
    skill: skill || undefined,
    available: availableOnly ? true : undefined,
  })

  const label = config?.worker_label ?? 'Worker'

  return (
    <div className="space-y-6">
      <PageHeader
        title={`${label}s`}
        subtitle="Skills, availability and current workload across the team."
      />

      <div className="card flex flex-wrap items-end gap-3 p-4">
        <label className="text-sm">
          <span className="label">Skill</span>
          <select
            className="input w-44"
            value={skill}
            onChange={(event) => setSkill(event.target.value)}
          >
            <option value="">Any skill</option>
            {(config?.skill_vocabulary ?? []).map((value) => (
              <option key={value} value={value}>
                {skillLabel(config, value)}
              </option>
            ))}
          </select>
        </label>

        <label className="flex items-center gap-2 pb-2 text-sm text-ink">
          <input
            type="checkbox"
            className="size-4 accent-brand-600"
            checked={availableOnly}
            onChange={(event) => setAvailableOnly(event.target.checked)}
          />
          Available only
        </label>

        <p className="ml-auto text-sm text-muted">
          {workers ? `${workers.length} ${label.toLowerCase()}s` : ''}
        </p>
      </div>

      {error && <ErrorState error={error} />}

      {isPending && (
        <div className="grid gap-3 sm:grid-cols-2">
          <Skeleton className="h-28" />
          <Skeleton className="h-28" />
        </div>
      )}

      {workers?.length === 0 && (
        <EmptyState
          title={`No ${label.toLowerCase()}s match`}
          hint="Try clearing the skill filter or the availability toggle."
        />
      )}

      <div className="grid gap-3 sm:grid-cols-2">
        {workers?.map((worker) => (
          <article key={worker.id} className="card p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 className="font-medium text-ink">{worker.name}</h2>
                <p className="text-sm text-muted">{worker.email}</p>
              </div>
              <span
                className={classes(
                  'inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset',
                  worker.is_available
                    ? 'bg-emerald-50 text-emerald-700 ring-emerald-200'
                    : 'bg-zinc-100 text-zinc-600 ring-zinc-200',
                )}
              >
                <span
                  aria-hidden
                  className={classes(
                    'size-1.5 rounded-full',
                    worker.is_available ? 'bg-emerald-500' : 'bg-zinc-400',
                  )}
                />
                {worker.is_available ? 'Available' : 'Unavailable'}
              </span>
            </div>

            <div className="mt-3 flex flex-wrap items-center gap-1.5">
              {worker.skills.length > 0 ? (
                worker.skills.map((value) => (
                  <Chip key={value}>{skillLabel(config, value)}</Chip>
                ))
              ) : (
                <span className="text-xs text-muted">No skills recorded</span>
              )}
            </div>

            <p className="mt-3 border-t border-line pt-3 text-sm text-muted">
              <span className="font-medium tabular-nums text-ink">
                {worker.active_ticket_count}
              </span>{' '}
              open job{worker.active_ticket_count === 1 ? '' : 's'}
            </p>
          </article>
        ))}
      </div>
    </div>
  )
}
