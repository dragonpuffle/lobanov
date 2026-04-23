import { useQuery } from '@tanstack/react-query'
import { api } from '@/shared/api/client'
import { qk, type SessionListFilters } from '@/shared/api/queryKeys'

export function useSessions(filters: SessionListFilters) {
  return useQuery({
    queryKey: qk.sessions(filters),
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/sessions', {
        params: {
          query: {
            limit: filters.limit ?? 100,
            offset: filters.offset ?? 0,
            status: filters.status ?? undefined,
          },
        },
      })
      if (error) throw new Error(String((error as { detail?: string }).detail ?? 'Failed to load sessions'))
      if (!data) throw new Error('No data')
      return data
    },
  })
}

export function useSessionDetails(id: string | undefined) {
  return useQuery({
    queryKey: qk.session(id ?? ''),
    enabled: !!id,
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/sessions/{session_id}', {
        params: { path: { session_id: id! } },
      })
      if (error) throw new Error(String((error as { detail?: string }).detail ?? 'Session not found'))
      if (!data) throw new Error('No data')
      return data
    },
    refetchInterval: (q) => {
      const d = q.state.data
      if (!d) return false
      if (d.has_audio && !d.has_transcript) return 2000
      if (d.has_transcript && !d.has_document) return 2000
      return false
    },
  })
}
