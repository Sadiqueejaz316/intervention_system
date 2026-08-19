import type { TicketHistoryEntry } from '@/api/types'
import { formatDateTime, humanise } from '@/lib/format'
import { Skeleton } from './ui'

const ACTION_TONES: Record<string, string> = {
  TICKET_CREATED: 'bg-slate-400',
  ASSIGNED: 'bg-blue-500',
  ASSIGNMENT_ACCEPTED: 'bg-teal-500',
  WORK_STARTED: 'bg-amber-500',
  RESOLVED: 'bg-emerald-500',
  CLOSED: 'bg-zinc-500',
}

export function TicketTimeline({
  entries,
  isPending,
}: {
  entries: TicketHistoryEntry[] | undefined
  isPending: boolean
}) {
  if (isPending) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-5 w-3/4" />
        <Skeleton className="h-5 w-2/3" />
        <Skeleton className="h-5 w-1/2" />
      </div>
    )
  }

  if (!entries?.length) {
    return <p className="text-sm text-muted">Nothing has happened yet.</p>
  }

  return (
    <ol className="relative space-y-5 border-l border-line pl-5">
      {entries.map((entry) => (
        <li key={entry.id} className="relative">
          <span
            aria-hidden
            className={`absolute -left-[1.6rem] top-1.5 size-2.5 rounded-full ring-4 ring-surface ${
              ACTION_TONES[entry.action] ?? 'bg-slate-300'
            }`}
          />
          <p className="text-sm font-medium text-ink">{humanise(entry.action)}</p>
          {entry.old_status && entry.new_status && (
            <p className="text-xs text-muted">
              {humanise(entry.old_status)} → {humanise(entry.new_status)}
            </p>
          )}
          {entry.comment && (
            <p className="mt-1 text-sm text-muted">“{entry.comment}”</p>
          )}
          <time className="mt-0.5 block text-xs text-muted/80">
            {formatDateTime(entry.created_at)}
          </time>
        </li>
      ))}
    </ol>
  )
}
