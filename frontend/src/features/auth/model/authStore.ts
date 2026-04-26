import { create } from 'zustand'
import { createJSONStorage, persist } from 'zustand/middleware'
import type { UserResponse } from '@/shared/api/types'

type AuthState = {
  user: UserResponse | null
  accessToken: string | null
  setAuth: (user: UserResponse, accessToken: string) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      setAuth: (user, accessToken) => set({ user, accessToken }),
      logout: () => set({ user: null, accessToken: null }),
    }),
    {
      name: 'mda-auth',
      storage: createJSONStorage(() => localStorage),
      partialize: (s) => ({ user: s.user, accessToken: s.accessToken }),
    },
  ),
)
