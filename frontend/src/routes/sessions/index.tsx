import { createFileRoute } from '@tanstack/react-router'
import { SessionsListPage } from '@/pages/SessionsListPage'
import { requireAuth } from '@/app/guards'

export const Route = createFileRoute('/sessions/')({
  beforeLoad: () => requireAuth(),
  component: SessionsListPage,
})
