import { useState } from 'react'

import { TicketCard, TicketCardSkeleton } from '@/components/TicketCard'
import { Button, EmptyState, ErrorState, PageHeader } from '@/components/ui'
import { classes } from '@/lib/format'
import { useMyTickets } from '@/hooks/queries'

/**
 * The contractor's own queue.
 *
 * It asks `/workers/me/tickets`, so no worker id is ever put in a URL and one
 * contractor cannot go fishing for another's jobs by editing the address bar.
 */
export function MyJobsPage() {
  const [activeOnly, setActiveOnly] = useState(true)
  const { data: tickets, isPending, error } = useMyTickets(activeOnly)

  return (
    <div className="space-y-6">
      <PageHeader
        title="My elevator jobs"
        subtitle="Jobs assigned to you, emergencies first."
        action={
          <div className="flex rounded-lg border border-line bg-surface p-0.5">
            {[
              { label: 'Active', value: true },
              { label: 'All', value: false },
            ].map((option) => (
              <button
                key={option.label}
                type="button"
                onClick={() => setActiveOnly(option.value)}
                className={classes(
                  'rounded-md px-3 py-1.5 text-sm font-medium transition',
                  activeOnly === option.value
                    ? 'bg-brand-50 text-brand-700'
                    : 'text-muted hover:text-ink',
                )}
              >
                {option.label}
              </button>
            ))}
          </div>
        }
      />

      {error && <ErrorState error={error} />}

      {isPending && (
        <div className="space-y-3">
          <TicketCardSkeleton />
          <TicketCardSkeleton />
        </div>
      )}

      {tickets?.length === 0 && (
        <EmptyState
          title={activeOnly ? 'No active jobs' : 'No jobs yet'}
          hint={
            activeOnly
              ? 'Finished work stays visible under “All”.'
              : 'A dispatcher will assign work to you here.'
          }
          action={
            activeOnly && (
              <Button
                variant="secondary"
                className="mt-2"
                onClick={() => setActiveOnly(false)}
              >
                Show everything
              </Button>
            )
          }
        />
      )}

      <div className="space-y-3">
        {tickets?.map((ticket) => (
          <TicketCard key={ticket.id} ticket={ticket} />
        ))}
      </div>
    </div>
  )
}
