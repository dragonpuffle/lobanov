from uuid import UUID

from lobanov.domain import DocumentationSession, DocumentationSessionStatus
from lobanov.protocols.repositories import DocumentationSessionRepositoryProtocol, UserRepositoryProtocol


class UserNotFoundError(Exception):
    pass


class GetUserSessions[sessionT]:
    def __init__(
        self,
        user_repository: UserRepositoryProtocol,
        session_repository: DocumentationSessionRepositoryProtocol,
    ):
        self.user_repository = user_repository
        self.session_repository = session_repository

    async def execute(
        self,
        session: sessionT,
        user_id: UUID,
        limit: int = 100,
        offset: int = 0,
        status: DocumentationSessionStatus | None = None,
    ) -> list[DocumentationSession]:
        user = await self.user_repository.get_by_id(session, user_id)
        if user is None:
            error_message = f"User with id {user_id} not found"
            raise UserNotFoundError(error_message)

        if not user.is_active:
            error_message = f"User with id {user_id} is not active"
            raise ValueError(error_message)

        sessions = await self.session_repository.get_by_user_id(session, user_id, limit, offset)

        if status is not None:
            sessions = [s for s in sessions if s.status == status]

        return sessions
