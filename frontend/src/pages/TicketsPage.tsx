import { useState, type ReactNode } from 'react'

import type { TicketPriority, TicketStatus } from '@/api/types'
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
import { humanise } from '@/lib/format'
import { useDomainConfig, useTickets } from '@/hooks/queries'

/** What "all tickets" means depends on who is asking; the API scopes the queue. */
const SCOPE_HINT: Record<string, string> = {
  REPORTER: 'Issues you have reported.',
  CONTRACTOR: 'Jobs currently assigned to you.',
  DISPATCHER: 'Every ticket, most urgent first.',
  ADMIN: 'Every ticket, most urgent first.',
}

export function TicketsPage() {
  const { user } = useAuth()
  const { data: config } = useDomainConfig()

  const [status, setStatus] = useState<TicketStatus | ''>('')
  const [priority, setPriority] = useState<TicketPriority | ''>('')
  const [type, setType] = useState('')

  const query = { status, priority, type, limit: 100 }
  const { data: tickets, isPending, error } = useTickets(query)

  if (!user) return null

  const hasFilters = status !== '' || priority !== '' || type !== ''

  return (
    <div className="space-y-6">
      <PageHeader
        title="Tickets"
        subtitle={SCOPE_HINT[user.role]}
        action={<ButtonLink to="/tickets/new">Report an issue</ButtonLink>}
      />

      <div className="card flex flex-wrap items-end gap-3 p-4">
        <Filter label="Status" value={status} onChange={(value) => setStatus(value as TicketStatus | '')}>
          <option value="">Any status</option>
          {(config?.statuses ?? []).map((value) => (
            <option key={value} value={value}>
              {humanise(value)}
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
              {humanise(value)}
            </option>
          ))}
        </Filter>

        <Filter label="Type" value={type} onChange={setType}>
          <option value="">Any type</option>
          {(config?.issue_types ?? []).map((value) => (
            <option key={value} value={value}>
              {humanise(value)}
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
          {tickets ? `${tickets.length} ticket${tickets.length === 1 ? '' : 's'}` : ''}
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
          title={hasFilters ? 'No tickets match these filters' : 'Nothing here yet'}
          hint={
            hasFilters
              ? 'Try clearing the filters to see the full queue.'
              : isStaff(user)
                ? 'Tickets reported by anyone will show up here.'
                : 'Report an issue and it will appear in the queue.'
          }
          action={
            !hasFilters && (
              <ButtonLink to="/tickets/new" className="mt-2">
                Report an issue
              </ButtonLink>
            )
          }
        />
      )}

      {tickets && tickets.length > 0 && (
        <div className="space-y-3">
          {tickets.map((ticket) => (
            <TicketCard key={ticket.id} ticket={ticket} />
          ))}
        </div>
      )}
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
        className="input w-40"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        {children}
      </select>
    </label>
  )
}
