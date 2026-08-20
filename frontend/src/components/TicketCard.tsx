import { Link } from 'react-router-dom'

import type { Ticket } from '@/api/types'
import { buildingLine, isEmergency, issueTypeLabel, metaText } from '@/lib/domain'
import { formatRelative } from '@/lib/format'
import { useDomainConfig } from '@/hooks/queries'
import { Chip, PriorityBadge, StatusBadge } from './ui'

export function TicketCard({ ticket }: { ticket: Ticket }) {
  const { data: config } = useDomainConfig()
  const emergency = isEmergency(ticket)
  const people = metaText(ticket, 'people_trapped')
  const elevator = metaText(ticket, 'elevator_id')
  const floor = metaText(ticket, 'floor')
  const where = buildingLine(ticket)

  return (
    <Link
      to={`/tickets/${ticket.id}`}
      className={
        emergency
          ? 'card block border-red-300 bg-red-50/70 p-4 transition hover:border-red-500 hover:shadow-md'
          : 'card block p-4 transition hover:border-brand-500/60 hover:shadow-md'
      }
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          {emergency && (
            <p className="mb-1 text-xs font-semibold tracking-wide text-red-800 uppercase">
              🚨 Person trapped
            </p>
          )}
          <h2 className="font-medium text-ink">{ticket.title}</h2>
        </div>
        <div className="flex shrink-0 gap-1.5">
          <PriorityBadge priority={ticket.priority} />
          <StatusBadge status={ticket.status} />
        </div>
      </div>

      <p className="mt-2 text-sm text-ink">
        {[where, elevator && `Elevator ${elevator}`, floor && `Floor ${floor}`, people && `${people} people`]
          .filter(Boolean)
          .join(' · ')}
      </p>

      {ticket.description && !emergency && (
        <p className="mt-1.5 line-clamp-2 text-sm text-muted">{ticket.description}</p>
      )}

      <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-muted">
        <Chip>{issueTypeLabel(config, ticket.type)}</Chip>
        <span className="ml-auto">
          {ticket.assigned_worker
            ? `Assigned to ${ticket.assigned_worker.name}`
            : 'Unassigned'}
          {' · '}
          {formatRelative(ticket.created_at)}
        </span>
      </div>
    </Link>
  )
}

export function TicketCardSkeleton() {
  return <div className="card h-28 animate-pulse bg-line/20" />
}