import { redirect } from '@tanstack/react-router'
import { useAuthStore } from '@/features/auth/model/authStore'

export function requireAuth() {
  if (!useAuthStore.getState().accessToken) {
    throw redirect({ to: '/login' })
  }
}

export function requireGuest() {
  if (useAuthStore.getState().accessToken) {
    throw redirect({ to: '/sessions' })
  }
}
