import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseMutationOptions,
} from '@tanstack/react-query'

import { domain, notifications, tickets, workers } from '@/api/endpoints'
import type {
  TicketCreateInput,
  TicketQuery,
  TicketStatus,
} from '@/api/types'

export const keys = {
  domainConfig: ['domain', 'config'] as const,
  tickets: (query: TicketQuery) => ['tickets', query] as const,
  ticket: (id: string) => ['ticket', id] as const,
  history: (id: string) => ['ticket', id, 'history'] as const,
  recommendations: (id: string) => ['ticket', id, 'recommendations'] as const,
  workers: (query: object) => ['workers', query] as const,
  myTickets: (activeOnly: boolean) => ['workers', 'me', 'tickets', activeOnly] as const,
  notifications: (unreadOnly: boolean) => ['notifications', unreadOnly] as const,
  unreadCount: ['notifications', 'unread-count'] as const,
  stats: ['tickets', 'stats'] as const,
}

/** The domain adapter decides terminology and issue types; it changes rarely. */
export function useDomainConfig() {
  return useQuery({
    queryKey: keys.domainConfig,
    queryFn: domain.config,
    staleTime: Infinity,
  })
}

export function useTickets(query: TicketQuery) {
  return useQuery({
    queryKey: keys.tickets(query),
    queryFn: () => tickets.list(query),
  })
}

export function useTicketStats(enabled: boolean) {
  return useQuery({
    queryKey: keys.stats,
    queryFn: tickets.stats,
    enabled,
  })
}

export function useTicket(id: string) {
  return useQuery({
    queryKey: keys.ticket(id),
    queryFn: () => tickets.get(id),
  })
}

export function useTicketHistory(id: string, enabled = true) {
  return useQuery({
    queryKey: keys.history(id),
    queryFn: () => tickets.history(id),
    enabled,
  })
}

export function useRecommendations(id: string, enabled: boolean) {
  return useQuery({
    queryKey: keys.recommendations(id),
    queryFn: () => tickets.recommendations(id, 10),
    enabled,
  })
}

export function useWorkers(query: { available?: boolean; skill?: string } = {}) {
  return useQuery({
    queryKey: keys.workers(query),
    queryFn: () => workers.list(query),
  })
}

export function useMyTickets(activeOnly: boolean) {
  return useQuery({
    queryKey: keys.myTickets(activeOnly),
    queryFn: () => workers.myTickets(activeOnly),
  })
}

export function useNotifications(unreadOnly: boolean) {
  return useQuery({
    queryKey: keys.notifications(unreadOnly),
    queryFn: () => notifications.list(unreadOnly),
  })
}

export function useUnreadCount(enabled: boolean) {
  return useQuery({
    queryKey: keys.unreadCount,
    queryFn: notifications.unreadCount,
    enabled,
    refetchInterval: 60_000,
  })
}

export function useCreateTicket(
  options?: UseMutationOptions<Awaited<ReturnType<typeof tickets.create>>, Error, TicketCreateInput>,
) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (input: TicketCreateInput) => tickets.create(input),
    ...options,
    onSuccess: (...args) => {
      void queryClient.invalidateQueries({ queryKey: ['tickets'] })
      void queryClient.invalidateQueries({ queryKey: keys.stats })
      options?.onSuccess?.(...args)
    },
  })
}

/**
 * Anything that moves a ticket touches its detail, the queues, the timeline and
 * the recipients' inboxes, so they are all refetched together.
 */
function useTicketMutation<TVariables>(
  ticketId: string,
  mutationFn: (variables: TVariables) => Promise<unknown>,
) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: keys.ticket(ticketId) })
      void queryClient.invalidateQueries({ queryKey: keys.history(ticketId) })
      void queryClient.invalidateQueries({ queryKey: keys.recommendations(ticketId) })
      void queryClient.invalidateQueries({ queryKey: ['tickets'] })
      void queryClient.invalidateQueries({ queryKey: keys.stats })
      void queryClient.invalidateQueries({ queryKey: ['workers'] })
      void queryClient.invalidateQueries({ queryKey: ['notifications'] })
    },
  })
}

export function useChangeStatus(ticketId: string) {
  return useTicketMutation(
    ticketId,
    ({ status, comment }: { status: TicketStatus; comment?: string }) =>
      tickets.changeStatus(ticketId, status, comment),
  )
}

export function useAssignTicket(ticketId: string) {
  return useTicketMutation(
    ticketId,
    ({ contractorId, notes }: { contractorId: string; notes?: string }) =>
      tickets.assign(ticketId, contractorId, notes),
  )
}

export function useAcceptAssignment(ticketId: string) {
  return useTicketMutation(ticketId, () => tickets.accept(ticketId))
}

export function useMarkNotificationRead() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => notifications.markRead(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['notifications'] })
    },
  })
}
