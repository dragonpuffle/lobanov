import { createFileRoute, redirect } from '@tanstack/react-router'
import { useAuthStore } from '@/features/auth/model/authStore'

export const Route = createFileRoute('/')({
  beforeLoad: () => {
    const t = useAuthStore.getState().accessToken
    throw redirect({ to: t ? '/sessions' : '/login' })
  },
  component: () => null,
})
