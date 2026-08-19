/**
 * What each role is allowed to see, mirrored from the backend.
 *
 * This decides what to *render*, nothing more. The API enforces the same rules and
 * is the only thing that actually protects the data: hiding a button here is a
 * courtesy to the user, not a security boundary.
 */

import type { Ticket, TicketStatus, User, UserRole } from '@/api/types'

export function isStaff(user: Pick<User, 'role'>): boolean {
  return user.role === 'DISPATCHER' || user.role === 'ADMIN'
}

export function isAdmin(user: Pick<User, 'role'>): boolean {
  return user.role === 'ADMIN'
}

export function hasRole(user: Pick<User, 'role'>, ...roles: UserRole[]): boolean {
  return user.role === 'ADMIN' || roles.includes(user.role)
}

export function canAssign(user: Pick<User, 'role'>): boolean {
  return isStaff(user)
}

export function canSeeRecommendations(user: Pick<User, 'role'>): boolean {
  return isStaff(user)
}

export function canListWorkers(user: Pick<User, 'role'>): boolean {
  return isStaff(user)
}

/** The contractor currently holding the job — the only one who may work on it. */
export function holdsAssignment(user: Pick<User, 'id'>, ticket: Ticket): boolean {
  return ticket.assigned_worker?.id === user.id
}

export function canAccept(user: User, ticket: Ticket): boolean {
  return (
    user.role === 'CONTRACTOR' &&
    holdsAssignment(user, ticket) &&
    ticket.status === 'ASSIGNED'
  )
}

/** Mirrors `ensure_can_change_status`: who may attempt a move to `target`. */
export function canChangeStatusTo(
  user: User,
  ticket: Ticket,
  target: TicketStatus,
): boolean {
  if (isAdmin(user)) return true

  if (target === 'IN_PROGRESS' || target === 'RESOLVED') {
    return holdsAssignment(user, ticket)
  }

  return isStaff(user)
}

/**
 * Moves offered for a ticket in its current status.
 *
 * `ASSIGNED` is deliberately absent: it only ever comes from the assign endpoint,
 * so that an assignment record always exists.
 */
export function nextStatuses(
  ticket: Ticket,
  transitions: Record<string, string[]> | undefined,
): TicketStatus[] {
  const allowed = transitions?.[ticket.status] ?? []

  return allowed.filter((status) => status !== 'ASSIGNED') as TicketStatus[]
}
