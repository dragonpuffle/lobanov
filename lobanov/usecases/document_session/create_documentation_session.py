from datetime import UTC, datetime
from uuid import UUID, uuid4

from lobanov.domain import DocumentationSession, DocumentationSessionStatus
from lobanov.protocols.repositories import DocumentationSessionRepositoryProtocol, UserRepositoryProtocol


class UserNotFoundError(Exception):
    pass


class CreateDocumentationSession[sessionT]:
    def __init__(
        self,
        user_repository: UserRepositoryProtocol,
        session_repository: DocumentationSessionRepositoryProtocol,
    ):
        self.user_repository = user_repository
        self.session_repository = session_repository

    async def execute(self, session: sessionT, user_id: UUID) -> DocumentationSession:
        user = await self.user_repository.get_by_id(session, user_id)
        if user is None:
            error_message = f"User with id {user_id} not found"
            raise UserNotFoundError(error_message)

        if not user.is_active:
            error_message = f"User with id {user_id} is not active"
            raise ValueError(error_message)

        now = datetime.now(UTC)
        documentation_session = DocumentationSession(
            id=uuid4(),
            user_id=user_id,
            status=DocumentationSessionStatus.CREATED,
            created_at=now,
            updated_at=now,
        )

        return await self.session_repository.create(session, documentation_session)
