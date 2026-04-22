from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from uuid import UUID, uuid4

from lobanov.domain import AudioRecord, DocumentationSession, DocumentationSessionStatus
from lobanov.protocols.repositories import AudioRecordRepositoryProtocol, DocumentationSessionRepositoryProtocol
from lobanov.protocols.services import FileStorageProtocol


class SessionNotFoundError(Exception):
    pass


class InvalidSessionStateError(Exception):
    pass


class AudioUploadError(Exception):
    pass


class UploadAudio[sessionT]:
    def __init__(
        self,
        session_repository: DocumentationSessionRepositoryProtocol[sessionT],
        audio_record_repository: AudioRecordRepositoryProtocol[sessionT],
        file_storage: FileStorageProtocol,
    ):
        self.session_repository = session_repository
        self.audio_record_repository = audio_record_repository
        self.file_storage = file_storage

    async def execute(self, session_id: UUID, file: BytesIO, filename: str) -> AudioRecord:
        async with self.session_repository.context() as session:
            documentation_session = await self.session_repository.get_by_id(session, session_id)
            if documentation_session is None:
                error_message = f"Session with id {session_id} not found"
                raise SessionNotFoundError(error_message)

            if documentation_session.status != DocumentationSessionStatus.CREATED:
                error_message = f"Session must be in CREATED state, current state: {documentation_session.status}"
                raise InvalidSessionStateError(error_message)

            try:
                file_path = await self.file_storage.save_audio(file, filename, session_id)
            except Exception as e:
                error_message = f"Failed to save audio file: {e}"
                raise AudioUploadError(error_message) from e

            file.seek(0, 2)
            file_size = file.tell()
            file.seek(0)

            file_ext = Path(filename).suffix.lower().lstrip(".")
            now = datetime.now(UTC)

            audio_record = AudioRecord(
                id=uuid4(),
                session_id=session_id,
                file_path=file_path,
                file_name=filename,
                file_size=file_size,
                duration=0.0,
                format=file_ext,
                created_at=now,
                updated_at=now,
            )

            created_audio_record = await self.audio_record_repository.create(session, audio_record)

            updated_session = DocumentationSession(
                id=documentation_session.id,
                user_id=documentation_session.user_id,
                status=DocumentationSessionStatus.AUDIO_UPLOADED,
                created_at=documentation_session.created_at,
                updated_at=now,
            )

            await self.session_repository.update(session, updated_session)

            return created_audio_record
