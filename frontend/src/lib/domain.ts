import type { DomainConfig, Ticket } from '@/api/types'
import { humanise } from './format'

export function isEmergency(ticket: Ticket): boolean {
  return Boolean(ticket.is_emergency || ticket.metadata.is_emergency)
}

export function issueTypeLabel(config: DomainConfig | undefined, value: string): string {
  return config?.issue_types.find((item) => item.value === value)?.label ?? humanise(value)
}

export function skillLabel(config: DomainConfig | undefined, value: string): string {
  return config?.skill_labels?.[value] ?? humanise(value)
}

export function metaText(ticket: Ticket, key: string): string | undefined {
  const value = ticket.metadata[key]
  if (value === undefined || value === null || value === '') return undefined
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  return String(value)
}

export function buildingLine(ticket: Ticket): string | undefined {
  return metaText(ticket, 'building_name') ?? ticket.location_text ?? undefined
}
