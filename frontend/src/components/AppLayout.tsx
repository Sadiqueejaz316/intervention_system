import { NavLink, Outlet } from 'react-router-dom'

import { useAuth } from '@/auth/useAuth'
import { canListWorkers } from '@/auth/permissions'
import { useDomainConfig, useUnreadCount } from '@/hooks/queries'
import { classes } from '@/lib/format'
import { Button, RoleBadge } from './ui'

export function AppLayout() {
  const { user, logout } = useAuth()
  const { data: config } = useDomainConfig()
  const { data: unread } = useUnreadCount(user !== null)

  if (!user) return null

  /**
   * Sign out with a full page load rather than a route change.
   *
   * A route change lets the guard redirect first and remember this page as
   * "where they were going", so the next person to sign in on this browser lands
   * on a ticket that was never theirs. Reloading discards that history state — and
   * everything still held in memory — for a genuinely clean session.
   */
  function signOut() {
    logout()
    window.location.replace('/login')
  }

  const links = [
    { to: '/tickets', label: 'Tickets' },
    ...(user.role === 'CONTRACTOR' ? [{ to: '/my-jobs', label: 'My jobs' }] : []),
    ...(canListWorkers(user)
      ? [{ to: '/workers', label: `${config?.worker_label ?? 'Worker'}s` }]
      : []),
    { to: '/notifications', label: 'Notifications', count: unread },
  ]

  return (
    <div className="min-h-full">
      <header className="sticky top-0 z-20 border-b border-line bg-surface/85 backdrop-blur">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-6 gap-y-3 px-4 py-3">
          <NavLink to="/tickets" className="flex items-center gap-2">
            <span className="grid size-8 place-items-center rounded-lg bg-brand-600 text-sm font-bold text-white">
              IS
            </span>
            <span className="text-sm font-semibold tracking-tight text-ink">
              {config?.domain_name ?? 'Intervention System'}
            </span>
          </NavLink>

          <nav className="order-3 flex w-full gap-1 sm:order-none sm:w-auto">
            {links.map(({ to, label, count }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  classes(
                    'flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition',
                    isActive
                      ? 'bg-brand-50 text-brand-700'
                      : 'text-muted hover:bg-canvas hover:text-ink',
                  )
                }
              >
                {label}
                {count ? (
                  <span className="rounded-full bg-brand-600 px-1.5 text-[11px] font-semibold text-white">
                    {count}
                  </span>
                ) : null}
              </NavLink>
            ))}
          </nav>

          <div className="ml-auto flex items-center gap-3">
            <div className="hidden text-right sm:block">
              <p className="text-sm font-medium text-ink">{user.name}</p>
              <p className="text-xs text-muted">{user.email}</p>
            </div>
            <RoleBadge role={user.role} />
            <Button variant="ghost" onClick={signOut}>
              Sign out
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-8">
        <Outlet />
      </main>
    </div>
  )
}
