import { useMutation } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { api } from '@/shared/api/client'
import { useAuthStore } from '@/features/auth/model/authStore'
import { qk } from '@/shared/api/queryKeys'
import { useQueryClient } from '@tanstack/react-query'

export function useLogin() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const setAuth = useAuthStore((s) => s.setAuth)
  const qc = useQueryClient()

  return useMutation({
    mutationKey: ['auth', 'login'],
    mutationFn: async (data: { email: string; password: string }) => {
      const { data: res, error, response } = await api.POST('/api/v1/auth/login', { body: data })
      if (error) throw new Error((error as { detail?: string })?.detail ?? t('auth.loginFailed'))
      if (response.status !== 200) throw new Error('Login failed')
      return res!
    },
    onSuccess: (data) => {
      if (!data.token.access_token) {
        toast.error(t('auth.noToken'))
        return
      }
      setAuth(data.user, data.token.access_token)
      qc.removeQueries({ queryKey: qk.sessions({}) })
      void navigate({ to: '/sessions' })
      toast.success(t('auth.welcome', { name: data.user.full_name }))
    },
    onError: (e: Error) => {
      toast.error(e.message)
    },
  })
}

export function useRegister() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  return useMutation({
    mutationKey: ['auth', 'register'],
    mutationFn: async (data: { email: string; password: string; full_name: string }) => {
      const { data: res, error, response } = await api.POST('/api/v1/auth/register', { body: data })
      if (error) throw new Error((error as { detail?: string })?.detail ?? t('auth.registerFailed'))
      if (response.status !== 201) throw new Error('Register failed')
      return res!
    },
    onSuccess: () => {
      toast.success(t('auth.registeredLogin'))
      void navigate({ to: '/login' })
    },
    onError: (e: Error) => {
      toast.error(e.message)
    },
  })
}
