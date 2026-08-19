/** Mirrors the response schemas in `backend/app/schemas`. */

export type UserRole = 'REPORTER' | 'CONTRACTOR' | 'DISPATCHER' | 'ADMIN'

export type TicketStatus =
  | 'OPEN'
  | 'ASSIGNED'
  | 'IN_PROGRESS'
  | 'RESOLVED'
  | 'CLOSED'

export type TicketPriority = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'

export type NotificationType =
  | 'INFO'
  | 'ASSIGNMENT'
  | 'STATUS_CHANGE'
  | 'ESCALATION'

export interface User {
  id: string
  name: string
  email: string
  role: UserRole
  skills: string[]
  latitude: number | null
  longitude: number | null
  is_available: boolean
  created_at: string
  updated_at: string
}

export interface Worker extends User {
  active_ticket_count: number
}

export interface WorkerSummary {
  id: string
  name: string
  skills: string[]
  is_available: boolean
}

export interface Ticket {
  id: string
  title: string
  description: string | null
  type: string
  priority: TicketPriority
  status: TicketStatus
  reporter_id: string | null
  location_text: string | null
  latitude: number | null
  longitude: number | null
  metadata: Record<string, unknown>
  created_at: string
  updated_at: string
  assigned_worker: WorkerSummary | null
}

export interface TicketHistoryEntry {
  id: string
  ticket_id: string
  user_id: string | null
  action: string
  old_status: string | null
  new_status: string | null
  comment: string | null
  metadata: Record<string, unknown>
  created_at: string
}

export interface Assignment {
  id: string
  ticket_id: string
  contractor_id: string
  assigned_by: string | null
  assigned_at: string
  accepted_at: string | null
  started_at: string | null
  completed_at: string | null
  notes: string | null
}

export interface WorkerRecommendation {
  worker_id: string
  name: string
  score: number
  reasons: string[]
}

export interface Notification {
  id: string
  user_id: string
  ticket_id: string | null
  title: string
  message: string
  type: NotificationType
  is_read: boolean
  created_at: string
}

export interface DomainConfig {
  domain_name: string
  worker_label: string
  issue_types: string[]
  skill_vocabulary: string[]
  status_transitions: Record<string, string[]>
  required_metadata: Record<string, string[]>
  required_skills_by_type: Record<string, string[]>
  priorities: TicketPriority[]
  statuses: TicketStatus[]
  metadata_hint: Record<string, unknown>
}

export interface TokenResponse {
  access_token: string
  token_type: string
}

export interface TicketCreateInput {
  title: string
  description?: string | null
  type: string
  priority: TicketPriority
  location_text?: string | null
  latitude?: number | null
  longitude?: number | null
  metadata?: Record<string, unknown>
}

export interface RegisterInput {
  name: string
  email: string
  password: string
  role: Extract<UserRole, 'REPORTER' | 'CONTRACTOR'>
  skills?: string[]
  latitude?: number | null
  longitude?: number | null
}

export interface TicketQuery {
  status?: TicketStatus | ''
  priority?: TicketPriority | ''
  type?: string
  limit?: number
  offset?: number
}
