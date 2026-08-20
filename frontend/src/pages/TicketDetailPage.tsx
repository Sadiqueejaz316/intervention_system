import { useState, type ReactNode } from 'react'
import { useParams } from 'react-router-dom'

import { ApiError } from '@/api/client'
import type { TicketStatus } from '@/api/types'
import {
  canAccept,
  canAssign,
  canChangeStatusTo,
  canSeeRecommendations,
  nextStatuses,
} from '@/auth/permissions'
import { useAuth } from '@/auth/useAuth'
import { AssignPanel } from '@/components/AssignPanel'
import { TicketTimeline } from '@/components/TicketTimeline'
import {
  Alert,
  Button,
  ButtonLink,
  Chip,
  EmptyState,
  PageHeader,
  PriorityBadge,
  Skeleton,
  StatusBadge,
} from '@/components/ui'
import { errorMessage } from '@/lib/errors'
import { formatDateTime, humanise } from '@/lib/format'
import { isEmergency, issueTypeLabel, metaText, skillLabel } from '@/lib/domain'
import {
  useAcceptAssignment,
  useChangeStatus,
  useDomainConfig,
  useTicket,
  useTicketHistory,
} from '@/hooks/queries'

/** What the button should say, rather than "Set status to IN_PROGRESS". */
const ACTION_LABELS: Record<string, string> = {
  IN_PROGRESS: 'Start work',
  RESOLVED: 'Mark resolved',
  CLOSED: 'Close ticket',
}

export function TicketDetailPage() {
  const { ticketId = '' } = useParams()
  const { user } = useAuth()
  const { data: config } = useDomainConfig()

  const { data: ticket, isPending, error } = useTicket(ticketId)
  const { data: history, isPending: historyPending } = useTicketHistory(
    ticketId,
    !error,
  )

  const changeStatus = useChangeStatus(ticketId)
  const accept = useAcceptAssignment(ticketId)

  const [comment, setComment] = useState('')

  if (isPending) return <DetailSkeleton />

  if (error) {
    const denied = error instanceof ApiError && error.isForbidden

    return (
      <div className="space-y-4">
        <ButtonLink to="/tickets" variant="secondary">
          Back to tickets
        </ButtonLink>
        <EmptyState
          title={denied ? 'This ticket is not yours to view' : 'Ticket not found'}
          hint={
            denied
              ? 'You can only open tickets you reported or are assigned to.'
              : errorMessage(error)
          }
        />
      </div>
    )
  }

  if (!ticket || !user) return null

  const emergency = isEmergency(ticket)
  const moves = nextStatuses(ticket, config?.status_transitions).filter((status) =>
    canChangeStatusTo(user, ticket, status),
  )
  const showAssign = canAssign(user) && canSeeRecommendations(user)
  const assignable = ticket.status === 'OPEN' || ticket.status === 'ASSIGNED'
  const acceptable = canAccept(user, ticket)
  const mutationError = changeStatus.error ?? accept.error

  function move(status: TicketStatus) {
    changeStatus.mutate({ status, comment }, { onSuccess: () => setComment('') })
  }

  return (
    <div className="space-y-6">
      <div>
        <ButtonLink to="/tickets" variant="ghost" className="-ml-3.5 mb-2">
          ← Back to tickets
        </ButtonLink>
        <PageHeader
          title={emergency ? `🚨 ${ticket.title}` : ticket.title}
          subtitle={`Reported ${formatDateTime(ticket.created_at)}`}
          action={
            <div className="flex flex-wrap gap-1.5">
              {emergency && (
                <span className="inline-flex items-center rounded-full bg-red-100 px-2 py-0.5 text-xs font-semibold text-red-800 ring-1 ring-inset ring-red-200">
                  Person trapped
                </span>
              )}
              <PriorityBadge priority={ticket.priority} />
              <StatusBadge status={ticket.status} />
            </div>
          }
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-[2fr_1fr]">
        <div className="space-y-6">
          <section className="card space-y-4 p-5">
            {ticket.description ? (
              <p className="whitespace-pre-line text-sm text-ink">
                {ticket.description}
              </p>
            ) : (
              <p className="text-sm text-muted">No further details were given.</p>
            )}

            <dl className="grid gap-3 border-t border-line pt-4 text-sm sm:grid-cols-2">
              <Detail label="Type">
                <Chip>{issueTypeLabel(config, ticket.type)}</Chip>
              </Detail>
              <Detail label="Building">
                {metaText(ticket, 'building_name') ?? (
                  <span className="text-muted">Not given</span>
                )}
              </Detail>
              <Detail label="Elevator">
                {metaText(ticket, 'elevator_id') ?? (
                  <span className="text-muted">Not given</span>
                )}
              </Detail>
              <Detail label="Known floor">
                {metaText(ticket, 'floor') ?? <span className="text-muted">Unknown</span>}
              </Detail>
              {emergency && (
                <Detail label="People trapped">
                  {metaText(ticket, 'people_trapped') ?? '—'}
                </Detail>
              )}
              {emergency && (
                <Detail label="Communication">
                  {metaText(ticket, 'communication_possible') ?? 'Unknown'}
                </Detail>
              )}
              <Detail label={config?.worker_label ?? 'Assigned to'}>
                {ticket.assigned_worker ? (
                  <span>
                    {ticket.assigned_worker.name}
                    {ticket.assigned_worker.skills.length > 0 && (
                      <span className="text-muted">
                        {' '}
                        · {ticket.assigned_worker.skills.map((skill) => skillLabel(config, skill)).join(', ')}
                      </span>
                    )}
                  </span>
                ) : (
                  <span className="text-muted">Nobody yet</span>
                )}
              </Detail>
              <Detail label="Last update">{formatDateTime(ticket.updated_at)}</Detail>
            </dl>
          </section>

          {(moves.length > 0 || acceptable) && (
            <section className="card space-y-4 p-5">
              <div>
                <h2 className="font-medium text-ink">Next step</h2>
                <p className="mt-0.5 text-sm text-muted">
                  You are recorded as whoever the token says you are — the timeline
                  will show your name.
                </p>
              </div>

              {mutationError && <Alert>{errorMessage(mutationError)}</Alert>}

              {moves.length > 0 && (
                <div>
                  <label className="label" htmlFor="comment">
                    Comment <span className="font-normal text-muted">(optional)</span>
                  </label>
                  <input
                    id="comment"
                    className="input"
                    maxLength={2000}
                    value={comment}
                    onChange={(event) => setComment(event.target.value)}
                    placeholder="On site, isolating the cabin"
                  />
                </div>
              )}

              <div className="flex flex-wrap gap-2">
                {acceptable && (
                  <Button
                    onClick={() => accept.mutate(undefined)}
                    loading={accept.isPending}
                  >
                    Accept this job
                  </Button>
                )}
                {moves.map((status) => (
                  <Button
                    key={status}
                    variant={acceptable ? 'secondary' : 'primary'}
                    onClick={() => move(status)}
                    loading={changeStatus.isPending}
                  >
                    {ACTION_LABELS[status] ?? `Move to ${humanise(status)}`}
                  </Button>
                ))}
              </div>
            </section>
          )}

          {showAssign && assignable && <AssignPanel ticket={ticket} />}
        </div>

        <section className="card h-fit p-5">
          <h2 className="mb-4 font-medium text-ink">Timeline</h2>
          <TicketTimeline entries={history} isPending={historyPending} />
        </section>
      </div>
    </div>
  )
}

function Detail({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase tracking-wide text-muted">
        {label}
      </dt>
      <dd className="mt-1 text-ink">{children}</dd>
    </div>
  )
}

function DetailSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-9 w-2/3" />
      <div className="grid gap-6 lg:grid-cols-[2fr_1fr]">
        <Skeleton className="h-64 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    </div>
  )
}
