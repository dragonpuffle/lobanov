import { createFileRoute } from '@tanstack/react-router'
import { SessionWorkspacePage } from '@/pages/SessionWorkspacePage'
import { requireAuth } from '@/app/guards'

export const Route = createFileRoute('/sessions/$sessionId')({
  beforeLoad: () => requireAuth(),
  component: SessionWorkspacePage,
})
