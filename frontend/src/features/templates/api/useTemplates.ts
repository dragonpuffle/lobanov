import { useQuery } from '@tanstack/react-query'
import { api } from '@/shared/api/client'
import { qk } from '@/shared/api/queryKeys'

export function useTemplates(activeOnly = true) {
  return useQuery({
    queryKey: qk.templates(activeOnly),
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/templates', {
        params: { query: { active_only: activeOnly, limit: 100, offset: 0 } },
      })
      if (error) throw new Error('Failed to load templates')
      if (!data) throw new Error('No data')
      return data
    },
  })
}

export function useTemplateDetails(id: string | undefined) {
  return useQuery({
    queryKey: qk.template(id ?? ''),
    enabled: !!id,
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/templates/{template_id}', {
        params: { path: { template_id: id! } },
      })
      if (error) throw new Error('Template not found')
      if (!data) throw new Error('No data')
      return data
    },
  })
}
