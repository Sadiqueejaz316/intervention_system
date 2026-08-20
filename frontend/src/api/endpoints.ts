import { request } from './client'
import type {
  Assignment,
  DomainConfig,
  Notification,
  RegisterInput,
  Ticket,
  TicketCreateInput,
  TicketHistoryEntry,
  TicketQuery,
  TicketStats,
  TicketStatus,
  TokenResponse,
  User,
  Worker,
  WorkerRecommendation,
} from './types'

export const auth = {
  login: (email: string, password: string) =>
    request<TokenResponse>('/auth/login', {
      method: 'POST',
      body: { email, password },
      anonymous: true,
    }),

  register: (input: RegisterInput) =>
    request<User>('/auth/register', {
      method: 'POST',
      body: input,
      anonymous: true,
    }),

  me: () => request<User>('/auth/me'),
}

export const tickets = {
  list: (query: TicketQuery = {}) =>
    request<Ticket[]>('/tickets', { query: { ...query } }),

  stats: () => request<TicketStats>('/tickets/stats'),

  get: (id: string) => request<Ticket>(`/tickets/${id}`),

  create: (input: TicketCreateInput) =>
    request<Ticket>('/tickets', { method: 'POST', body: input }),

  /** The actor is the bearer token; only the target status travels in the body. */
  changeStatus: (id: string, status: TicketStatus, comment?: string) =>
    request<Ticket>(`/tickets/${id}/status`, {
      method: 'PATCH',
      body: { status, comment: comment?.trim() || null },
    }),

  history: (id: string) =>
    request<TicketHistoryEntry[]>(`/tickets/${id}/history`),

  recommendations: (id: string, limit = 5) =>
    request<WorkerRecommendation[]>(`/tickets/${id}/recommendations`, {
      query: { limit },
    }),

  assign: (id: string, contractorId: string, notes?: string) =>
    request<Assignment>(`/tickets/${id}/assign`, {
      method: 'POST',
      body: { contractor_id: contractorId, notes: notes?.trim() || null },
    }),

  accept: (id: string) =>
    request<Assignment>(`/tickets/${id}/accept`, { method: 'POST' }),
}

export const workers = {
  list: (query: { available?: boolean; skill?: string } = {}) =>
    request<Worker[]>('/workers', { query: { ...query } }),

  me: () => request<Worker>('/workers/me'),

  myTickets: (activeOnly = false) =>
    request<Ticket[]>('/workers/me/tickets', { query: { active_only: activeOnly } }),

  tickets: (workerId: string, activeOnly = false) =>
    request<Ticket[]>(`/workers/${workerId}/tickets`, {
      query: { active_only: activeOnly },
    }),
}

export const notifications = {
  list: (unreadOnly = false) =>
    request<Notification[]>('/notifications', { query: { unread_only: unreadOnly } }),

  unreadCount: () => request<number>('/notifications/unread-count'),

  markRead: (id: string) =>
    request<Notification>(`/notifications/${id}/read`, { method: 'PATCH' }),
}

export const domain = {
  config: () => request<DomainConfig>('/domain/config', { anonymous: true }),
}
