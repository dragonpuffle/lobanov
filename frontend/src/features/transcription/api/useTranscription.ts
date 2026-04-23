import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/shared/api/client'
import { qk } from '@/shared/api/queryKeys'

export function useStartTranscription() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ sessionId, language }: { sessionId: string; language?: string }) => {
      const { data, error } = await api.POST('/api/v1/sessions/{session_id}/transcribe', {
        params: { path: { session_id: sessionId } },
        body: { language: (language as 'ru' | 'en' | undefined) ?? 'ru' },
      })
      if (error) throw new Error(String((error as { detail?: string }).detail ?? 'Transcribe failed'))
      return data
    },
    onSuccess: (_d, v) => {
      void qc.invalidateQueries({ queryKey: qk.session(v.sessionId) })
    },
  })
}

export function useTranscript(sessionId: string | undefined) {
  return useQuery({
    queryKey: qk.transcript(sessionId ?? ''),
    enabled: !!sessionId,
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/sessions/{session_id}/transcript', {
        params: { path: { session_id: sessionId! } },
      })
      if (error) throw error
      return data
    },
    retry: false,
  })
}
