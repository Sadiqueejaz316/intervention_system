import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'

import type { UserRole } from '@/api/types'
import { hasRole } from '@/auth/permissions'
import { useAuth } from '@/auth/useAuth'
import { EmptyState, Skeleton } from './ui'

/**
 * Routing guards, not security.
 *
 * They keep people out of screens that would only 403 anyway; the API is what
 * actually refuses the data.
 */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { user, isLoading } = useAuth()
  const location = useLocation()

  if (isLoading) return <FullPageLoading />

  if (!user) {
    // The destination rides in the URL rather than in router state: signing out
    // then navigates to a plain `/login`, which cannot inherit it by accident.
    const intended = encodeURIComponent(location.pathname + location.search)

    return <Navigate to={`/login?next=${intended}`} replace />
  }

  return <>{children}</>
}

export function RequireRole({
  roles,
  children,
}: {
  roles: UserRole[]
  children: ReactNode
}) {
  const { user } = useAuth()

  if (!user) return null

  if (!hasRole(user, ...roles)) {
    return (
      <EmptyState
        title="Not available for your role"
        hint={`This screen is for ${roles.join(' and ').toLowerCase()} accounts.`}
      />
    )
  }

  return <>{children}</>
}

export function FullPageLoading() {
  return (
    <div className="mx-auto max-w-6xl space-y-4 px-4 py-10">
      <Skeleton className="h-8 w-56" />
      <Skeleton className="h-32 w-full" />
      <Skeleton className="h-32 w-full" />
    </div>
  )
}
