import { createFileRoute } from '@tanstack/react-router'
import { SettingsPage } from '@/pages/SettingsPage'
import { requireAuth } from '@/app/guards'

export const Route = createFileRoute('/settings')({
  beforeLoad: () => requireAuth(),
  component: SettingsPage,
})
