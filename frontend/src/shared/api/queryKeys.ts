import type { DocumentationSessionStatus } from '@/shared/api/types'

export type SessionListFilters = {
  status?: DocumentationSessionStatus | null
  limit?: number
  offset?: number
}

export const qk = {
  me: ['auth', 'me'] as const,
  sessions: (f: SessionListFilters) => ['sessions', f] as const,
  session: (id: string) => ['sessions', id] as const,
  transcript: (id: string) => ['sessions', id, 'transcript'] as const,
  document: (id: string) => ['sessions', id, 'document'] as const,
  validation: (id: string) => ['sessions', id, 'document', 'validate'] as const,
  templates: (activeOnly?: boolean) => ['templates', { activeOnly }] as const,
  template: (id: string) => ['templates', id] as const,
}
