import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/shared/api/client'

export function useCreateSession() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (template_id: string) => {
      const { data, error } = await api.POST('/api/v1/sessions', { body: { template_id } })
      if (error) throw new Error(String((error as { detail?: string }).detail ?? 'Create failed'))
      if (!data) throw new Error('No data')
      return data
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['sessions'], exact: false })
    },
  })
}
