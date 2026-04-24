import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/shared/api/client'
import { getAccessToken } from '@/shared/api/token-bridge'
import { API_BASE } from '@/shared/config/env'
import { qk } from '@/shared/api/queryKeys'
import type { MedicalDocumentDetailsResponse } from '@/shared/api/types'

function parseFilenameFromContentDisposition(header: string | null, fallback: string): string {
  if (!header) return fallback
  const m = /filename\*=UTF-8''([^;]+)|filename="([^"]+)"|filename=([^;]+)/i.exec(header)
  if (m) {
    const raw = (m[1] ?? m[2] ?? m[3]).trim()
    try {
      return decodeURIComponent(raw)
    } catch {
      return raw
    }
  }
  return fallback
}

export function useGenerateDocument() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ sessionId, templateId }: { sessionId: string; templateId: string }) => {
      const { data, error } = await api.POST('/api/v1/sessions/{session_id}/document/generate', {
        params: { path: { session_id: sessionId } },
        body: { template_id: templateId },
      })
      if (error) throw new Error(String((error as { detail?: string }).detail ?? 'Generate failed'))
      return data
    },
    onSuccess: (_d, v) => {
      void qc.invalidateQueries({ queryKey: qk.session(v.sessionId) })
    },
  })
}

export function useMedicalDocument(sessionId: string | undefined) {
  return useQuery({
    queryKey: qk.document(sessionId ?? ''),
    enabled: !!sessionId,
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/sessions/{session_id}/document', {
        params: { path: { session_id: sessionId! } },
      })
      if (error) throw error
      if (!data) throw new Error('No document')
      return data
    },
    retry: false,
  })
}

export function useUpdateField(sessionId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ fieldId, value }: { fieldId: string; value: string }) => {
      const { data, error } = await api.PUT('/api/v1/sessions/{session_id}/document/fields/{field_id}', {
        params: { path: { session_id: sessionId, field_id: fieldId } },
        body: { value },
      })
      if (error) throw new Error(String((error as { detail?: string }).detail ?? 'Update failed'))
      if (!data) throw new Error('No data')
      return data
    },
    onMutate: async ({ fieldId, value }) => {
      await qc.cancelQueries({ queryKey: qk.document(sessionId) })
      const previous = qc.getQueryData<MedicalDocumentDetailsResponse>(qk.document(sessionId))
      if (previous) {
        qc.setQueryData<MedicalDocumentDetailsResponse>(qk.document(sessionId), {
          ...previous,
          field_values: previous.field_values.map((f) =>
            f.field_id === fieldId ? { ...f, value, status: 'user_edited' } : f,
          ),
        })
      }
      return { previous }
    },
    onError: (_e, _v, ctx) => {
      if (ctx?.previous) qc.setQueryData(qk.document(sessionId), ctx.previous)
    },
    onSettled: () => {
      void qc.invalidateQueries({ queryKey: qk.document(sessionId) })
      void qc.invalidateQueries({ queryKey: qk.validation(sessionId) })
    },
  })
}

export function useValidateDocument(sessionId: string | undefined) {
  return useQuery({
    queryKey: qk.validation(sessionId ?? ''),
    enabled: !!sessionId,
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/sessions/{session_id}/document/validate', {
        params: { path: { session_id: sessionId! } },
      })
      if (error) throw error
      if (!data) throw new Error('No data')
      return data
    },
  })
}

export function useConfirmDocument() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (sessionId: string) => {
      const { data, error } = await api.POST('/api/v1/sessions/{session_id}/document/confirm', {
        params: { path: { session_id: sessionId } },
      })
      if (error) throw new Error(String((error as { detail?: string }).detail ?? 'Confirm failed'))
      return data
    },
    onSuccess: (_d, sessionId) => {
      void qc.invalidateQueries({ queryKey: qk.session(sessionId) })
      void qc.invalidateQueries({ queryKey: qk.document(sessionId) })
    },
  })
}

export function useExportDocument() {
  return useMutation({
    mutationFn: async ({ sessionId, format }: { sessionId: string; format: string }) => {
      const token = getAccessToken()
      const res = await fetch(`${API_BASE}/api/v1/sessions/${sessionId}/document/export`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ format }),
      })
      if (!res.ok) {
        let detail = 'Export failed'
        try {
          const j = (await res.json()) as { detail?: unknown }
          detail = String(j.detail ?? detail)
        } catch {
          /* ignore */
        }
        throw new Error(detail)
      }
      const blob = await res.blob()
      const fallback = format === 'pdf' ? 'document.pdf' : 'document.json'
      const filename = parseFilenameFromContentDisposition(res.headers.get('Content-Disposition'), fallback)
      return { blob, filename }
    },
  })
}
