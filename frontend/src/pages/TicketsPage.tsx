import { useState, type ReactNode } from 'react'

import type { TicketPriority, TicketStats, TicketStatus } from '@/api/types'
import { isStaff } from '@/auth/permissions'
import { useAuth } from '@/auth/useAuth'
import { TicketCard, TicketCardSkeleton } from '@/components/TicketCard'
import {
  Button,
  ButtonLink,
  EmptyState,
  ErrorState,
  PageHeader,
} from '@/components/ui'
import { isEmergency } from '@/lib/domain'
import { useDomainConfig, useTicketStats, useTickets } from '@/hooks/queries'

const SCOPE_HINT: Record<string, string> = {
  REPORTER: 'Incidents you have reported across the co-op.',
  CONTRACTOR: 'Elevator jobs currently assigned to you.',
  DISPATCHER: 'Every incident, trapped-person emergencies first.',
  ADMIN: 'Every incident, trapped-person emergencies first.',
}

export function TicketsPage() {
  const { user } = useAuth()
  const { data: config } = useDomainConfig()

  const [status, setStatus] = useState<TicketStatus | ''>('')
  const [priority, setPriority] = useState<TicketPriority | ''>('')
  const [type, setType] = useState('')

  const query = { status, priority, type, limit: 100 }
  const { data: tickets, isPending, error } = useTickets(query)
  const { data: stats } = useTicketStats(Boolean(user && isStaff(user)))

  if (!user) return null

  const hasFilters = status !== '' || priority !== '' || type !== ''
  const emergencies = tickets?.filter(isEmergency) ?? []
  const rest = tickets?.filter((ticket) => !isEmergency(ticket)) ?? []

  return (
    <div className="space-y-6">
      <PageHeader
        title={isStaff(user) ? 'Elevator operations' : 'Incidents'}
        subtitle={SCOPE_HINT[user.role]}
        action={<ButtonLink to="/tickets/new">Report an incident</ButtonLink>}
      />

      {isStaff(user) && stats && <OperationsStrip stats={stats} />}

      <div className="card flex flex-wrap items-end gap-3 p-4">
        <Filter label="Status" value={status} onChange={(value) => setStatus(value as TicketStatus | '')}>
          <option value="">Any status</option>
          {(config?.statuses ?? []).map((value) => (
            <option key={value} value={value}>
              {value.replaceAll('_', ' ')}
            </option>
          ))}
        </Filter>

        <Filter
          label="Priority"
          value={priority}
          onChange={(value) => setPriority(value as TicketPriority | '')}
        >
          <option value="">Any priority</option>
          {(config?.priorities ?? []).map((value) => (
            <option key={value} value={value}>
              {value}
            </option>
          ))}
        </Filter>

        <Filter label="Type" value={type} onChange={setType}>
          <option value="">Any type</option>
          {(config?.issue_types ?? []).map((issue) => (
            <option key={issue.value} value={issue.value}>
              {issue.label}
            </option>
          ))}
        </Filter>

        {hasFilters && (
          <Button
            variant="ghost"
            onClick={() => {
              setStatus('')
              setPriority('')
              setType('')
            }}
          >
            Clear
          </Button>
        )}

        <p className="ml-auto text-sm text-muted">
          {tickets ? `${tickets.length} incident${tickets.length === 1 ? '' : 's'}` : ''}
        </p>
      </div>

      {error && <ErrorState error={error} />}

      {isPending && (
        <div className="space-y-3">
          <TicketCardSkeleton />
          <TicketCardSkeleton />
          <TicketCardSkeleton />
        </div>
      )}

      {tickets && tickets.length === 0 && (
        <EmptyState
          title={hasFilters ? 'No incidents match these filters' : 'No elevator incidents yet'}
          hint={
            hasFilters
              ? 'Try clearing the filters to see the full queue.'
              : isStaff(user)
                ? 'Trapped-person reports appear at the top of this queue.'
                : 'Report an elevator incident and it will appear here.'
          }
          action={
            !hasFilters && (
              <ButtonLink to="/tickets/new" className="mt-2">
                Report an incident
              </ButtonLink>
            )
          }
        />
      )}

      {emergencies.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-sm font-semibold tracking-wide text-red-800 uppercase">
            Emergency queue
          </h2>
          {emergencies.map((ticket) => (
            <TicketCard key={ticket.id} ticket={ticket} />
          ))}
        </section>
      )}

      {rest.length > 0 && (
        <section className="space-y-3">
          {emergencies.length > 0 && (
            <h2 className="text-sm font-semibold tracking-wide text-muted uppercase">
              Other incidents
            </h2>
          )}
          {rest.map((ticket) => (
            <TicketCard key={ticket.id} ticket={ticket} />
          ))}
        </section>
      )}
    </div>
  )
}

function OperationsStrip({ stats }: { stats: TicketStats }) {
  const items: { label: string; value: number; emergency?: boolean }[] = [
    { label: 'Emergencies', value: stats.emergency, emergency: true },
    { label: 'Open', value: stats.open },
    { label: 'Assigned', value: stats.assigned },
    { label: 'In progress', value: stats.in_progress },
    { label: 'Resolved', value: stats.resolved },
    { label: 'Closed', value: stats.closed },
  ]

  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
      {items.map((item) => (
        <div
          key={item.label}
          className={
            item.emergency
              ? 'card border-red-200 bg-red-50 px-3 py-3'
              : 'card px-3 py-3'
          }
        >
          <p className="text-xs font-medium uppercase tracking-wide text-muted">
            {item.emergency ? '🚨 Emergencies' : item.label}
          </p>
          <p
            className={
              item.emergency
                ? 'mt-1 text-2xl font-semibold tabular-nums text-red-800'
                : 'mt-1 text-2xl font-semibold tabular-nums text-ink'
            }
          >
            {item.value}
          </p>
        </div>
      ))}
    </div>
  )
}

function Filter({
  label,
  value,
  onChange,
  children,
}: {
  label: string
  value: string
  onChange: (value: string) => void
  children: ReactNode
}) {
  return (
    <label className="text-sm">
      <span className="label">{label}</span>
      <select
        className="input w-44"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        {children}
      </select>
    </label>
  )
}