import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { Link } from 'react-router-dom'

import type { TicketPriority, TicketStatus, UserRole } from '@/api/types'
import { errorMessage } from '@/lib/errors'
import { classes, humanise } from '@/lib/format'

/* -------------------------------------------------------------------------- */
/* Buttons                                                                     */
/* -------------------------------------------------------------------------- */

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger'

const BUTTON_VARIANTS: Record<ButtonVariant, string> = {
  primary: 'bg-brand-600 text-white hover:bg-brand-700 disabled:hover:bg-brand-600',
  secondary: 'border border-line bg-surface text-ink hover:bg-canvas',
  ghost: 'text-muted hover:bg-canvas hover:text-ink',
  danger: 'border border-red-200 bg-white text-red-700 hover:bg-red-50',
}

const BUTTON_BASE =
  'inline-flex items-center justify-center gap-2 rounded-lg px-3.5 py-2 text-sm ' +
  'font-medium transition disabled:cursor-not-allowed disabled:opacity-60'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  loading?: boolean
}

export function Button({
  variant = 'primary',
  loading = false,
  disabled,
  className,
  children,
  ...rest
}: ButtonProps) {
  return (
    <button
      {...rest}
      disabled={disabled || loading}
      className={classes(BUTTON_BASE, BUTTON_VARIANTS[variant], className)}
    >
      {loading && <Spinner />}
      {children}
    </button>
  )
}

/** A link that looks like a button — navigation, so never a `<button>`. */
export function ButtonLink({
  to,
  variant = 'primary',
  className,
  children,
}: {
  to: string
  variant?: ButtonVariant
  className?: string
  children: ReactNode
}) {
  return (
    <Link to={to} className={classes(BUTTON_BASE, BUTTON_VARIANTS[variant], className)}>
      {children}
    </Link>
  )
}

function Spinner() {
  return (
    <span
      aria-hidden
      className="size-3.5 animate-spin rounded-full border-2 border-current border-t-transparent"
    />
  )
}

/* -------------------------------------------------------------------------- */
/* Badges                                                                      */
/* -------------------------------------------------------------------------- */

const STATUS_STYLES: Record<TicketStatus, string> = {
  OPEN: 'bg-slate-100 text-slate-700 ring-slate-200',
  ASSIGNED: 'bg-blue-50 text-blue-700 ring-blue-200',
  IN_PROGRESS: 'bg-amber-50 text-amber-800 ring-amber-200',
  RESOLVED: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
  CLOSED: 'bg-zinc-100 text-zinc-600 ring-zinc-200',
}

const PRIORITY_STYLES: Record<TicketPriority, string> = {
  LOW: 'bg-slate-100 text-slate-600 ring-slate-200',
  MEDIUM: 'bg-sky-50 text-sky-700 ring-sky-200',
  HIGH: 'bg-orange-50 text-orange-700 ring-orange-200',
  CRITICAL: 'bg-red-50 text-red-700 ring-red-200',
}

const ROLE_STYLES: Record<UserRole, string> = {
  REPORTER: 'bg-violet-50 text-violet-700 ring-violet-200',
  CONTRACTOR: 'bg-teal-50 text-teal-700 ring-teal-200',
  DISPATCHER: 'bg-indigo-50 text-indigo-700 ring-indigo-200',
  ADMIN: 'bg-rose-50 text-rose-700 ring-rose-200',
}

function Badge({ tone, children }: { tone: string; children: ReactNode }) {
  return (
    <span
      className={classes(
        'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium',
        'whitespace-nowrap ring-1 ring-inset',
        tone,
      )}
    >
      {children}
    </span>
  )
}

export function StatusBadge({ status }: { status: TicketStatus }) {
  return <Badge tone={STATUS_STYLES[status]}>{humanise(status)}</Badge>
}

export function PriorityBadge({ priority }: { priority: TicketPriority }) {
  return <Badge tone={PRIORITY_STYLES[priority]}>{humanise(priority)}</Badge>
}

export function RoleBadge({ role }: { role: UserRole }) {
  return <Badge tone={ROLE_STYLES[role]}>{humanise(role)}</Badge>
}

export function Chip({ children }: { children: ReactNode }) {
  return (
    <span className="rounded-md bg-canvas px-2 py-0.5 text-xs font-medium text-muted ring-1 ring-inset ring-line">
      {children}
    </span>
  )
}

/* -------------------------------------------------------------------------- */
/* Feedback                                                                    */
/* -------------------------------------------------------------------------- */

export function Alert({
  tone = 'error',
  children,
}: {
  tone?: 'error' | 'info' | 'success'
  children: ReactNode
}) {
  const tones = {
    error: 'border-red-200 bg-red-50 text-red-800',
    info: 'border-brand-100 bg-brand-50 text-brand-700',
    success: 'border-emerald-200 bg-emerald-50 text-emerald-800',
  }

  return (
    <div
      role={tone === 'error' ? 'alert' : 'status'}
      className={classes('rounded-lg border px-3 py-2 text-sm', tones[tone])}
    >
      {children}
    </div>
  )
}

export function ErrorState({ error }: { error: unknown }) {
  return <Alert>{errorMessage(error)}</Alert>
}

export function EmptyState({
  title,
  hint,
  action,
}: {
  title: string
  hint?: string
  action?: ReactNode
}) {
  return (
    <div className="card flex flex-col items-center gap-2 px-6 py-12 text-center">
      <p className="font-medium text-ink">{title}</p>
      {hint && <p className="max-w-sm text-sm text-muted">{hint}</p>}
      {action}
    </div>
  )
}

export function Skeleton({ className }: { className?: string }) {
  return (
    <div aria-hidden className={classes('animate-pulse rounded-lg bg-line/60', className)} />
  )
}

export function PageHeader({
  title,
  subtitle,
  action,
}: {
  title: string
  subtitle?: string
  action?: ReactNode
}) {
  return (
    <header className="flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-ink">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-muted">{subtitle}</p>}
      </div>
      {action}
    </header>
  )
}
