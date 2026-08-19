import { useState } from 'react'
import { Link } from 'react-router-dom'

import type { NotificationType } from '@/api/types'
import {
  Button,
  EmptyState,
  ErrorState,
  PageHeader,
  Skeleton,
} from '@/components/ui'
import { classes, formatRelative } from '@/lib/format'
import { useMarkNotificationRead, useNotifications } from '@/hooks/queries'

const TYPE_TONES: Record<NotificationType, string> = {
  INFO: 'bg-slate-400',
  ASSIGNMENT: 'bg-blue-500',
  STATUS_CHANGE: 'bg-amber-500',
  ESCALATION: 'bg-red-500',
}

/** Always the caller's own inbox: the API takes the recipient from the token. */
export function NotificationsPage() {
  const [unreadOnly, setUnreadOnly] = useState(false)
  const { data: notifications, isPending, error } = useNotifications(unreadOnly)
  const markRead = useMarkNotificationRead()

  const unread = notifications?.filter((notification) => !notification.is_read) ?? []

  return (
    <div className="space-y-6">
      <PageHeader
        title="Notifications"
        subtitle="Everything that happened on tickets you are involved in."
        action={
          <div className="flex items-center gap-2">
            <label className="flex items-center gap-2 text-sm text-ink">
              <input
                type="checkbox"
                className="size-4 accent-brand-600"
                checked={unreadOnly}
                onChange={(event) => setUnreadOnly(event.target.checked)}
              />
              Unread only
            </label>
            {unread.length > 0 && (
              <Button
                variant="secondary"
                loading={markRead.isPending}
                onClick={() => {
                  for (const notification of unread) markRead.mutate(notification.id)
                }}
              >
                Mark all read
              </Button>
            )}
          </div>
        }
      />

      {error && <ErrorState error={error} />}

      {isPending && (
        <div className="space-y-2">
          <Skeleton className="h-20" />
          <Skeleton className="h-20" />
        </div>
      )}

      {notifications?.length === 0 && (
        <EmptyState
          title={unreadOnly ? 'Nothing unread' : 'No notifications yet'}
          hint="You are told when a ticket you reported or hold changes hands or status."
        />
      )}

      <ul className="space-y-2">
        {notifications?.map((notification) => (
          <li
            key={notification.id}
            className={classes(
              'card flex gap-3 p-4 transition',
              !notification.is_read && 'border-brand-500/40 bg-brand-50/40',
            )}
          >
            <span
              aria-hidden
              className={classes(
                'mt-1.5 size-2 shrink-0 rounded-full',
                TYPE_TONES[notification.type],
              )}
            />

            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-baseline gap-x-2">
                <h2 className="font-medium text-ink">{notification.title}</h2>
                <time className="text-xs text-muted">
                  {formatRelative(notification.created_at)}
                </time>
              </div>
              <p className="mt-0.5 text-sm text-muted">{notification.message}</p>

              {notification.ticket_id && (
                <Link
                  to={`/tickets/${notification.ticket_id}`}
                  className="mt-1.5 inline-block text-sm font-medium text-brand-600 hover:underline"
                >
                  Open ticket
                </Link>
              )}
            </div>

            {!notification.is_read && (
              <Button
                variant="ghost"
                onClick={() => markRead.mutate(notification.id)}
                className="self-start"
              >
                Mark read
              </Button>
            )}
          </li>
        ))}
      </ul>
    </div>
  )
}
