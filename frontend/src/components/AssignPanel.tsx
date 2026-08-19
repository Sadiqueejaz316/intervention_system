import { useState } from 'react'

import { ApiError } from '@/api/client'
import type { Ticket } from '@/api/types'
import { Alert, Button, Chip, Skeleton } from '@/components/ui'
import { errorMessage } from '@/lib/errors'
import { classes, humanise } from '@/lib/format'
import { useAssignTicket, useDomainConfig, useRecommendations } from '@/hooks/queries'

/**
 * Dispatcher-only panel: ranked suggestions, plus the freedom to ignore them.
 *
 * The score is advice. A skill mismatch is shown as a warning and never disables
 * the button, because the dispatcher on the ground knows things the ranking does
 * not — the backend agrees and accepts the assignment either way.
 */
export function AssignPanel({ ticket }: { ticket: Ticket }) {
  const { data: config } = useDomainConfig()
  const {
    data: recommendations,
    isPending,
    error: recommendationError,
  } = useRecommendations(ticket.id, true)
  const assign = useAssignTicket(ticket.id)

  const [selected, setSelected] = useState<string | null>(null)
  const [notes, setNotes] = useState('')

  const workerLabel = config?.worker_label ?? 'worker'
  const requiredSkills = config?.required_skills_by_type[ticket.type] ?? []
  const isReassignment = ticket.assigned_worker !== null

  function submit() {
    if (!selected) return
    assign.mutate(
      { contractorId: selected, notes },
      {
        onSuccess: () => {
          setSelected(null)
          setNotes('')
        },
      },
    )
  }

  return (
    <section className="card p-5">
      <header className="mb-4">
        <h2 className="font-medium text-ink">
          {isReassignment ? `Reassign this job` : `Assign this job`}
        </h2>
        <p className="mt-0.5 text-sm text-muted">
          Ranked by skill match, availability, distance and current workload.
          {requiredSkills.length > 0 && (
            <> Usually needs {requiredSkills.map(humanise).join(', ')}.</>
          )}
        </p>
      </header>

      {recommendationError && <Alert>{errorMessage(recommendationError)}</Alert>}

      {isPending && (
        <div className="space-y-2">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
        </div>
      )}

      {recommendations?.length === 0 && (
        <p className="text-sm text-muted">
          No {workerLabel.toLowerCase()}s are registered yet.
        </p>
      )}

      <ul className="space-y-2">
        {recommendations?.map((recommendation) => {
          const isCurrent = ticket.assigned_worker?.id === recommendation.worker_id
          const isSelected = selected === recommendation.worker_id
          const mismatch = recommendation.reasons.some((reason) =>
            reason.toLowerCase().includes('missing'),
          )

          return (
            <li key={recommendation.worker_id}>
              <button
                type="button"
                disabled={isCurrent}
                onClick={() => setSelected(isSelected ? null : recommendation.worker_id)}
                aria-pressed={isSelected}
                className={classes(
                  'w-full rounded-lg border p-3 text-left transition',
                  isCurrent && 'cursor-not-allowed border-line bg-canvas opacity-70',
                  !isCurrent && isSelected
                    ? 'border-brand-500 bg-brand-50'
                    : !isCurrent && 'border-line hover:bg-canvas',
                )}
              >
                <div className="flex items-center justify-between gap-3">
                  <span className="font-medium text-ink">{recommendation.name}</span>
                  <span className="flex items-center gap-2">
                    {isCurrent && <Chip>On the job</Chip>}
                    {mismatch && (
                      <span className="rounded-md bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-800 ring-1 ring-inset ring-amber-200">
                        Skill mismatch
                      </span>
                    )}
                    <span className="text-sm font-semibold tabular-nums text-brand-700">
                      {recommendation.score}
                    </span>
                  </span>
                </div>
                <p className="mt-1 text-xs text-muted">
                  {recommendation.reasons.join(' · ')}
                </p>
              </button>
            </li>
          )
        })}
      </ul>

      {selected && (
        <div className="mt-4 space-y-3 border-t border-line pt-4">
          <div>
            <label className="label" htmlFor="assign-notes">
              Notes for the {workerLabel.toLowerCase()}{' '}
              <span className="font-normal text-muted">(optional)</span>
            </label>
            <input
              id="assign-notes"
              className="input"
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
              placeholder="Night shift; access code 4432"
            />
          </div>

          {assign.isError && (
            <Alert>
              {assign.error instanceof ApiError && assign.error.isConflict
                ? assign.error.message
                : errorMessage(assign.error)}
            </Alert>
          )}

          <Button onClick={submit} loading={assign.isPending}>
            {isReassignment ? 'Reassign' : 'Assign'}
          </Button>
          {isReassignment && (
            <p className="text-xs text-muted">
              Reassigning keeps the original dispatch in the timeline; it is never
              overwritten.
            </p>
          )}
        </div>
      )}
    </section>
  )
}
