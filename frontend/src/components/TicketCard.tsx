import { Link } from 'react-router-dom'

import type { Ticket } from '@/api/types'
import { formatRelative, humanise } from '@/lib/format'
import { Chip, PriorityBadge, StatusBadge } from './ui'

export function TicketCard({ ticket }: { ticket: Ticket }) {
  return (
    <Link
      to={`/tickets/${ticket.id}`}
      className="card block p-4 transition hover:border-brand-500/60 hover:shadow-md"
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <h2 className="font-medium text-ink">{ticket.title}</h2>
        <div className="flex shrink-0 gap-1.5">
          <PriorityBadge priority={ticket.priority} />
          <StatusBadge status={ticket.status} />
        </div>
      </div>

      {ticket.description && (
        <p className="mt-1.5 line-clamp-2 text-sm text-muted">{ticket.description}</p>
      )}

      <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-muted">
        <Chip>{humanise(ticket.type)}</Chip>
        {ticket.location_text && <span>· {ticket.location_text}</span>}
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
